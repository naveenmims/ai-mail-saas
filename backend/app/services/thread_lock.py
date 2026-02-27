from datetime import datetime, timedelta, timezone
from sqlalchemy import text


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _bucket_start(dt: datetime, cooldown_seconds: int) -> datetime:
    # bucket by cooldown_seconds in UTC (e.g., 600 sec = 10 min)
    ts = int(dt.timestamp())
    bucket = ts - (ts % cooldown_seconds)
    return datetime.fromtimestamp(bucket, tz=timezone.utc)


def try_acquire_thread_lock(
    engine,
    org_id: int,
    thread_key: str,
    cooldown_seconds: int,
    worker_id: str,
    ttl_seconds: int,
) -> bool:
    """
    One row per (org_id, thread_key). Acquire rules:
    - Insert if no row exists.
    - If row exists and is expired -> takeover (update).
    - If row exists and is owned by same worker_id -> allow re-enter (idempotent).
    - Else -> deny (someone else holds unexpired lock).
    """
    now = _utcnow()
    bucket_start = _bucket_start(now, cooldown_seconds)
    expires_at = now + timedelta(seconds=ttl_seconds)

    sql = text("""
        INSERT INTO reply_thread_locks (org_id, thread_key, bucket_start, worker_id, expires_at)
        VALUES (:org_id, :thread_key, :bucket_start, :worker_id, :expires_at)
        ON CONFLICT (org_id, thread_key) DO UPDATE
        SET bucket_start = EXCLUDED.bucket_start,
            worker_id    = EXCLUDED.worker_id,
            expires_at   = EXCLUDED.expires_at
        WHERE
            reply_thread_locks.worker_id = :worker_id
            OR reply_thread_locks.expires_at IS NULL
            OR reply_thread_locks.expires_at <= :now
        RETURNING worker_id
    """)

    params = {
        "org_id": org_id,
        "thread_key": thread_key,
        "bucket_start": bucket_start,
        "worker_id": worker_id,
        "expires_at": expires_at,
        "now": now,
    }

    with engine.begin() as conn:
        row = conn.execute(sql, params).fetchone()
        if not row:
            return False
        locked_by = row[0] or ""
        return locked_by == worker_id
