import os
import random
from typing import Optional
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Header, HTTPException

router = APIRouter(tags=["demo"])

def _require_demo(x_demo_token: Optional[str] = None) -> None:
    if os.getenv("DEMO_MODE", "0") != "1":
        raise HTTPException(status_code=404, detail="Not found")

    expected = os.getenv("DEMO_TOKEN", "").strip()
    if expected:
        if not x_demo_token or x_demo_token != expected:
            raise HTTPException(status_code=404, detail="Not found")

@router.get("/demo/dashboard")
def demo_dashboard(x_demo_token: Optional[str] = Header(default=None, alias="X-Demo-Token")):
    _require_demo(x_demo_token)

    now = datetime.now(timezone.utc)

    emails_today = random.randint(18, 46)
    replied_today = random.randint(12, emails_today)
    credits_used_7d = random.randint(120, 420)

    trend = []
    for i in range(7):
        day = (now - timedelta(days=6 - i)).date().isoformat()
        inbound = random.randint(20, 60)
        replied = random.randint(10, inbound)
        trend.append({"day": day, "inbound": inbound, "replied": replied})

    subjects = [
        "Course fees and admission details",
        "Need invoice for last payment",
        "Request for callback",
        "Query about services and pricing",
        "Unable to login – help",
    ]
    recent = []
    for i in range(8):
        ts = (now - timedelta(minutes=15 * i)).isoformat()
        recent.append({
            "when": ts,
            "from": f"customer{i+1}@example.com",
            "subject": random.choice(subjects),
            "status": random.choice(["replied", "queued", "needs-human"]),
        })

    return {
        "org_name": os.getenv("DEMO_ORG_NAME", "BookURL Demo"),
        "kpis": {
            "emails_today": emails_today,
            "auto_replied_today": replied_today,
            "credits_used_last_7d": credits_used_7d,
        },
        "trend_7d": trend,
        "recent": recent,
    }
