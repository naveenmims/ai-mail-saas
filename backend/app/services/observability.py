from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import ConversationAudit


def now_utc():
    return datetime.now(timezone.utc)


from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.orm import Session

def upsert_worker_status(
    db: Session,
    worker_id: str,
    last_run_at=None,
    last_email_processed_at=None,
    last_email_message_id=None,
    last_thread_key=None,
    lock_health_ok=True,
    credits_health_ok=True,
    last_error=None,
):
    # ✅ Normalize booleans (accepts 1/0, "1"/"0", True/False)
    lock_health_ok = bool(int(lock_health_ok)) if isinstance(lock_health_ok, (int, str)) else bool(lock_health_ok)
    credits_health_ok = bool(int(credits_health_ok)) if isinstance(credits_health_ok, (int, str)) else bool(credits_health_ok)

    db.execute(
        text(
            """
            INSERT INTO worker_status (
                worker_id, last_run_at, last_email_processed_at,
                last_email_message_id, last_thread_key,
                lock_health_ok, credits_health_ok, last_error, updated_at
            )
            VALUES (
                :worker_id, :last_run_at, :last_email_processed_at,
                :last_email_message_id, :last_thread_key,
                :lock_health_ok, :credits_health_ok, :last_error, :updated_at
            )
            ON CONFLICT(worker_id) DO UPDATE SET
                last_run_at=excluded.last_run_at,
                last_email_processed_at=excluded.last_email_processed_at,
                last_email_message_id=excluded.last_email_message_id,
                last_thread_key=excluded.last_thread_key,
                lock_health_ok=excluded.lock_health_ok,
                credits_health_ok=excluded.credits_health_ok,
                last_error=excluded.last_error,
                updated_at=excluded.updated_at
            """
        ),
        {
            "worker_id": worker_id,
            "last_run_at": last_run_at,
            "last_email_processed_at": last_email_processed_at,
            "last_email_message_id": last_email_message_id,
            "last_thread_key": last_thread_key,
            "lock_health_ok": lock_health_ok,            # ✅ now True/False
            "credits_health_ok": credits_health_ok,      # ✅ now True/False
            "last_error": last_error,
            "updated_at": datetime.now(timezone.utc),
        },
    )
    db.commit()


def log_conversation(
    db: Session,
    *,
    org_id: int,
    thread_key: str,
    direction: str,  # "IN" or "OUT"
    customer_email: Optional[str] = None,
    subject: Optional[str] = None,
    body_text: Optional[str] = None,
    body_html: Optional[str] = None,
    email_message_id: Optional[str] = None,
    in_reply_to: Optional[str] = None,
    references_header: Optional[str] = None,
    ai_model: Optional[str] = None,
    ai_tokens_in: Optional[int] = None,
    ai_tokens_out: Optional[int] = None,
    
) -> None:
    row = ConversationAudit(
        org_id=org_id,
        thread_key=thread_key,
        direction=direction,
        customer_email=customer_email,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        email_message_id=email_message_id,        
        ai_model=ai_model,
        ai_tokens_in=ai_tokens_in,
        ai_tokens_out=ai_tokens_out,
        in_reply_to=in_reply_to,
        references_header=references_header,

    )
    db.add(row)
