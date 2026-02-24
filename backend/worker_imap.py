"""
worker_imap.py (Postgres-only / C3)

✅ What changed (without breaking behavior):
- Removed all SQLite reads/writes (ai_mail.db) and replaced with Postgres queries.
- Fixed SQLite-only datetime syntax in replies_sent_last_hour() -> Postgres interval.
- get_org_settings(), cooldown checks, thread context now come from Postgres (organizations + conversation_audit).
- store_conversation() / store_reply_log() kept as NO-OP to avoid disturbing call sites.

Everything else (IMAP filtering, OpenAI, locks, billing, observability) stays the same.
"""

from dotenv import load_dotenv

load_dotenv()

import os
import sys
import re
import hashlib
import time
import imaplib
import smtplib
import uuid
import socket
import traceback
import logging
from datetime import datetime
from pathlib import Path
from email import message_from_bytes
from email.policy import default
from email.message import EmailMessage

from openai import OpenAI

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db import engine, SessionLocal
from app.services.billing_guard import get_remaining_credits, consume_credits, log_usage
from app.services.observability import upsert_worker_status, log_conversation, now_utc
from app.models import Organization, EmailAccount

POLL_SECONDS = int(os.getenv("POLL_SECONDS", "60"))

# --- Windows/Console UTF-8 safety (prevents UnicodeEncodeError) ---
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
# ------------------------------------------------------------------

DEBUG = os.getenv("DEBUG", "0") == "1"

# Stable worker id (override via env if you want)
WORKER_ID = os.getenv("WORKER_ID") or f"{socket.gethostname()}-{os.getpid()}-{str(uuid.uuid4())[:6]}"

INBOX_FOLDER = "INBOX"
SCAN_LAST_N = 30  # scan last N emails for a non-marketing one (reduce load)

# ---------- logging (analytics-friendly) ----------
LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
TODAY = datetime.now().strftime("%Y%m%d")

logger = logging.getLogger("ai_mail_worker")
logger.setLevel(logging.INFO)

if not logger.handlers:
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    daily_path = os.path.join(LOGS_DIR, f"worker_{TODAY}.log")
    rolling_path = os.path.join(LOGS_DIR, "worker.log")

    fh1 = logging.FileHandler(daily_path, encoding="utf-8")
    fh1.setFormatter(fmt)
    logger.addHandler(fh1)

    fh2 = logging.FileHandler(rolling_path, encoding="utf-8")
    fh2.setFormatter(fmt)
    logger.addHandler(fh2)
# -----------------------------------------------

# ✅ Marketing/newsletter-only keywords.
# IMPORTANT: Do NOT put "signin/login/otp/password" here (they appear in normal email footers).
IGNORE_KEYWORDS = [
    "unsubscribe", "manage preferences", "preference center", "view in browser",
    "nurture", "campaign", "offer", "promotion", "newsletter",
    "webinar", "join us", "register", "event", "summit",
    "do not reply", "no reply", "noreply", "donotreply",
    "privacy policy", "powered by", "email preferences", "mailing list",
]

# ✅ Bulk sender patterns (domains / platforms)
IGNORE_SENDERS = [
    "no-reply", "noreply", "donotreply", "mailer-daemon", "postmaster",
    "bounce@", "secureserver.net", "go.", "marketing@", "news@", "updates@",
    "sender-sib.com", "sibmail.com", "sendinblue", "brevo",
    "sender-sib", "sendib", "mailchimp", "sendgrid.net", "campaign-", "email.",
]

# ---------- helpers ----------
def read_text_file(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8", errors="ignore").strip()


def safe_decode(b) -> str:
    try:
        return b.decode(errors="ignore")
    except Exception:
        return ""

ALLOWED_STATUSES = {"active", "trialing"}

def org_can_process(org) -> tuple[bool, str]:
    status = (getattr(org, "subscription_status", "") or "").lower()
    credits = int(getattr(org, "credits_balance", 0) or 0)

    if status not in ALLOWED_STATUSES:
        return False, f"blocked: subscription_status={status}"
    if credits <= 0:
        return False, f"blocked: credits_balance={credits}"
    return True, "ok"


def norm_mid(mid: str | None) -> str | None:
    if not mid:
        return None
    mid = mid.strip().lower()
    if mid.startswith("<") and mid.endswith(">"):
        mid = mid[1:-1].strip()
    return mid


def extract_email(from_header: str) -> str:
    """
    Returns the email part from a From header.
    Example: 'Name <a@b.com>' -> 'a@b.com'
    """
    if not from_header:
        return ""
    m = re.search(r"<([^>]+)>", from_header)
    if m:
        return m.group(1).strip()
    return from_header.strip().strip('"')


def is_ignored_email(text_lower: str) -> bool:
    """
    Pass lowercase text. Returns True if it's marketing/system based on static lists.
    """
    if not text_lower:
        return False
    if any(k in text_lower for k in IGNORE_KEYWORDS):
        return True
    if any(s in text_lower for s in IGNORE_SENDERS):
        return True
    return False


def is_security_alert_email(subject: str, body: str, raw_headers) -> bool:
    """
    STRICT system/security filter.
    Return True only when we are highly confident the message is automated security/system noise
    (bounces, delivery reports, auto-generated alerts, list mail).
    """
    subj = (subject or "").lower()
    text_ = (body or "").lower()

    # raw_headers can be dict-like or string; normalize
    try:
        hdr_str = "\n".join([f"{k}: {v}" for k, v in (raw_headers or {}).items()]).lower()
    except Exception:
        hdr_str = str(raw_headers or "").lower()

    combined = f"{subj}\n{text_}\n{hdr_str}"

    # Strong automated/system signals (headers)
    auto_header_signals = (
        "auto-submitted: auto-generated" in combined
        or "auto-submitted: auto-replied" in combined
        or "x-autoreply" in combined
        or "x-auto-response-suppress" in combined
        or "precedence: bulk" in combined
        or "precedence: junk" in combined
        or "precedence: list" in combined
        or "list-id:" in combined
        or "list-unsubscribe:" in combined
        or "feedback-id:" in combined
    )

    # Bounce / DSN / delivery failure patterns
    bounce_signals = (
        "mailer-daemon" in combined
        or "postmaster@" in combined
        or "delivery status notification" in combined
        or "undelivered mail" in combined
        or "returned mail" in combined
        or "diagnostic-code:" in combined
        or "final-recipient:" in combined
        or "x-failed-recipients:" in combined
        or "report-type=delivery-status" in combined
        or "message/delivery-status" in combined
    )

    # Security-alert style keywords (NOT enough alone to skip)
    security_keywords = (
        "security alert" in combined
        or "suspicious sign" in combined
        or "new sign-in" in combined
        or "new login" in combined
        or "unusual activity" in combined
        or "verify your account" in combined
        or "password reset" in combined
        or "reset your password" in combined
        or "2-step verification" in combined
        or "two-step verification" in combined
        or "verification code" in combined
        or "one-time password" in combined
        or "otp" in combined
    )

    # The key rule:
    # - Always skip bounces/DSNs
    # - Skip security alerts ONLY if also auto-generated (headers) or clearly bulk/list
    if bounce_signals:
        return True

    if security_keywords and auto_header_signals:
        return True

    return False


def is_trusted_sender(sender_email: str, org_settings: dict) -> bool:
    """
    Allow bypass of security/system filter for trusted senders.
    - Org support_email (if set)
    - Org domain (from website or support_email)
    """
    se = (sender_email or "").strip().lower()
    if not se or "@" not in se:
        return False

    trusted = set()

    support_email = (org_settings.get("support_email") or "").strip().lower()
    if support_email and "@" in support_email:
        trusted.add(support_email)

    website = (org_settings.get("website") or org_settings.get("website_url") or "").strip().lower()
    org_domain = ""
    if "://" in website:
        org_domain = website.split("://", 1)[1].split("/", 1)[0]
    elif website:
        org_domain = website.split("/", 1)[0]

    if support_email and "@" in support_email:
        org_domain = support_email.split("@", 1)[1]

    org_domain = (org_domain or "").replace("www.", "").strip()
    if org_domain:
        if se.endswith("@" + org_domain):
            return True

    return se in trusted


def get_body_text(msg) -> str:
    """
    Prefer plain text. Avoid attachments.
    """
    try:
        body_part = msg.get_body(preferencelist=("plain",))
        if body_part:
            return body_part.get_content() or ""
    except Exception:
        pass

    try:
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                disp = str(part.get("Content-Disposition") or "").lower()
                if "attachment" in disp:
                    continue
                if ctype == "text/plain":
                    return part.get_content() or ""
        else:
            return msg.get_content() or ""
    except Exception:
        pass

    return ""


# ---------------------- Postgres-backed settings / history ----------------------
def get_org_settings(org_id: int) -> dict:
    """
    Load org settings from Postgres (organizations).
    Keeps same return keys as old SQLite function, to avoid breaking logic.
    """
    with SessionLocal() as db:
        org = db.query(Organization).filter(Organization.id == org_id).first()

    if not org:
        return {
            "org_name": f"Org{org_id}",
            "support_name": f"Tenant{org_id} Support",
            "support_email": "",
            "website": "",
            "website_url": "",
            "kb_text": "",
            "system_prompt": "",
            "auto_reply": 1,
            "auto_reply_enabled": 1,
            "max_replies_per_hour": 10,
            "cooldown_hours": 24,
        }

    return {
        "org_name": (org.name or f"Org{org_id}"),
        "support_name": (getattr(org, "support_name", None) or f"Tenant{org_id} Support"),
        "support_email": (getattr(org, "support_email", None) or ""),
        "website": (getattr(org, "website", None) or ""),
        "website_url": (getattr(org, "website_url", None) or ""),
        "kb_text": (getattr(org, "kb_text", None) or ""),
        "system_prompt": (getattr(org, "system_prompt", None) or ""),
        "auto_reply": int(getattr(org, "auto_reply", 1) or 1),
        "auto_reply_enabled": 1 if bool(getattr(org, "auto_reply_enabled", True)) else 0,
        "max_replies_per_hour": int(getattr(org, "max_replies_per_hour", 10) or 10),
        "cooldown_hours": int(getattr(org, "cooldown_hours", 24) or 24),
    }


def replies_sent_last_hour(org_id: int) -> int:
    """
    Count replies in last 60 minutes using org_usage table (Postgres).
    """
    try:
        with engine.connect() as conn:
            res = conn.execute(
                text(
                    """
                    SELECT COALESCE(SUM(qty), 0)
                    FROM org_usage
                    WHERE org_id = :oid
                      AND event = 'reply_sent'
                      AND created_at >= (NOW() AT TIME ZONE 'utc') - INTERVAL '1 hour'
                    """
                ),
                {"oid": org_id},
            ).scalar_one()
        return int(res or 0)
    except Exception:
        return 0


SUBJECT_PREFIX_RE = re.compile(r"^\s*((re|fw|fwd)\s*:\s*)+", re.IGNORECASE)


def normalize_subject(s: str) -> str:
    s = (s or "").strip()
    s = SUBJECT_PREFIX_RE.sub("", s).strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s[:180]


def extract_msgids(refs_header: str):
    if not refs_header:
        return []
    return re.findall(r"<[^>]+>", refs_header)


def make_thread_key(
    org_id: int,
    sender_email: str,
    subject: str,
    in_reply_to: str | None,
    references: str | None,
) -> str:
    if in_reply_to:
        return f"m:{in_reply_to.strip()}"
    refs = extract_msgids(references or "")
    if refs:
        return f"m:{refs[-1].strip()}"

    ns = normalize_subject(subject)
    raw = f"{org_id}|{(sender_email or '').strip().lower()}|{ns}"
    h = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    return f"s:{h}"


def replied_to_thread_recently(org_id: int, thread_key: str, hours: int) -> bool:
    """
    Cooldown check: uses conversation_audit OUT rows (Postgres).
    """
    if not thread_key:
        return False
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT 1
                    FROM conversation_audit
                    WHERE org_id = :oid
                      AND thread_key = :tkey
                      AND direction = 'OUT'
                      AND created_at >= (NOW() AT TIME ZONE 'utc') - (:hrs * INTERVAL '1 hour')
                    LIMIT 1
                    """
                ),
                {"oid": org_id, "tkey": thread_key, "hrs": int(hours)},
            ).fetchone()
        return bool(row)
    except Exception:
        return False


def replied_to_sender_recently(org_id: int, sender_email: str, hours: int) -> bool:
    """
    Cooldown check: uses conversation_audit OUT rows (Postgres).
    """
    sender_email = (sender_email or "").strip().lower()
    if not sender_email:
        return False
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT 1
                    FROM conversation_audit
                    WHERE org_id = :oid
                      AND lower(customer_email) = :email
                      AND direction = 'OUT'
                      AND created_at >= (NOW() AT TIME ZONE 'utc') - (:hrs * INTERVAL '1 hour')
                    LIMIT 1
                    """
                ),
                {"oid": org_id, "email": sender_email, "hrs": int(hours)},
            ).fetchone()
        return bool(row)
    except Exception:
        return False


def already_replied(org_id: int, message_id: str) -> bool:
    if not message_id:
        return False

    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT 1
                    FROM conversation_audit
                    WHERE org_id = :oid
                      AND email_message_id = :mid
                      AND direction = 'OUT'
                    LIMIT 1
                    """
                ),
                {"oid": org_id, "mid": message_id},
            ).fetchone()
        return bool(row)
    except Exception:
        return False


def thread_needs_reply(org_id: int, thread_key: str) -> bool:
    if not thread_key:
        return True

    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT
                        MAX(CASE WHEN direction = 'IN' THEN created_at END) AS last_in,
                        MAX(CASE WHEN direction = 'OUT' THEN created_at END) AS last_out
                    FROM conversation_audit
                    WHERE org_id = :oid
                      AND thread_key = :tkey
                    """
                ),
                {"oid": org_id, "tkey": thread_key},
            ).fetchone()

        if not row:
            return True

        last_in, last_out = row
        if last_out is None:
            return True
        if last_in and last_in > last_out:
            return True
        return False

    except Exception:
        return True


def mark_replied(org_id: int, message_id: str):
    """
    Deprecated in C3: we record replies via conversation_audit OUT rows.
    Kept as no-op for backward compatibility.
    """
    return


def mark_seen_by_relogin(a: EmailAccount, imap_host: str, imap_port: int, mid):
    """
    Because we logout before OpenAI (good), we re-login only to mark the chosen email as Seen.
    Prevents repeated re-processing load.
    """
    try:
        im = imaplib.IMAP4_SSL(imap_host, imap_port)
        im.login(a.imap_username, a.imap_password)
        im.select(INBOX_FOLDER)
        im.store(mid, "+FLAGS", "\\Seen")
        im.logout()
    except Exception:
        pass


def send_smtp_safe(a: EmailAccount, to_email: str, subject: str, body: str) -> bool:
    if not to_email:
        return False

    msg_out = EmailMessage()
    msg_out["From"] = a.email
    msg_out["To"] = to_email
    msg_out["Subject"] = subject
    msg_out.set_content(body)

    for attempt in range(3):
        try:
            print(f"SMTP attempt {attempt+1}/3")
            with smtplib.SMTP("smtpout.secureserver.net", 587, timeout=60) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                time.sleep(1)
                smtp.login(a.email, a.imap_password)
                time.sleep(1)
                smtp.send_message(msg_out)
            print("SMTP SUCCESS")
            return True
        except Exception as e:
            print("SMTP ERROR:", repr(e))
            time.sleep(3)

    return False


def load_thread_context(org_id: int, thread_key: str, limit: int = 6) -> str:
    """
    Thread context from Postgres conversation_audit (keeps similar formatting).
    """
    if not thread_key:
        return ""

    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT direction, body_text, created_at
                    FROM conversation_audit
                    WHERE org_id = :oid AND thread_key = :tkey
                    ORDER BY created_at DESC
                    LIMIT :lim
                    """
                ),
                {"oid": org_id, "tkey": thread_key, "lim": int(limit) * 2},  # IN+OUT
            ).fetchall()

        if not rows:
            return ""

        rows = list(reversed(rows))
        chunks = []
        i = 1
        pending_in = None
        pending_time = None

        for direction, body_text, created_at in rows:
            bt = (body_text or "").strip()
            ts = str(created_at) if created_at else ""
            if direction == "IN":
                pending_in = bt
                pending_time = ts
            elif direction == "OUT":
                cust = (pending_in or "").strip()
                ai = bt
                if cust or ai:
                    chunks.append(
                        f"[{i}] ({pending_time or ts})\nCustomer:\n{cust[:1200]}\n\nAssistant:\n{ai[:1200]}\n"
                    )
                    i += 1
                pending_in = None
                pending_time = None

        # If we ended on an IN without OUT yet:
        if pending_in:
            chunks.append(
                f"[{i}] ({pending_time or ''})\nCustomer:\n{pending_in[:1200]}\n\nAssistant:\n(pending)\n"
            )

        return "\n".join(chunks).strip()
    except Exception:
        return ""


# Keep these as no-op to avoid disturbing old flow/call sites.
def store_conversation(*args, **kwargs):
    return


def store_reply_log(*args, **kwargs):
    return


def search_candidate_ids(imap) -> list:
    try:
        st, msg = imap.search(None, "UNSEEN")
        if st == "OK" and msg and msg[0]:
            ids = msg[0].split()
            if ids:
                return ids
    except Exception:
        pass

    st, msg = imap.search(None, "ALL")
    if st != "OK" or not msg or not msg[0]:
        return []
    return msg[0].split()


# ---------- main ----------
replied_mids_this_run = set()
replied_threads_this_run = set()


def is_real_enquiry(
    subject: str,
    sender: str,
    body: str,
    raw_headers: str = "",
    trusted_sender: bool = False,
) -> bool:
    s = (subject or "").lower().strip()
    f = (sender or "").lower().strip()
    b = (body or "").lower().strip()
    h = (raw_headers or "").lower().strip()

    combined = "\n".join([s, f, h, b])
    combined_h = "\n".join([s, f, h])

    # debug reason tracker
    is_real_enquiry.last_reason = ""

    # Bulk signals: check ONLY subject+from+headers (NOT body)
    bulk_signals = [
        "list-unsubscribe", "list-id", "list-help", "list-post",
        "unsubscribe", "manage preferences", "view in browser",
        "you are receiving this email because", "email preferences",
        "newsletter", "promotion", "campaign", "marketing",
    ]
    hit = next((x for x in bulk_signals if x in combined_h), None)
    if hit and (not trusted_sender):
        is_real_enquiry.last_reason = f"bulk:{hit}"
        return False

    # Strict security/system filter (bypass for trusted)
    if (not trusted_sender) and is_security_alert_email(subject, body, raw_headers):
        is_real_enquiry.last_reason = "security_alert"
        return False

    # Static ignore lists (keywords + senders). This checks combined (includes body)
    ignored = is_ignored_email(combined)
    if DEBUG:
        print(f"[DEBUG is_real_enquiry] ignored={ignored} trusted_sender={trusted_sender}")

    if (not trusted_sender) and ignored:
        is_real_enquiry.last_reason = "ignored_static"
        return False

    # Subject contains enquiry-like signals
    if 3 <= len(s) <= 90:
        subject_signals = [
            "web", "website", "design", "developer", "consultant",
            "seo", "marketing", "app", "service", "quote", "pricing", "cost", "fees"
        ]
        if any(x in s for x in subject_signals):
            is_real_enquiry.last_reason = "ok"
            return True

    # Positive intent signals anywhere in combined
    positive = [
        "enquiry", "inquiry", "quote", "quotation", "estimate",
        "pricing", "price", "fees", "fee", "cost",
        "demo", "trial", "meeting", "schedule", "call", "callback",
        "support", "help", "issue", "problem", "error", "unable", "not working",
        "refund", "cancel",
        "admission", "join", "apply", "register",
        "need", "require", "looking for", "want to", "i want", "i need",
        "web design", "web developer", "developer", "consultant",
        "ui", "ux", "digital marketing", "branding", "app development",
    ]
    if any(p in combined for p in positive):
        is_real_enquiry.last_reason = "ok"
        return True

    # Human-ish short body with question
    if 20 <= len(b) <= 600:
        human_signals = ["hi", "hello", "dear", "please", "kindly", "thanks", "thank you"]
        if any(hs in b for hs in human_signals) or "?" in b:
            is_real_enquiry.last_reason = "ok"
            return True

    return False


def build_prompt(org_settings: dict, subject: str, sender: str, body: str, thread_context: str) -> tuple[str, str]:
    kb_text = (org_settings.get("kb_text") or "").strip()
    org_name = (org_settings.get("org_name") or org_settings.get("name") or "our institute").strip()
    support_name = (org_settings.get("support_name") or "Support Team").strip()
    support_email = (org_settings.get("support_email") or "").strip()
    website = (org_settings.get("website") or org_settings.get("website_url") or "").strip()
    base_sys = (org_settings.get("system_prompt") or "").strip()

    GLOBAL_BASE_SYSTEM_PROMPT = """
You are an AI email support assistant inside a multi-tenant SaaS platform.

NON-NEGOTIABLE RULES:
1) Use ONLY the provided Knowledge Base (KB) for factual answers (fees, duration, pricing, policies, contacts, addresses, timings, placements, refund, EMI).
2) If the requested information EXISTS in KB, you MUST answer it clearly.
3) If the exact detail is NOT in KB, ask 1–2 short clarification questions. Do NOT guess.
4) If the email is an OTP, invoice, login alert, newsletter, security notification, or automated system message → output exactly: SKIP_REPLY
5) Keep replies concise, structured, and actionable. Prefer bullet points.
""".strip()

    policy = f"""
You are the official email support assistant for {org_name}.

Hard rules:
- Use ONLY the Knowledge Base (KB) below for factual details such as courses, fees, duration, syllabus, schedules, admissions, contact, and address.
- If the exact fee or detail is not present in KB, do NOT guess. Clearly state that it is not listed and ask 1-2 specific follow-up questions.
- Never use placeholders. Address the user neutrally (Hello or Hi).
- Keep the reply concise (5-10 lines), clear, and helpful.
- End every reply exactly with:
  Best regards,
  {support_name}
  {support_email}
""".strip()

    system_prompt = (
        GLOBAL_BASE_SYSTEM_PROMPT
        + "\n\n"
        + base_sys
        + "\n\n"
        + policy
        + "\n\nKB:\n"
        + kb_text
    ).strip()

    user_prompt = f"""INCOMING EMAIL
Subject: {subject}
From: {sender}

Message:
{body}

ORG WEBSITE (reference only):
{website if website else "(not provided)"}

RECENT THREAD CONTEXT (latest first):
{thread_context if thread_context else "(none)"}

ORG KNOWLEDGE BASE (KB):
{kb_text if kb_text else "(not provided)"}
"""
    return system_prompt, user_prompt


def main():
    print("IMAP Worker started...\n")
    logger.info("event=test_log_created org=system credits=0")
    logger.info(f"event=worker_start worker_id={WORKER_ID}")

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Initial heartbeat
    db = SessionLocal()
    try:
        upsert_worker_status(
            db,
            worker_id=WORKER_ID,
            last_run_at=now_utc(),
            lock_health_ok=True,
            credits_health_ok=True,
            last_error=None,
        )
        db.commit()
    finally:
        db.close()

    with Session(engine) as db:
        accounts = (
            db.query(EmailAccount)
            .join(Organization, EmailAccount.org_id == Organization.id)
            .filter(Organization.auto_reply_enabled == True)
            .all()
        )
    print(f"[DEBUG] accounts_found={len(accounts)}")

    for a in accounts:
        org_id = int(a.org_id)
        org_settings = get_org_settings(org_id)
        cooldown_hours = int(org_settings.get("cooldown_hours", 24) or 24)
        org_name = org_settings.get("org_name", f"org_id={org_id}")
        org_slug = f"org{org_id}"

        print(f"[ORG] {org_name} cooldown={cooldown_hours}h")
        logger.info(f"event=org_cycle_start org={org_slug} org_name={org_name}")

        if not int(org_settings.get("auto_reply_enabled", 1)):
            print(f"Connecting IMAP: {a.imap_username}")
            print("Auto-reply disabled (enterprise toggle). Skipping.\n")
            continue
        if not int(org_settings.get("auto_reply", 1)):
            print(f"Connecting IMAP: {a.imap_username}")
            print("Auto-reply disabled (legacy flag). Skipping.\n")
            continue

        sent_last_hour = replies_sent_last_hour(org_id)
        max_per_hour = int(org_settings.get("max_replies_per_hour", 10) or 10)
        if sent_last_hour >= max_per_hour:
            print(f"Connecting IMAP: {a.imap_username}")
            print(f"Rate limited: {sent_last_hour}/{max_per_hour} replies in last hour. Skipping.\n")
            logger.info(f"event=rate_limited org={org_slug} sent_last_hour={sent_last_hour} max_per_hour={max_per_hour}")
            continue

        for attempt in range(1):
            imap = None
            chosen_mid = None
            message_id = ""
            thread_key = ""
            sender_email = ""
            subject = ""
            sender = ""
            body = ""
            in_reply_to = None
            references_header = ""
            chosen_hdr = ""
            smtp_ok = False
            reply = ""

            try:
                if attempt == 0:
                    print(f"Connecting IMAP: {a.imap_username}")
                else:
                    print(f"Retrying IMAP ({attempt+1}/1): {a.imap_username}")

                imap = imaplib.IMAP4_SSL(a.imap_host, a.imap_port)
                imap.login(a.imap_username, a.imap_password)
                imap.select(INBOX_FOLDER)

                ids = search_candidate_ids(imap)
                if not ids:
                    imap.logout()
                    print("No emails found.\n")
                    break

                # choose a non-marketing email based on headers
                for mid in reversed(ids[-SCAN_LAST_N:]):
                    st, hdrdata = imap.fetch(
                        mid,
                        "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE MESSAGE-ID REFERENCES IN-REPLY-TO LIST-UNSUBSCRIBE LIST-ID)])",
                    )
                    if not hdrdata or not isinstance(hdrdata[0], tuple):
                        continue
                    hdr = safe_decode(hdrdata[0][1]) or ""
                    if is_ignored_email(hdr.lower()):
                        continue
                    chosen_mid = mid
                    chosen_hdr = hdr
                    break

                if chosen_mid is None:
                    imap.logout()
                    print("No suitable (non-marketing/system) emails found.\n")
                    break

                st, data = imap.fetch(chosen_mid, "(BODY.PEEK[])")
                if not data or not isinstance(data[0], tuple):
                    imap.logout()
                    print("Failed to fetch email body.\n")
                    break

                msg = message_from_bytes(data[0][1], policy=default)

                subject = msg.get("Subject", "") or ""
                sender = msg.get("From", "") or ""
                message_id = (msg.get("Message-ID", "") or "").strip()
                message_id_n = norm_mid(message_id) or ""

                body = get_body_text(msg)
                sender_email = extract_email(sender)

                in_reply_to = (msg.get("In-Reply-To") or "").strip() or None
                references_header = (msg.get("References") or "").strip() or None

                thread_key = make_thread_key(org_id, sender_email, subject, in_reply_to, references_header)
                thread_key_n = (thread_key or "").strip().lower() if thread_key else ""

                print("\nSelected Email:")
                print("Subject:", subject)
                print("From:", sender)
                print("Message-ID:", message_id)
                print("Thread-Key:", thread_key)

                logger.info(f"event=email_selected org={org_slug} message_id={message_id_n} thread_key={thread_key}")

                hdr_combo = f"{subject}\n{sender}\n{message_id}".lower()
                if is_ignored_email(hdr_combo):
                    print("Ignored (marketing/system email) — Skipping.\n")
                    imap.logout()
                    break

                # Per-message-id de-dupe (DB) early
                if message_id_n and already_replied(org_id, message_id_n):
                    print("Already replied to this Message-ID. Skipping send.\n")
                    try:
                        imap.store(chosen_mid, "+FLAGS", "\\Seen")
                    except Exception:
                        pass
                    try:
                        imap.logout()
                    except Exception:
                        pass
                    break

                # In-run de-dupe
                if message_id_n and message_id_n in replied_mids_this_run:
                    print("[SKIP] already replied (this run) message_id", message_id_n)
                    try:
                        imap.store(chosen_mid, "+FLAGS", "\\Seen")
                    except Exception:
                        pass
                    imap.logout()
                    break
                if thread_key_n and thread_key_n in replied_threads_this_run:
                    print("[SKIP] already replied (this run) thread", thread_key_n)
                    try:
                        imap.store(chosen_mid, "+FLAGS", "\\Seen")
                    except Exception:
                        pass
                    imap.logout()
                    break

                # Thread cooldown (Postgres)
                if replied_to_thread_recently(org_id, thread_key, hours=cooldown_hours):
                    print(
                        f"Cooldown(thread): already replied in last {cooldown_hours}h "
                        f"for {sender_email} thread={thread_key}. Skipping.\n"
                    )
                    try:
                        imap.store(chosen_mid, "+FLAGS", "\\Seen")
                    except Exception:
                        pass
                    try:
                        imap.logout()
                    except Exception:
                        pass
                    continue

                # Sender cooldown (only if thread_key missing)
                if not thread_key and replied_to_sender_recently(org_id, sender_email, hours=cooldown_hours):
                    print(f"Cooldown(sender): already replied to {sender_email} in last {cooldown_hours}h. Skipping.\n")
                    try:
                        imap.store(chosen_mid, "+FLAGS", "\\Seen")
                    except Exception:
                        pass
                    try:
                        imap.logout()
                    except Exception:
                        pass
                    continue

                trusted_sender = is_trusted_sender(sender_email, org_settings)

                # Security/system filter (bypass for trusted senders)
                if is_security_alert_email(subject, body, str(chosen_hdr or "")) and not trusted_sender:
                    logger.info(
                        f"event=security_skip org={org_slug} from={sender_email} thread_key={thread_key} subject={subject[:120]!r}"
                    )
                    print("Security/system email detected. Skipping.\n")
                    try:
                        imap.store(chosen_mid, "+FLAGS", "\\Seen")
                    except Exception:
                        pass
                    try:
                        imap.logout()
                    except Exception:
                        pass
                    break

                # Enquiry filter
                if not is_real_enquiry(subject, sender, body, raw_headers=chosen_hdr, trusted_sender=trusted_sender):
                    reason = getattr(is_real_enquiry, "last_reason", "")
                    logger.info(
                        f"event=not_real_enquiry org={org_slug} reason={reason} from={sender_email} thread_key={thread_key} subject={subject[:120]!r}"
                    )
                    print("Not a real enquiry (likely marketing/system). Skipping.\n")
                    try:
                        imap.store(chosen_mid, "+FLAGS", "\\Seen")
                    except Exception:
                        pass
                    try:
                        imap.logout()
                    except Exception:
                        pass
                    break

                # Enterprise lock (Postgres: app.services.thread_lock)
                from app.services.thread_lock import try_acquire_thread_lock

                THREAD_LOCK_SECONDS = 600
                got_lock = try_acquire_thread_lock(
                    engine,
                    org_id=org_id,
                    thread_key=thread_key,
                    cooldown_seconds=THREAD_LOCK_SECONDS,
                    worker_id=WORKER_ID,
                    ttl_seconds=THREAD_LOCK_SECONDS + 120,
                )
                if not got_lock:
                    print(f"[LOCK] Skip duplicate reply (another worker owns lock) org={org_id} thread={thread_key}\n")
                    logger.info(f"event=lock_skip org={org_slug} thread_key={thread_key}")
                    try:
                        imap.store(chosen_mid, "+FLAGS", "\\Seen")
                    except Exception:
                        pass

                    db = SessionLocal()
                    try:
                        upsert_worker_status(
                            db,
                            worker_id=WORKER_ID,
                            last_run_at=now_utc(),
                            lock_health_ok=True,
                            credits_health_ok=True,
                            last_error=None,
                        )
                        db.commit()
                    finally:
                        db.close()

                    try:
                        imap.logout()
                    except Exception:
                        pass
                    break

                # Credits check
                remaining = get_remaining_credits(engine, org_id)
                if remaining <= 0:
                    print(f"[BILLING] No credits left for org={org_id}. Skipping.\n")
                    logger.info(f"event=blocked_no_credits org={org_slug} remaining={remaining}")
                    log_usage(
                        engine,
                        org_id,
                        event="blocked_no_credits",
                        qty=1,
                        meta={"thread_key": thread_key, "from": sender_email, "message_id": message_id_n},
                    )
                    try:
                        imap.store(chosen_mid, "+FLAGS", "\\Seen")
                    except Exception:
                        pass

                    db = SessionLocal()
                    try:
                        upsert_worker_status(
                            db,
                            worker_id=WORKER_ID,
                            last_run_at=now_utc(),
                            credits_health_ok=False,
                            lock_health_ok=True,
                            last_error="No credits left",
                        )
                        db.commit()
                    finally:
                        db.close()

                    try:
                        imap.logout()
                    except Exception:
                        pass
                    break

                # Re-check enterprise toggle right before generating (live from PG)
                org_settings_live = get_org_settings(org_id)
                if not int(org_settings_live.get("auto_reply_enabled", 1)):
                    print("Auto-reply disabled (enterprise toggle) — Skipping.\n")
                    logger.info(f"event=auto_reply_disabled_live org={org_slug}")
                    try:
                        imap.store(chosen_mid, "+FLAGS", "\\Seen")
                    except Exception:
                        pass
                    try:
                        imap.logout()
                    except Exception:
                        pass
                    break

                # Only reply if new IN > OUT
                if not thread_needs_reply(org_id, thread_key):
                    print("[SKIP] No new customer message in thread. Already replied.\n")
                    try:
                        imap.store(chosen_mid, "+FLAGS", "\\Seen")
                    except Exception:
                        pass
                    try:
                        imap.logout()
                    except Exception:
                        pass
                    break

                print("ENQUIRY DETECTED -> Generating reply")

                # Log IN to Postgres (conversation_audit)
                db = SessionLocal()
                try:
                    log_conversation(
                        db,
                        org_id=org_id,
                        thread_key=thread_key,
                        direction="IN",
                        customer_email=sender_email,
                        subject=subject,
                        body_text=body,
                        ai_model=None,
                        email_message_id=message_id_n or None,
                        in_reply_to=in_reply_to,
                        references_header=references_header,
                    )
                    db.commit()
                finally:
                    db.close()

                # Build thread context before OpenAI
                thread_context = load_thread_context(org_id, thread_key, limit=6)

                # Logout before OpenAI
                try:
                    imap.logout()
                except Exception:
                    pass
                imap = None

                system_prompt, user_prompt = build_prompt(
                    org_settings=org_settings,
                    subject=subject,
                    sender=sender,
                    body=body,
                    thread_context=thread_context,
                )

                print(
                    f"[ORG] org_id={org_id} "
                    f"kb_len={len((org_settings.get('kb_text') or ''))} "
                    f"sys_len={len((org_settings.get('system_prompt') or ''))}"
                )

                # OpenAI + SMTP
                try:
                    print("Calling OpenAI...")
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    )

                    reply = (response.choices[0].message.content or "").strip()

                    if reply.strip().upper() == "SKIP_REPLY":
                        # Model tried to skip, but local rules marked this as an enquiry. Force a safe generic reply.
                        print("[WARN] Model returned SKIP_REPLY, but local rules marked as enquiry. Forcing a real reply.")

                        support_name = (org_settings.get("support_name") or "Support Team").strip()
                        support_email = (org_settings.get("support_email") or "").strip()

                        reply = (
                            "Hello,\n\n"
                            "Thanks for reaching out. We received your enquiry and we’re happy to help.\n"
                            "Could you please share a bit more detail about what you need (service/course/topic) and your preferred mode/timing?\n"
                            "If you want a callback, share your phone number (optional).\n\n"
                            f"Best regards,\n{support_name}"
                            + (f"\n{support_email}" if support_email else "")
                        ).strip()

                    print("---- AI REPLY (preview) ----")
                    print(reply[:800])

                    to_email = sender_email
                    smtp_ok = send_smtp_safe(a, to_email, "Re: " + subject, reply)

                except Exception as e:
                    print("WORKER ERROR (OpenAI/SMTP block):", repr(e))
                    logger.exception(f"event=worker_error org={org_slug} kind=openai_or_smtp")
                    smtp_ok = False
                    if not reply:
                        reply = "(generation failed) Please try again later."
                    to_email = sender_email

                # ✅ analytics log line (this is what your /admin/analytics/summary reads)
                credits_used = 1 if smtp_ok else 0
                logger.info(
                    f"event=email_processed org={org_slug} message_id={message_id_n} thread_key={thread_key} credits={credits_used}"
                )

                # Log OUT + worker status
                db = SessionLocal()
                try:
                    log_conversation(
                        db,
                        org_id=org_id,
                        thread_key=thread_key,
                        direction="OUT",
                        customer_email=sender_email,
                        subject=subject,
                        body_text=reply if smtp_ok else f"(SMTP FAILED)\n\n{reply}",
                        ai_model=model,
                        email_message_id=message_id_n or None,
                    )
                    upsert_worker_status(
                        db,
                        worker_id=WORKER_ID,
                        last_run_at=now_utc(),
                        last_email_processed_at=now_utc(),
                        last_email_message_id=message_id_n or None,
                        last_thread_key=thread_key,
                        lock_health_ok=True,
                        credits_health_ok=True,
                        last_error=None if smtp_ok else "SMTP send failed",
                    )
                    db.commit()
                finally:
                    db.close()

                # Billing + usage
                if smtp_ok:
                    ok = consume_credits(engine, org_id, qty=1)
                    log_usage(
                        engine,
                        org_id,
                        event="reply_sent",
                        qty=1,
                        meta={"thread_key": thread_key, "to": to_email, "message_id": message_id_n},
                    )
                    if not ok:
                        print(f"[BILLING] Warning: credits could not be consumed after send (org={org_id}).")
                        logger.info(f"event=credits_consume_failed org={org_slug} message_id={message_id_n}")
                else:
                    log_usage(
                        engine,
                        org_id,
                        event="smtp_failed",
                        qty=1,
                        meta={"thread_key": thread_key, "to": to_email, "message_id": message_id_n},
                    )

                # Mark seen (requires re-login because we logged out earlier)
                if chosen_mid is not None:
                    mark_seen_by_relogin(a, a.imap_host, a.imap_port, chosen_mid)

                if smtp_ok and message_id_n:
                    mark_replied(org_id, message_id_n)
                    print("Reply recorded + conversation stored.\n")

                if message_id_n:
                    replied_mids_this_run.add(message_id_n)
                if thread_key_n:
                    replied_threads_this_run.add(thread_key_n)

            except (ConnectionResetError, imaplib.IMAP4.abort, OSError) as e:
                print("NETWORK/IMAP ERROR:", repr(e))
                logger.exception(f"event=worker_error org=org{org_id} kind=network")

                try:
                    if imap:
                        imap.logout()
                except Exception:
                    pass

                db = SessionLocal()
                try:
                    upsert_worker_status(
                        db,
                        worker_id=WORKER_ID,
                        last_run_at=now_utc(),
                        lock_health_ok=True,
                        credits_health_ok=True,
                        last_error=f"NETWORK/IMAP ERROR: {repr(e)}"[:2000],
                    )
                    db.commit()
                finally:
                    db.close()

                time.sleep(2)
                if attempt == 0:
                    continue
                break

            except Exception as e:
                print("WORKER ERROR:", repr(e))
                logger.exception(f"event=worker_error org=org{org_id} kind=general")

                try:
                    if imap:
                        imap.logout()
                except Exception:
                    pass

                db = SessionLocal()
                try:
                    upsert_worker_status(
                        db,
                        worker_id=WORKER_ID,
                        last_run_at=now_utc(),
                        lock_health_ok=False,
                        credits_health_ok=True,
                        last_error=f"WORKER ERROR: {repr(e)}"[:2000],
                    )
                    db.commit()
                finally:
                    db.close()

                break


if __name__ == "__main__":
    import time as _time
    import logging as _logging

    _logging.basicConfig(level=_logging.INFO)
    _logger = _logging.getLogger("aimail-worker")

    _logger.info("IMAP Worker started (continuous mode)...")

    while True:
        try:
            main()
        except Exception as e:
            _logger.exception("Worker crashed: %s", e)

        _time.sleep(POLL_SECONDS)
