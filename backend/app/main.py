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

