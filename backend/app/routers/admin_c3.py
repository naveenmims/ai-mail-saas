from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db import get_db  # <-- adjust if different
from sqlalchemy.orm import Session
from sqlalchemy import desc

# Import your models (adjust paths)
from app.models import Organization, ConversationAudit, WorkerStatus  # <-- adjust if different


router = APIRouter(prefix="/admin", tags=["admin-c3"])


# --------- Schemas ---------
class AutoReplyToggleIn(BaseModel):
    enabled: bool


class AutoReplyToggleOut(BaseModel):
    org_id: int
    auto_reply_enabled: bool


class ConversationOut(BaseModel):
    id: int
    org_id: int
    thread_key: str
    direction: str
    customer_email: Optional[str] = None
    subject: Optional[str] = None
    body_text: Optional[str] = None
    ai_model: Optional[str] = None
    created_at: datetime


class WorkerStatusOut(BaseModel):
    worker_id: str
    last_run_at: Optional[datetime] = None
    last_email_processed_at: Optional[datetime] = None
    last_email_message_id: Optional[str] = None
    last_thread_key: Optional[str] = None
    lock_health_ok: bool
    credits_health_ok: bool
    last_error: Optional[str] = None
    updated_at: Optional[datetime] = None


# --------- Endpoints ---------

@router.patch("/orgs/{org_id}/auto-reply", response_model=AutoReplyToggleOut)
def set_org_auto_reply(org_id: int, payload: AutoReplyToggleIn, db: Session = Depends(get_db)):
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")

    org.auto_reply_enabled = bool(payload.enabled)
    db.add(org)
    db.commit()
    db.refresh(org)
    return AutoReplyToggleOut(org_id=org.id, auto_reply_enabled=org.auto_reply_enabled)


@router.get("/orgs/{org_id}/conversations", response_model=List[ConversationOut])
def get_org_conversations(org_id: int, limit: int = 20, db: Session = Depends(get_db)):
    # Ensure org exists
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")

    limit = max(1, min(limit, 100))

    rows = (
        db.query(ConversationAudit)
        .filter(ConversationAudit.org_id == org_id)
        .order_by(desc(ConversationAudit.created_at))
        .limit(limit)
        .all()
    )
    return [
        ConversationOut(
            id=r.id,
            org_id=r.org_id,
            thread_key=r.thread_key,
            direction=r.direction,
            customer_email=r.customer_email,
            subject=r.subject,
            body_text=r.body_text,
            ai_model=r.ai_model,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/worker-status", response_model=List[WorkerStatusOut])
def list_worker_status(db: Session = Depends(get_db)):
    rows = db.query(WorkerStatus).order_by(desc(WorkerStatus.updated_at)).limit(50).all()
    return [
        WorkerStatusOut(
            worker_id=r.worker_id,
            last_run_at=r.last_run_at,
            last_email_processed_at=r.last_email_processed_at,
            last_email_message_id=r.last_email_message_id,
            last_thread_key=r.last_thread_key,
            lock_health_ok=r.lock_health_ok,
            credits_health_ok=r.credits_health_ok,
            last_error=r.last_error,
            updated_at=r.updated_at,
        )
        for r in rows
    ]
