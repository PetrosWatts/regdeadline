import os
import json
import stripe
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(__file__)
SUBSCRIBERS_PATH = os.path.join(BASE_DIR, "subscribers.json")

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

def load_subscribers():
    try:
        with open(SUBSCRIBERS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_subscribers(data):
    tmp = SUBSCRIBERS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, SUBSCRIBERS_PATH)

def sync_from_stripe():
    if not stripe.api_key:
        raise RuntimeError("Missing STRIPE_SECRET_KEY")

    existing = load_subscribers()
    existing_emails = {s["email"].lower() for s in existing if "email" in s}

    new_entries = []

    sessions = stripe.checkout.Session.list(limit=100)

    for session in sessions.auto_paging_iter():
        if session.payment_status != "paid":
            continue

        email = (session.customer_email or "").strip().lower()
        if not email:
            continue

    # Extract company number from Stripe Payment Link custom field
        company_number = None
        try:
            custom_fields = getattr(session, "custom_fields", None) or []
            for f in custom_fields:
                label = (getattr(f, "label", "") or "").strip().lower()
                if "company" in label and "number" in label:
                    text = getattr(f, "text", None)
                    if text and getattr(text, "value", None):
                        company_number = str(text.value).strip().upper()
                        break
        except Exception:
            company_number = None

    # Bulletproof: do not enroll without a company number
        if not company_number:
            print(f"[STRIPE] Paid session missing company number for {email} — skipping")
            continue

        if email in existing_emails:
            continue

        entry = {
            "email": email,
            "company_number": company_number,
            "source": "stripe",
            "added_at": datetime.now(timezone.utc).isoformat()
        }

        new_entries.append(entry)
        existing_emails.add(email)

    if new_entries:
        print(f"[STRIPE] Adding {len(new_entries)} new subscribers")
        savef_subscribers(existing + new_entries)
    else:
        print("[STRIPE] No new subscribers found")

if __name__ == "__main__":
    sync_from_stripe()