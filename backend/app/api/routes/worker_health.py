from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.db import engine

router = APIRouter(tags=["ops"])

@router.get("/worker/healthz")
def worker_healthz(max_age_seconds: int = 300):
    """
    Health endpoint based on worker_status.last_run_at.
    ok=True if the most recent worker heartbeat is within max_age_seconds and health flags are ok.
    """
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT worker_id, last_run_at, lock_health_ok, credits_health_ok, last_error
            FROM worker_status
            ORDER BY last_run_at DESC NULLS LAST, updated_at DESC
            LIMIT 1
        """)).mappings().first()

    if not row:
        raise HTTPException(status_code=503, detail="No worker_status rows found")

    last_run_at = row["last_run_at"]
    if last_run_at is None:
        ok = False
        age = None
    else:
        now = datetime.now(timezone.utc)
        age = int((now - last_run_at).total_seconds())
        ok = age <= max_age_seconds

    ok = bool(ok and row["lock_health_ok"] and row["credits_health_ok"])

    return {
        "ok": ok,
        "max_age_seconds": max_age_seconds,
        "worker_id": row["worker_id"],
        "last_run_at": last_run_at.isoformat() if last_run_at else None,
        "seconds_since_last_run": age,
        "lock_health_ok": bool(row["lock_health_ok"]),
        "credits_health_ok": bool(row["credits_health_ok"]),
        "last_error": row["last_error"],
    }
