from datetime import datetime, timezone, timedelta
from app.db import SessionLocal
from app.models import Organization

ALLOWED_STATUSES = {"active", "trialing"}

def utcnow():
    return datetime.now(timezone.utc)

def main():
    db = SessionLocal()
    now = utcnow()

    # Reset any org whose credits_reset_at is due
    orgs = (
        db.query(Organization)
        .filter(Organization.credits_reset_at.isnot(None))
        .all()
    )

    changed = 0
    for org in orgs:
        status = (org.subscription_status or "").lower()
        if status not in ALLOWED_STATUSES:
            continue

        reset_at = org.credits_reset_at
        if reset_at and reset_at <= now:
            monthly = int(org.credits_monthly or 0)
            if monthly <= 0:
                # safety default for paid orgs if not set
                monthly = 100

            org.credits_balance = monthly
            org.last_credit_reset_at = now
            # naive 30-day cycle; later we anchor to Stripe billing period
            org.credits_reset_at = now + timedelta(days=30)
            changed += 1

    if changed:
        db.commit()

    db.close()
    print(f"credits_reset_done changed={changed}")

if __name__ == "__main__":
    main()
