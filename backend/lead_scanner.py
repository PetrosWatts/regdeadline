import json
import time
from .utils import get_company_deadlines, deadline_in_range
from .outreach import build_outreach_email
from .scan_companies import get_older_companies
from .send_email import send_email
import os
from pathlib import Path

def build_company_pool(limit=20):
    companies = get_older_companies(limit=limit)
    return [c["company_number"] for c in companies]

SENT_FILE = Path(__file__).with_name("sent_leads.json")

def load_sent():
    if not SENT_FILE.exists():
        return set()
    try:
        data = json.loads(SENT_FILE.read_text())
        return set(data)
    except Exception:
        return set()

def save_sent(sent_set):
    SENT_FILE.write_text(json.dumps(sorted(list(sent_set)), indent=2))

def scan_for_leads():
    MAX_EMAILS = 5
    emailed_companies = set()
    sent = load_sent()
    leads = []
    company_pool = build_company_pool()

    for company in company_pool:
        if len(leads) >= MAX_EMAILS:
            break

        if company in sent:
            continue

        print(f"Scanning {company}...")
        deadlines = get_company_deadlines(company)

        if not deadlines:
            continue

        for dtype, date in deadlines.items():
            if company in emailed_companies:
                continue
            if deadline_in_range(date, 60):
                subject, body = build_outreach_email(company, dtype, date)
                send_email(
                to_email="petrwatts@gmail.com",
                subject=subject,
                body=body
            )           
                print(f"📧 Test email sent for company {company}")

                sent.add(company)
                save_sent(sent)

                leads.append({
                    "company": company,
                    "deadline_type": dtype,
                    "deadline_date": date,
                })

                emailed_companies.add(company)
                print(f"  ⚠️ {dtype} due on {date}")

        time.sleep(1)

    return leads

if __name__ == "__main__":
    leads = scan_for_leads()
    print("\nPotential leads:")
    print(json.dumps(leads, indent=2))