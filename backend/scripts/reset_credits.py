import os, sys
from datetime import datetime, timezone, timedelta

# Ensure /opt/ai-mail/backend is on sys.path so "import app" works
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../backend
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.db import SessionLocal
from app.models import Organization

ALLOWED_STATUSES = {"active", "trialing"}

def utcnow():
    return datetime.now(timezone.utc)

def main():
    db = SessionLocal()
    now = utcnow()
    changed = 0

    orgs = (
        db.query(Organization)
        .filter(Organization.credits_reset_at.isnot(None))
        .all()
    )

    for org in orgs:
        status = (org.subscription_status or "").lower()
        if status not in ALLOWED_STATUSES:
            continue

        if org.credits_reset_at and org.credits_reset_at <= now:
            monthly = int(org.credits_monthly or 0)
            if monthly <= 0:
                monthly = 100

            org.credits_monthly = monthly
            org.credits_balance = monthly
            org.last_credit_reset_at = now
            org.credits_reset_at = now + timedelta(days=30)
            changed += 1

    if changed:
        db.commit()

    db.close()
    print(f"done changed={changed}")

if __name__ == "__main__":
    main()
