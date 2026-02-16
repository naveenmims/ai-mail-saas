import json
from typing import Any, Dict, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError


def _ensure_org_credits_row(conn, org_id: int) -> None:
    """
    Ensure org_credits row exists for this org.
    Uses Postgres ON CONFLICT DO NOTHING (NOT SQLite syntax).
    """
    conn.execute(
        text(
            """
            INSERT INTO org_credits (org_id, plan, credits_total, credits_used, credits_reset_at, updated_at)
            VALUES (:oid, 'free', 100, 0, CURRENT_DATE, NOW())
            ON CONFLICT (org_id) DO NOTHING
            """
        ),
        {"oid": org_id},
    )


def _reset_if_needed(conn, org_id: int) -> None:
    """
    If credits_reset_at < today, reset used credits to 0 and set credits_reset_at=today.
    """
    conn.execute(
        text(
            """
            UPDATE org_credits
            SET credits_used = 0,
                credits_reset_at = CURRENT_DATE,
                updated_at = NOW()
            WHERE org_id = :oid
              AND credits_reset_at IS NOT NULL
              AND credits_reset_at < CURRENT_DATE
            """
        ),
        {"oid": org_id},
    )


def get_remaining_credits(engine: Engine, org_id: int) -> int:
    """
    Returns remaining credits. Auto-creates org_credits row if missing.
    """
    try:
        with engine.begin() as conn:
            _ensure_org_credits_row(conn, org_id)
            _reset_if_needed(conn, org_id)

            row = conn.execute(
                text(
                    """
                    SELECT (credits_total - credits_used) AS remaining
                    FROM org_credits
                    WHERE org_id = :oid
                    """
                ),
                {"oid": org_id},
            ).fetchone()

            if not row or row[0] is None:
                return 0
            return int(row[0])
    except SQLAlchemyError:
        # Never leave transactions hanging; engine.begin() already rolls back on exception.
        return 0


def consume_credits(engine: Engine, org_id: int, qty: int = 1) -> bool:
    """
    Atomically consume credits if available.
    Returns True if consumed, False if insufficient or error.
    """
    qty = int(qty or 0)
    if qty <= 0:
        return True

    try:
        with engine.begin() as conn:
            _ensure_org_credits_row(conn, org_id)
            _reset_if_needed(conn, org_id)

            res = conn.execute(
                text(
                    """
                    UPDATE org_credits
                    SET credits_used = credits_used + :qty,
                        updated_at = NOW()
                    WHERE org_id = :oid
                      AND (credits_total - credits_used) >= :qty
                    """
                ),
                {"oid": org_id, "qty": qty},
            )
            return (res.rowcount or 0) == 1
    except SQLAlchemyError:
        return False


def log_usage(
    engine: Engine,
    org_id: int,
    event: str,
    qty: int = 1,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Insert a usage event. MUST NOT leave aborted transactions behind.
    """
    event = (event or "").strip()
    if not event:
        return

    qty = int(qty or 0)
    if qty <= 0:
        qty = 1

    meta_json = json.dumps(meta or {}, ensure_ascii=False)

    try:
        with engine.begin() as conn:
            # Do NOT insert id. Let Postgres sequence generate it.
            conn.execute(
                text(
                    """
                    INSERT INTO org_usage (org_id, event, qty, meta, created_at)
                    VALUES (:oid, :event, :qty, CAST(:meta AS JSONB), NOW())
                    """
                ),
                {"oid": org_id, "event": event, "qty": qty, "meta": meta_json},
            )
    except SQLAlchemyError:
        # Swallow logging errors; but engine.begin() already rolled back safely.
        return
