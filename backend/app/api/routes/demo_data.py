import os
import random
import hashlib
from typing import Optional
from datetime import datetime, timedelta, timezone, time

from fastapi import APIRouter, Header, HTTPException

router = APIRouter(tags=["demo"])

def _require_demo(x_demo_token: Optional[str] = None) -> None:
    if os.getenv("DEMO_MODE", "0") != "1":
        raise HTTPException(status_code=404, detail="Not found")

    expected = os.getenv("DEMO_TOKEN", "").strip()
    if expected:
        if not x_demo_token or x_demo_token != expected:
            raise HTTPException(status_code=404, detail="Not found")

def _daily_seed() -> int:
    """
    Deterministic seed that changes once per UTC day.
    """
    org = os.getenv("DEMO_ORG_NAME", "BookURL Demo").strip()
    salt = os.getenv("DEMO_DASHBOARD_SALT", "v1").strip()
    today = datetime.now(timezone.utc).date().isoformat()
    raw = f"{org}|{today}|{salt}".encode("utf-8")
    digest = hashlib.sha256(raw).digest()
    return int.from_bytes(digest[:8], "big", signed=False)

@router.get("/demo/dashboard")
def demo_dashboard(x_demo_token: Optional[str] = Header(default=None, alias="X-Demo-Token")):
    _require_demo(x_demo_token)

    rng = random.Random(_daily_seed())

    now = datetime.now(timezone.utc)
    base = datetime.combine(now.date(), time(12, 0), tzinfo=timezone.utc)  # stable within the day

    emails_today = rng.randint(18, 46)
    replied_today = rng.randint(12, emails_today)
    credits_used_7d = rng.randint(120, 420)

    trend = []
    for i in range(7):
        day_dt = (base - timedelta(days=6 - i))
        day = day_dt.date().isoformat()
        inbound = rng.randint(20, 60)
        replied = rng.randint(10, inbound)
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
        ts = (base - timedelta(minutes=15 * i)).isoformat()
        recent.append({
            "when": ts,
            "from": f"customer{i+1}@example.com",
            "subject": rng.choice(subjects),
            "status": rng.choice(["replied", "queued", "needs-human"]),
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
