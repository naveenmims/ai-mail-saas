from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

def _utcnow():
    return datetime.now(timezone.utc)

def _bucket_start(dt: datetime, cooldown_seconds: int) -> datetime:
    ts = int(dt.timestamp())
    bucket = ts - (ts % cooldown_seconds)
    return datetime.fromtimestamp(bucket, tz=timezone.utc)

def try_acquire_thread_lock(engine, org_id: int, thread_key: str, cooldown_seconds: int, worker_id: str, ttl_seconds: int) -> bool:
    now = _utcnow()
    bucket_start = _bucket_start(now, cooldown_seconds)
    expires_at = now + timedelta(seconds=ttl_seconds)

    params = {
        "org_id": org_id,
        "thread_key": thread_key,
        "bucket_start": bucket_start.isoformat(),
        "worker_id": worker_id,
        "expires_at": expires_at.isoformat(),
    }

    with engine.begin() as conn:
        # Cleanup expired locks
        conn.execute(text("""
            DELETE FROM reply_thread_locks
            WHERE expires_at IS NOT NULL
              AND expires_at <= now()
        """))

        # Acquire / takeover if expired
        try:
            conn.execute(
                text("""
                    INSERT INTO reply_thread_locks (org_id, thread_key, bucket_start, worker_id, expires_at)
                    VALUES (:org_id, :thread_key, :bucket_start, :worker_id, :expires_at)
                    ON CONFLICT (org_id, thread_key)
                    DO UPDATE SET
                        bucket_start = EXCLUDED.bucket_start,
                        worker_id    = EXCLUDED.worker_id,
                        expires_at   = EXCLUDED.expires_at
                    WHERE reply_thread_locks.expires_at < now()
                """),
                params,
            )
        except IntegrityError:
            return False

        # Verify we own the lock
        row = conn.execute(text("""
            SELECT worker_id
            FROM reply_thread_locks
            WHERE org_id=:org_id AND thread_key=:thread_key
            LIMIT 1
        """), {"org_id": org_id, "thread_key": thread_key}).mappings().first()

        if not row:
            return False

        return (row.get("worker_id") or "") == worker_id
