import smtplib
import os
from email.message import EmailMessage
from dotenv import load_dotenv
import time
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any

SUPPRESSION_PATH = os.path.join(os.path.dirname(__file__), "suppression.json")
SEND_LOG_PATH = os.path.join(os.path.dirname(__file__), "send_log.json")

DEFAULT_DAILY_CAP = int(os.getenv("DAILY_SEND_CAP", "25"))          # hard ceiling per day
DEFAULT_PER_RUN_CAP = int(os.getenv("PER_RUN_SEND_CAP", "25"))      # ceiling per workflow run
DEFAULT_SLEEP_SECONDS = float(os.getenv("SEND_SLEEP_SECONDS", "6")) # spacing between sends
DEFAULT_SAFETY_MODE = os.getenv("SAFETY_MODE", "true").lower() == "true"  # true = do not send to real companies

def _read_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default

def _write_json(path: str, data: Any) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def is_suppressed(email: str) -> bool:
    email_l = (email or "").strip().lower()
    if not email_l or "@" not in email_l:
        return True  # treat invalid as suppressed

    dom = email_l.split("@", 1)[1]
    sup = _read_json(SUPPRESSION_PATH, {
        "suppressed_emails": [],
        "suppressed_domains": [],
        "unsubscribed_emails": [],
        "notes": {}
    })

    suppressed_emails = set(e.lower() for e in sup.get("suppressed_emails", []))
    unsubscribed = set(e.lower() for e in sup.get("unsubscribed_emails", []))
    suppressed_domains = set(d.lower() for d in sup.get("suppressed_domains", []))

    if email_l in suppressed_emails:
        return True
    if email_l in unsubscribed:
        return True
    if dom in suppressed_domains:
        return True

    return False

def can_send_more(per_run_sent: int) -> bool:
    # per-run cap
    if per_run_sent >= DEFAULT_PER_RUN_CAP:
        return False

    # daily cap
    log = _read_json(SEND_LOG_PATH, {})
    today = _today_utc()
    sent_today = int(log.get(today, 0))

    return sent_today < DEFAULT_DAILY_CAP

def record_send() -> None:
    log = _read_json(SEND_LOG_PATH, {})
    today = _today_utc()
    log[today] = int(log.get(today, 0)) + 1
    _write_json(SEND_LOG_PATH, log)

# Load .env
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(ROOT_DIR, ".env"))

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_PASS")

def send_email(to_email: str, subject: str, body: str, *, reply_to: Optional[str] = None, dry_run: Optional[bool] = None) -> bool:
    """
    Returns True if treated as sent (including dry-run), False if blocked/fails.
    """
    if dry_run is None:
        dry_run = DEFAULT_SAFETY_MODE

    to_email = (to_email or "").strip()
    if is_suppressed(to_email):
        print(f"[BLOCKED] Suppressed recipient: {to_email}")
        return False

    # Safety mode: never email real companies (only your own safe inbox)
    safe_inbox = os.getenv("SAFE_TEST_INBOX", "").strip()
    if dry_run:
        if not safe_inbox:
            print("[BLOCKED] SAFETY_MODE is on but SAFE_TEST_INBOX is not set.")
            return False
        print(f"[DRY-RUN] Redirecting {to_email} -> {safe_inbox}")
        to_email = safe_inbox

    # (keep your existing SMTP send implementation below)
    # Add basic headers:
    headers = {
        "X-RegDeadline": "true",
        "List-Unsubscribe": f"<mailto:{os.getenv('GMAIL_USER')}?subject=UNSUBSCRIBE>"
    }

    # If current code builds a MIME message, add headers like:
    # msg["List-Unsubscribe"] = headers["List-Unsubscribe"]
    # msg["X-RegDeadline"] = headers["X-RegDeadline"]
    # msg["Reply-To"] = reply_to or os.getenv("GMAIL_USER")

    msg = EmailMessage()
    msg["From"] = GMAIL_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg["Reply-To"] = reply_to or GMAIL_USER
    msg["List-Unsubscribe"] = f"<mailto:{GMAIL_USER}?subject=UNSUBSCRIBE>"
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            server.send_message(msg)

        record_send()
        time.sleep(DEFAULT_SLEEP_SECONDS)
        return True
    except Exception as e:
        print(f"[ERROR] send_email failed to {to_email}: {e}")
        return False