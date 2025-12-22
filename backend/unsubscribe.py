import os
import re
import imaplib
import email
import json
from datetime import datetime, timezone

SUPPRESSION_PATH = os.path.join(os.path.dirname(__file__), "suppression.json")

KEYWORDS = [
    "unsubscribe",
    "opt out",
    "stop",
    "remove me",
    "do not contact",
]

def _read_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default

def _write_json(path: str, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def _now_utc_iso():
    return datetime.now(timezone.utc).isoformat()

def _extract_from_addr(msg) -> str:
    from_hdr = msg.get("From", "")
    # best-effort parse
    m = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_hdr)
    return (m.group(0) if m else "").lower().strip()

def _get_body_text(msg) -> str:
    if msg.is_multipart():
        parts = []
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition", "")).lower()
            if ctype == "text/plain" and "attachment" not in disp:
                try:
                    parts.append(part.get_payload(decode=True).decode(errors="ignore"))
                except Exception:
                    pass
        return "\n".join(parts).lower()
    else:
        try:
            return (msg.get_payload(decode=True) or b"").decode(errors="ignore").lower()
        except Exception:
            return ""

def process_unsubscribes() -> int:
    user = os.getenv("GMAIL_USER", "").strip()
    pwd = os.getenv("GMAIL_PASS", "").strip()
    if not user or not pwd:
        print("[UNSUB] Missing GMAIL_USER/GMAIL_PASS")
        return 0

    sup = _read_json(SUPPRESSION_PATH, {
        "suppressed_emails": [],
        "suppressed_domains": [],
        "unsubscribed_emails": [],
        "notes": {}
    })

    unsub = set(e.lower() for e in sup.get("unsubscribed_emails", []))
    notes = sup.get("notes", {})

    m = imaplib.IMAP4_SSL("imap.gmail.com")
    m.login(user, pwd)
    m.select("INBOX")

    # Search recent unseen messages (you can widen this later)
    status, data = m.search(None, "UNSEEN")
    if status != "OK":
        print("[UNSUB] IMAP search failed")
        return 0

    ids = data[0].split()
    added = 0

    for msg_id in ids:
        status, msg_data = m.fetch(msg_id, "(RFC822)")
        if status != "OK":
            continue

        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)

        subj = (msg.get("Subject", "") or "").lower()
        body = _get_body_text(msg)

        text = subj + "\n" + body
        if not any(k in text for k in KEYWORDS):
            continue

        from_addr = _extract_from_addr(msg)
        if not from_addr:
            continue

        if from_addr not in unsub:
            unsub.add(from_addr)
            notes[from_addr] = {"reason": "unsubscribe_request", "ts": _now_utc_iso()}
            added += 1
            print(f"[UNSUB] Added: {from_addr}")

        # mark seen regardless (prevents re-processing loops)
        m.store(msg_id, "+FLAGS", "\\Seen")

    sup["unsubscribed_emails"] = sorted(unsub)
    sup["notes"] = notes
    _write_json(SUPPRESSION_PATH, sup)

    m.close()
    m.logout()
    return added

if __name__ == "__main__":
    n = process_unsubscribes()
    print(f"[UNSUB] Processed. Newly added: {n}")