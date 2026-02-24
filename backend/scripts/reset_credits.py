import os, sys
from datetime import datetime, timezone, timedelta
from sqlalchemy import text

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.db import SessionLocal

ALLOWED_STATUSES = {"active", "trialing"}

def utcnow():
    return datetime.now(timezone.utc)

def main():
    db = SessionLocal()
    now = utcnow()
    changed = 0

    rows = db.execute(text("""
        SELECT id, subscription_status, credits_monthly, credits_reset_at
        FROM organizations
        WHERE credits_reset_at IS NOT NULL
          AND credits_reset_at <= :now
    """), {"now": now}).mappings().all()

    for r in rows:
        status = (r.get("subscription_status") or "").lower()
        if status not in ALLOWED_STATUSES:
            continue

        monthly = int(r.get("credits_monthly") or 0)
        if monthly <= 0:
            monthly = 100

        db.execute(text("""
            UPDATE organizations
            SET credits_monthly = :monthly,
                credits_balance = :monthly,
                last_credit_reset_at = :now,
                credits_reset_at = :next_reset
            WHERE id = :id
        """), {
            "id": r["id"],
            "monthly": monthly,
            "now": now,
            "next_reset": now + timedelta(days=30),
        })
        changed += 1

    if changed:
        db.commit()

    db.close()
    print(f"done changed={changed}")

if __name__ == "__main__":
    main()
