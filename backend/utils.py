import json
import os
from datetime import datetime

import requests
from dotenv import load_dotenv

# Load .env from project root
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(ROOT_DIR, ".env"))

COMPANIES_HOUSE_API_KEY = os.getenv("COMPANIES_HOUSE_API_KEY")


def load_subscribers():
    """Load subscribers from backend/subscribers.json"""
    path = os.path.join(os.path.dirname(__file__), "subscribers.json")
    with open(path, "r") as f:
        return json.load(f)


def save_subscribers(data):
    """Save subscribers to backend/subscribers.json"""
    path = os.path.join(os.path.dirname(__file__), "subscribers.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=4)


def get_company_deadlines(company_number: str):
    """
    Call Companies House API and return next accounts + confirmation statement due dates.
    """
    if not COMPANIES_HOUSE_API_KEY:
        raise RuntimeError("COMPANIES_HOUSE_API_KEY is not set in .env")

    url = f"https://api.company-information.service.gov.uk/company/{company_number}"
    resp = requests.get(url, auth=(COMPANIES_HOUSE_API_KEY, ""))

    if resp.status_code != 200:
        print(f"[WARN] API returned {resp.status_code} for company {company_number}")
        return None

    data = resp.json()
    deadlines = {}

    accounts = data.get("accounts", {})
    conf_stmt = data.get("confirmation_statement", {})

    if "next_due" in accounts:
        deadlines["accounts"] = accounts["next_due"]
    if "next_due" in conf_stmt:
        deadlines["confirmation_statement"] = conf_stmt["next_due"]

    return deadlines


def deadline_in_range(date_str: str, days_range: int = 30) -> bool:
    """
    True if deadline is within the next `days_range` days.
    """
    if not date_str:
        return False

    # Companies House dates are YYYY-MM-DD
    dt = datetime.fromisoformat(date_str)
    diff = (dt - datetime.now()).days
    return 0 < diff <= days_range