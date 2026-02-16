import os
import re
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from fastapi import APIRouter, Header, HTTPException, Query

router = APIRouter(tags=["admin-analytics"])

def require_admin(x_admin_token: str | None, authorization: str | None):
    expected = os.getenv("ADMIN_TOKEN", "")
    token = x_admin_token

    if (not token) and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()

    if not expected or token != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")

def logs_dir() -> Path:
    # backend/logs
    return Path(__file__).resolve().parents[1] / "logs"

LOG_LINE_TS = re.compile(r"^(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})")
ORG_HINT = re.compile(r"\b(org|tenant|workspace|company|brand)\b[:= ]+([A-Za-z0-9_.\-@]+)", re.IGNORECASE)
CREDITS_HINT = re.compile(r"\bcredits?\b[:= ]+(\d+)", re.IGNORECASE)
EMAIL_PROCESSED = re.compile(r"\bevent=email_processed\b|\b(processed|replied|sent)\b.*\bemail\b", re.IGNORECASE)
ERROR_HINT = re.compile(r"\b(ERROR|Exception|Traceback)\b", re.IGNORECASE)

def _parse_time(line: str) -> datetime | None:
    m = LOG_LINE_TS.search(line)
    if not m:
        return None
    s = m.group(1).replace("T", " ")
    # assume local time if no tz info in log; convert to UTC naive-ish
    try:
        dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)  # treat as UTC (good enough for admin analytics)
    except Exception:
        return None

def _pick_files(days: int) -> List[Path]:
    d = logs_dir()
    files = []
    # Prefer daily logs if present
    for i in range(days):
        day = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y%m%d")
        p = d / f"worker_{day}.log"
        if p.exists():
            files.append(p)
    # Fallback: worker.log (rolling)
    roll = d / "worker.log"
    if roll.exists():
        files.append(roll)
    # Deduplicate
    seen = set()
    out = []
    for f in files:
        if str(f) not in seen:
            out.append(f)
            seen.add(str(f))
    return out

def _aggregate_from_logs(days: int) -> Dict[str, Any]:
    per_org: Dict[str, Dict[str, Any]] = {}
    totals = {"emails": 0, "errors": 0, "credits": 0}

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    for f in _pick_files(days):
        try:
            for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
                ts = _parse_time(line)
                if ts and ts < cutoff:
                    continue

                org = "unknown"
                m_org = ORG_HINT.search(line)
                if m_org:
                    org = m_org.group(2)

                bucket = per_org.setdefault(org, {
                    "emails": 0,
                    "errors": 0,
                    "credits": 0,
                    "last_seen_utc": None,
                    "last_error": None,
                    "sources": set(),
                })
                bucket["sources"].add(f.name)

                if ts:
                    prev = bucket["last_seen_utc"]
                    if (prev is None) or (ts > prev):
                        bucket["last_seen_utc"] = ts

                # credits
                m_c = CREDITS_HINT.search(line)
                if m_c:
                    c = int(m_c.group(1))
                    bucket["credits"] += c
                    totals["credits"] += c

                # emails
                if EMAIL_PROCESSED.search(line):
                    bucket["emails"] += 1
                    totals["emails"] += 1

                # errors
                if ERROR_HINT.search(line):
                    bucket["errors"] += 1
                    totals["errors"] += 1
                    bucket["last_error"] = line[-300:]  # keep it short
        except Exception:
            # ignore unreadable file
            continue

    # finalize
    org_list = []
    for org, b in per_org.items():
        org_list.append({
            "org": org,
            "emails": b["emails"],
            "errors": b["errors"],
            "credits": b["credits"],
            "last_seen_utc": b["last_seen_utc"].isoformat() if b["last_seen_utc"] else None,
            "last_error": b["last_error"],
            "log_files": sorted(list(b["sources"])),
        })
    org_list.sort(key=lambda x: (x["errors"], x["emails"]), reverse=True)

    return {
        "days": days,
        "cutoff_utc": cutoff.isoformat(),
        "totals": totals,
        "orgs": org_list,
        "log_files_used": [p.name for p in _pick_files(days)],
    }

@router.get("/admin/analytics/summary")
def admin_analytics_summary(
    days: int = Query(default=7, ge=1, le=90),
    x_admin_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
):
    require_admin(x_admin_token, authorization)
    return _aggregate_from_logs(days)

@router.get("/admin/analytics/raw-tail")
def admin_analytics_raw_tail(
    lines: int = Query(default=200, ge=10, le=5000),
    x_admin_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
):
    require_admin(x_admin_token, authorization)
    p = logs_dir() / f"worker_{datetime.now(timezone.utc).strftime('%Y%m%d')}.log"
    if not p.exists():
        p = logs_dir() / "worker.log"
    if not p.exists():
        return {"ok": False, "error": "No log file found"}
    all_lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    return {"ok": True, "file": p.name, "tail": all_lines[-lines:]}
