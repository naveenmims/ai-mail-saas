from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

import os


import stripe

from fastapi import FastAPI, Depends, HTTPException, Request, Header
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db import test_db_connection, init_db, engine
from app.models import Organization, User, EmailAccount
from app.schemas import OrganizationCreate, UserCreate, LoginRequest, EmailAccountCreate
from app.security import hash_password, verify_password
from app.jwt_utils import create_access_token
from app.auth import get_current_user, require_roles
from app.ai_engine import generate_reply
from app.admin_api import router as admin_router
from app.routers.admin_c3 import router as admin_c3_router

from app.routers.billing import router as billing_router   # keep as it is ✅
from app.routers.billing_manual import router as manual_billing_router  # add ✅
from pathlib import Path
from app.admin_analytics import router as admin_analytics_router


def load_env_file():
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

load_env_file()


def load_env_file():
    env_path = Path(__file__).resolve().parents[1] / ".env"  # backend/.env
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

load_env_file()



# ✅ Create app FIRST
app = FastAPI(title="AI Mail SaaS")
templates = Jinja2Templates(directory="app/templates")
@app.post("/stripe/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None, alias="Stripe-Signature")):
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=STRIPE_WEBHOOK_SECRET,
        )
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": f"webhook signature failed: {repr(e)}"})

    event_type = event.get("type", "")
    obj = event.get("data", {}).get("object", {})

    # We will rely on metadata.org_id in Stripe objects you create (checkout/subscription)
    org_id = None
    try:
        md = obj.get("metadata") or {}
        if "org_id" in md:
            org_id = int(md["org_id"])
    except Exception:
        org_id = None

    # If org_id not present, try customer lookup path (optional)
    customer_id = obj.get("customer")

    def update_org(**fields):
        if not fields:
            return
        sets = ", ".join([f"{k} = :{k}" for k in fields.keys()])
        params = dict(fields)
        if org_id is not None:
            params["org_id"] = org_id
            q = f"UPDATE organizations SET {sets} WHERE id = :org_id"
        elif customer_id:
            params["customer_id"] = customer_id
            q = f"UPDATE organizations SET {sets} WHERE stripe_customer_id = :customer_id"
        else:
            return

        with engine.begin() as conn:
            conn.execute(text(q), params)

    # --- Handle key subscription lifecycle events ---
    if event_type in ("checkout.session.completed",):
        # checkout session contains customer + subscription
        update_org(
            stripe_customer_id=obj.get("customer"),
            stripe_subscription_id=obj.get("subscription"),
            subscription_status="active",
        )

    elif event_type in ("customer.subscription.created", "customer.subscription.updated"):
        update_org(
            stripe_customer_id=obj.get("customer"),
            stripe_subscription_id=obj.get("id"),
            stripe_price_id=(obj.get("items", {}).get("data") or [{}])[0].get("price", {}).get("id"),
            subscription_status=obj.get("status") or "active",
        )

    elif event_type in ("customer.subscription.deleted",):
        update_org(subscription_status="canceled")

    elif event_type in ("invoice.payment_failed",):
        update_org(subscription_status="past_due")

    elif event_type in ("invoice.paid", "invoice.payment_succeeded"):
        # optional: you can reset credits here based on plan/price_id
        update_org(subscription_status="active")

    return {"ok": True}

app.include_router(admin_router)
app.include_router(admin_c3_router)
app.include_router(billing_router)          # Stripe
app.include_router(manual_billing_router)   # Manual
app.include_router(admin_analytics_router)



# ✅ Static mount AFTER app exists
app.mount("/static", StaticFiles(directory="static"), name="static")

# ✅ If you want uvicorn app.main:application to work
application = app

bearer_scheme = HTTPBearer()

# ✅ Admin API routes (used by /static/admin.html)
app.include_router(admin_router)

@app.get("/debug/env")
def debug_env():
    import os
    return {
        "has_stripe_key": bool(os.getenv("STRIPE_SECRET_KEY")),
        "stripe_price_pro": os.getenv("STRIPE_PRICE_PRO"),
        "stripe_price_business": os.getenv("STRIPE_PRICE_BUSINESS"),
    }
@app.get("/debug/stripe")
def debug_stripe():
    import os
    k = os.getenv("STRIPE_SECRET_KEY") or ""
    return {"key_prefix": k[:8], "key_len": len(k)}

from fastapi.responses import PlainTextResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(Exception)
async def all_exception_handler(request, exc):
    return PlainTextResponse(str(exc), status_code=500)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/db-check")
def db_check():
    try:
        test_db_connection()
        return {"db": "connected"}
    except Exception as e:
        return {"db": "error", "detail": str(e)}


@app.post("/organizations")
def create_organization(payload: OrganizationCreate):
    with Session(engine) as db:
        existing = db.query(Organization).filter(Organization.name == payload.name).first()
        if existing:
            raise HTTPException(status_code=409, detail="Organization already exists")

        org = Organization(name=payload.name)
        db.add(org)
        db.commit()
        db.refresh(org)
        return {"id": org.id, "name": org.name}


@app.get("/organizations")
def list_organizations():
    with Session(engine) as db:
        orgs = db.query(Organization).order_by(Organization.id).all()
        return [{"id": o.id, "name": o.name} for o in orgs]


@app.post("/users")
def create_user(payload: UserCreate):
    with Session(engine) as db:
        org = db.query(Organization).filter(Organization.id == payload.org_id).first()
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        existing = db.query(User).filter(User.email == payload.email).first()
        if existing:
            raise HTTPException(status_code=409, detail="User already exists")

        user = User(
            org_id=payload.org_id,
            email=payload.email,
            password=hash_password(payload.password),
            role=payload.role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"id": user.id, "org_id": user.org_id, "email": user.email, "role": user.role}


@app.get("/users")
def list_users(current_user: User = Depends(get_current_user)):
    require_roles(current_user, ["owner", "admin"])
    with Session(engine) as db:
        users = db.query(User).filter(User.org_id == current_user.org_id).all()
        return [{"id": u.id, "org_id": u.org_id, "email": u.email, "role": u.role} for u in users]


@app.post("/email-accounts")
def create_email_account(payload: EmailAccountCreate, current_user: User = Depends(get_current_user)):
    require_roles(current_user, ["owner", "admin"])
    with Session(engine) as db:
        acc = EmailAccount(
            org_id=current_user.org_id,
            label=payload.label,
            email=payload.email,
            imap_host=payload.imap_host,
            imap_port=payload.imap_port,
            imap_username=payload.imap_username,
            imap_password=payload.imap_password,
            sendgrid_api_key=payload.sendgrid_api_key,
            from_name=payload.from_name,
        )
        db.add(acc)
        db.commit()
        db.refresh(acc)
        return {"id": acc.id, "org_id": acc.org_id}


@app.get("/email-accounts")
def list_email_accounts(current_user: User = Depends(get_current_user)):
    require_roles(current_user, ["owner", "admin"])
    with Session(engine) as db:
        accs = db.query(EmailAccount).filter(EmailAccount.org_id == current_user.org_id).all()
        return [
            {
                "id": a.id,
                "org_id": a.org_id,
                "label": a.label,
                "email": a.email,
                "imap_host": a.imap_host,
                "imap_port": a.imap_port,
                "imap_username": a.imap_username,
                "from_name": a.from_name,
            }
            for a in accs
        ]


@app.post("/login")
def login(payload: LoginRequest):
    with Session(engine) as db:
        user = db.query(User).filter(User.email == payload.email).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not verify_password(payload.password, user.password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = create_access_token(user.id, user.org_id, user.role)
        return {"access_token": token, "token_type": "bearer"}

def _db_path() -> str:
    # Ensures DB path is based on backend working directory
    return os.path.join(os.getcwd(), "ai_mail.db")

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    db = _db_path()
    con = sqlite3.connect(db)
    cur = con.cursor()

    # worker_status
    cur.execute("SELECT worker_id, last_run_at FROM worker_status ORDER BY last_run_at DESC LIMIT 25")
    worker_rows = cur.fetchall()

    # conversation_audit
    cur.execute("SELECT direction, thread_key, created_at FROM conversation_audit ORDER BY id DESC LIMIT 50")
    audit_rows = cur.fetchall()

    con.close()
    return templates.TemplateResponse(
        "admin.html",
        {"request": request, "worker_rows": worker_rows, "audit_rows": audit_rows},
    )

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="AI Mail SaaS",
        version="0.1.0",
        description="AI Mail SaaS API",
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    }
    openapi_schema["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema
from fastapi import Header, HTTPException
from datetime import datetime, timezone

def require_admin(x_admin_token: str | None, authorization: str | None):
    expected = os.getenv("ADMIN_TOKEN", "")
    token = x_admin_token

    if (not token) and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()

    if not expected or token != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/admin/health")
def admin_health(
    x_admin_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
):
    require_admin(x_admin_token, authorization)
    return {"ok": True, "server_time_utc": datetime.now(timezone.utc).isoformat()}


app.openapi = custom_openapi

app.include_router(admin_analytics_router)

class ReplyRequest(BaseModel):
    subject: str
    body: str


@app.post("/ai/reply")
def ai_reply(payload: ReplyRequest, current_user: User = Depends(get_current_user)):
    reply_text = generate_reply(payload.subject, payload.body)
    return {"reply": reply_text}
