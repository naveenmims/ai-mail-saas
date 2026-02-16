import os
import stripe
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Organization

router = APIRouter(prefix="/billing", tags=["billing"])

PRICE_MAP = {
    "pro": os.getenv("STRIPE_PRICE_PRO", ""),
    "business": os.getenv("STRIPE_PRICE_BUSINESS", ""),
}

SUCCESS_URL = os.getenv("STRIPE_SUCCESS_URL", "http://127.0.0.1:8000/docs")
CANCEL_URL = os.getenv("STRIPE_CANCEL_URL", "http://127.0.0.1:8000/docs")


class CheckoutIn(BaseModel):
    org_id: int
    plan: str


@router.post("/checkout-session")
def create_checkout_session(payload: CheckoutIn):
    # set key here to be 100% sure it exists at request time
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="STRIPE_SECRET_KEY not set")

    plan = payload.plan.lower().strip()
    price_id = PRICE_MAP.get(plan, "")
    if not price_id:
        raise HTTPException(status_code=400, detail=f"Invalid plan or missing price id for plan={plan}")

    db: Session = SessionLocal()
    try:
        org = db.get(Organization, payload.org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        # 1) Customer
        customer_id = org.stripe_customer_id
        if not customer_id:
            try:
                customer = stripe.Customer.create(
                    name=org.name,
                    email=org.support_email or None,
                    metadata={"org_id": str(org.id)},
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Stripe customer error: {repr(e)}")

            customer_id = customer["id"]
            org.stripe_customer_id = customer_id
            db.commit()

        # 2) Checkout session
        try:
            session = stripe.checkout.Session.create(
                mode="subscription",
                customer=customer_id,
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=SUCCESS_URL,
                cancel_url=CANCEL_URL,
                subscription_data={"metadata": {"org_id": str(org.id)}},
                metadata={"org_id": str(org.id), "plan": plan},
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Stripe checkout error: {repr(e)}")

        # 3) Persist selected plan/price
        org.stripe_price_id = price_id
        db.commit()

        return {"url": session.get("url"), "session_id": session.get("id")}

    finally:
        db.close()


class PortalIn(BaseModel):
    org_id: int


@router.post("/portal")
def create_customer_portal(payload: PortalIn):
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="STRIPE_SECRET_KEY not set")

    db: Session = SessionLocal()
    try:
        org = db.get(Organization, payload.org_id)
        if not org or not org.stripe_customer_id:
            raise HTTPException(status_code=404, detail="Stripe customer not found for org")

        try:
            portal = stripe.billing_portal.Session.create(
                customer=org.stripe_customer_id,
                return_url=SUCCESS_URL,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Stripe portal error: {repr(e)}")

        return {"url": portal.get("url")}

    finally:
        db.close()
