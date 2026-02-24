from datetime import datetime, timedelta, timezone
from sqlalchemy import text

def _utcnow():
    return datetime.now(timezone.utc)

def _bucket_start(dt: datetime, cooldown_seconds: int) -> datetime:
    # bucket by cooldown_seconds in UTC (e.g., 600 sec = 10 min)
    ts = int(dt.timestamp())
    bucket = ts - (ts % cooldown_seconds)
    return datetime.fromtimestamp(bucket, tz=timezone.utc)

def try_acquire_thread_lock(engine, org_id: int, thread_key: str, cooldown_seconds: int, worker_id: str, ttl_seconds: int) -> bool:
    now = _utcnow()
    bucket_start = _bucket_start(now, cooldown_seconds)
    expires_at = now + timedelta(seconds=ttl_seconds)

    with engine.begin() as conn:
        # 1) Cleanup expired locks (keeps table small + prevents stale blocks)
        conn.execute(text("""
            DELETE FROM reply_thread_locks
            WHERE expires_at IS NOT NULL
              AND expires_at <= :now
        """), {"now": now.isoformat()})

        # 2) Try insert (unique index enforces single row per bucket)
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
                 params
             ) {
                "org_id": org_id,
                "thread_key": thread_key,
                "bucket_start": bucket_start.isoformat(),
                "worker_id": worker_id,
                "expires_at": expires_at.isoformat(),
            })
            return True
        except Exception:
            # 3) If already exists, allow same worker to re-enter (idempotent)
            row = conn.execute(text("""
                SELECT worker_id, expires_at
                FROM reply_thread_locks
                WHERE org_id=:org_id AND thread_key=:thread_key
                LIMIT 1
            """), {"org_id": org_id, "thread_key": thread_key}).mappings().first()
            
            if not row:
                return False
            
            # If we wrote the row, worker_id should match.
            return row["worker_id"] == worker_id

            locked_by = (row[0] or "")
            # if same worker_id, allow
            if locked_by == worker_id:
                return True

            return False
