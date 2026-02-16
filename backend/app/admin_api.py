import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from sqlalchemy.orm import Session

from app.db import engine
from app.models import Organization
from app.models import Organization, ConversationAudit, WorkerStatus

router = APIRouter(prefix="/admin", tags=["admin"])


# --------------------------------------------------
# ADMIN TOKEN CHECK
# --------------------------------------------------
def require_admin_token(x_admin_token: Optional[str]):
    expected = os.getenv("ADMIN_TOKEN")

    if not expected:
        raise HTTPException(
            status_code=500,
            detail="ADMIN_TOKEN not set in .env"
        )

    if not x_admin_token or x_admin_token != expected:
        raise HTTPException(
            status_code=401,
            detail="Invalid admin token"
        )


# --------------------------------------------------
# LIST ORGS
# --------------------------------------------------
@router.get("/orgs")
def list_orgs(x_admin_token: Optional[str] = Header(None)):
    require_admin_token(x_admin_token)

    with Session(engine) as db:
        orgs = db.query(Organization).order_by(Organization.id).all()
        return [{"id": o.id, "name": o.name} for o in orgs]


# --------------------------------------------------
# GET SINGLE ORG
# --------------------------------------------------
@router.get("/orgs/{org_id}")
def get_org(org_id: int, x_admin_token: Optional[str] = Header(None)):
    require_admin_token(x_admin_token)

    with Session(engine) as db:
        o = db.query(Organization).filter(Organization.id == org_id).first()

        if not o:
            raise HTTPException(status_code=404, detail="Organization not found")

        return {
            "id": o.id,
            "name": o.name,
            "support_name": o.support_name,
            "support_email": o.support_email,
            "website": o.website,
            "kb_text": o.kb_text,
            "system_prompt": o.system_prompt,
            "auto_reply": o.auto_reply,
            "max_replies_per_hour": o.max_replies_per_hour,
        }


# --------------------------------------------------
# UPDATE ORG
# --------------------------------------------------
@router.put("/orgs/{org_id}")
def update_org(
    org_id: int,
    payload: dict,
    x_admin_token: Optional[str] = Header(None)
):
    require_admin_token(x_admin_token)

    allowed_fields = {
        "name",
        "support_name",
        "support_email",
        "website",
        "kb_text",
        "system_prompt",
        "auto_reply",
        "max_replies_per_hour",
    }

    with Session(engine) as db:
        o = db.query(Organization).filter(Organization.id == org_id).first()

        if not o:
            raise HTTPException(status_code=404, detail="Organization not found")

        for key, value in payload.items():
            if key in allowed_fields:
                setattr(o, key, value)

        db.commit()

        return {"ok": True, "updated_org_id": org_id}
