import os
from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text

from app.db import engine
from app.services.billing_guard import get_remaining_credits, set_plan, log_usage

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()


def _check_admin(request: Request):
    # Simple protection: /admin?pw=YOURPASS
    if not ADMIN_PASSWORD:
        return
    pw = (request.query_params.get("pw") or "").strip()
    if pw != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    _check_admin(request)

    with engine.connect() as c:
        org_rows = c.execute(text("SELECT id, name FROM organizations ORDER BY id")).fetchall()
        acct_rows = c.execute(
            text("SELECT org_id, email, imap_host, imap_port FROM email_accounts ORDER BY org_id")
        ).fetchall()
        usage_rows = c.execute(
            text("SELECT org_id, event, qty, meta, created_at FROM org_usage ORDER BY id DESC LIMIT 50")
        ).fetchall()
        credit_rows = c.execute(text("SELECT org_id, plan FROM org_credits")).fetchall()

    plan_map = {int(r[0]): (r[1] or "free") for r in credit_rows}

    orgs = []
    for r in org_rows:
        oid = int(r[0])
        orgs.append(
            {
                "id": oid,
                "name": r[1] or f"Org{oid}",
                "plan": plan_map.get(oid, "free"),
                "remaining": get_remaining_credits(engine, oid),
            }
        )

    accounts = [
        {"org_id": int(r[0]), "email": r[1], "imap_host": r[2], "imap_port": r[3]} for r in acct_rows
    ]
    usage = [
        {"org_id": int(r[0]), "event": r[1], "qty": int(r[2]), "meta": r[3], "created_at": r[4]}
        for r in usage_rows
    ]

    pw = request.query_params.get("pw") or ""
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "orgs": orgs, "accounts": accounts, "usage": usage, "pw": pw},
    )


@router.post("/admin/set-plan")
def admin_set_plan(
    request: Request,
    org_id: int = Form(...),
    plan: str = Form(...),
    pw: str = Form(""),
):
    # Rebuild query_params-like auth
    class _FakeReq:
        def __init__(self, pwv): self.query_params = {"pw": pwv}

    _check_admin(_FakeReq(pw))

    plan = (plan or "").strip().lower()
    if plan not in ("free", "pro", "enterprise"):
        plan = "free"

    set_plan(engine, int(org_id), plan)
    log_usage(engine, int(org_id), "admin_set_plan", 1, {"plan": plan})

    # Redirect back to dashboard (keep pw)
    url = f"/admin"
    if pw:
        url += f"?pw={pw}"
    return RedirectResponse(url=url, status_code=303)
