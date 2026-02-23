from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.db import engine

router = APIRouter(tags=["ops"])

@router.get("/worker/healthz")
def worker_healthz(max_age_seconds: int = 300):
    """
    Uses worker_status table (Postgres) to detect if the worker is alive.
    ok=True when last_run_at is recent AND health flags are ok.
    """
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT worker_id, last_run_at, last_email_processed_at,
                   lock_health_ok, credits_health_ok, last_error, updated_at
            FROM worker_status
            ORDER BY last_run_at DESC NULLS LAST, updated_at DESC
            LIMIT 1
        """)).mappings().first()

    if not row:
        raise HTTPException(status_code=503, detail="No worker_status rows found")

    last_run_at = row["last_run_at"]
    now = datetime.now(timezone.utc)

    if last_run_at is None:
        age = None
        fresh = False
    else:
        age = int((now - last_run_at).total_seconds())
        fresh = age <= max_age_seconds

    ok = bool(fresh and row["lock_health_ok"] and row["credits_health_ok"])

    return {
        "ok": ok,
        "max_age_seconds": max_age_seconds,
        "worker_id": row["worker_id"],
        "last_run_at": last_run_at.isoformat() if last_run_at else None,
        "seconds_since_last_run": age,
        "last_email_processed_at": row["last_email_processed_at"].isoformat() if row["last_email_processed_at"] else None,
        "lock_health_ok": bool(row["lock_health_ok"]),
        "credits_health_ok": bool(row["credits_health_ok"]),
        "last_error": row["last_error"],
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }
