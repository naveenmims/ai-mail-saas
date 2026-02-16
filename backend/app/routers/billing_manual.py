import os
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Organization
from sqlalchemy import text


router = APIRouter(prefix="/billing-manual", tags=["billing-manual"])

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

PLAN_LIMITS = {
    "free": {"credits_total": 1000, "cooldown_hours": 24},
    "pro": {"credits_total": 10000, "cooldown_hours": 12},
    "business": {"credits_total": 50000, "cooldown_hours": 6},
}

def require_admin(x_admin_token: str | None):
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=500, detail="ADMIN_TOKEN not set")
    if not x_admin_token or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token")


class ManualActivateIn(BaseModel):
    org_id: int
    plan: str  # free | pro | business
    days: int = 30


@router.post("/activate")
def manual_activate(payload: ManualActivateIn, x_admin_token: str | None = Header(None, alias="X-Admin-Token")):
    require_admin(x_admin_token)

    plan = payload.plan.lower().strip()
    cfg = PLAN_LIMITS.get(plan)
    if not cfg:
        raise HTTPException(status_code=400, detail=f"Invalid plan: {plan}")

    db: Session = SessionLocal()
    try:
        org = db.get(Organization, payload.org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        # Mark subscription active (gateway-independent)
        org.subscription_status = "active"
        org.stripe_price_id = f"MANUAL:{plan}"
        org.stripe_subscription_id = None
        org.stripe_customer_id = None

        # Apply plan-based cooldown (your worker uses this)
        org.cooldown_hours = int(cfg["cooldown_hours"])

        # Update org_credits using SQLite UPSERT
        db.execute(
            text("""
                INSERT INTO org_credits (org_id, plan, credits_total, credits_used, credits_reset_at, updated_at)
                VALUES (:org_id, :plan, :total, 0, NULL, CURRENT_TIMESTAMP)
                ON CONFLICT(org_id) DO UPDATE SET
                    plan=excluded.plan,
                    credits_total=excluded.credits_total,
                    updated_at=CURRENT_TIMESTAMP
            """),
            {"org_id": org.id, "plan": plan, "total": int(cfg["credits_total"])},
        )


        # Optional expiry info (not stored in DB unless you add a column)
        expires_at = datetime.utcnow() + timedelta(days=int(payload.days))

        db.commit()

        return {
            "ok": True,
            "org_id": org.id,
            "plan": plan,
            "subscription_status": org.subscription_status,
            "cooldown_hours": org.cooldown_hours,
            "credits_total": int(cfg["credits_total"]),
            "manual_expires_at_utc": expires_at.isoformat() + "Z",
        }
    finally:
        db.close()


class ManualCancelIn(BaseModel):
    org_id: int


@router.post("/cancel")
def manual_cancel(payload: ManualCancelIn, x_admin_token: str | None = Header(None, alias="X-Admin-Token")):
    require_admin(x_admin_token)

    db: Session = SessionLocal()
    try:
        org = db.get(Organization, payload.org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        org.subscription_status = "inactive"
        org.stripe_price_id = None
        org.stripe_subscription_id = None
        org.stripe_customer_id = None

        # Downgrade cooldown to free
        org.cooldown_hours = int(PLAN_LIMITS["free"]["cooldown_hours"])

        # Downgrade org_credits to free
        db.execute(
            text("""
                INSERT INTO org_credits (org_id, plan, credits_total, credits_used, credits_reset_at, updated_at)
                VALUES (:org_id, 'free', :total, 0, NULL, CURRENT_TIMESTAMP)
                ON CONFLICT(org_id) DO UPDATE SET
                    plan='free',
                    credits_total=:total,
                    updated_at=CURRENT_TIMESTAMP
            """),
            {"org_id": org.id, "total": int(PLAN_LIMITS["free"]["credits_total"])},
        )


        db.commit()
        return {"ok": True, "org_id": org.id, "subscription_status": org.subscription_status, "plan": "free"}
    finally:
        db.close()
