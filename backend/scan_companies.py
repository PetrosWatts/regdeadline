import requests
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load env vars
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(ROOT_DIR, ".env"))

API_KEY = os.getenv("COMPANIES_HOUSE_API_KEY")


def get_recent_companies(limit=30):
    """
    Fetch companies incorporated in the last 7 days.
    """
    url = "https://api.company-information.service.gov.uk/advanced-search/companies"

    params = {
        "size": limit,
        "incorporated_from": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
        "incorporated_to": datetime.now().strftime("%Y-%m-%d"),
        "sort_order": "descending",
    }

    resp = requests.get(url, auth=(API_KEY, ""), params=params, timeout=10)

    if resp.status_code != 200:
        print("API error:", resp.status_code, resp.text)
        return []

    data = resp.json()
    return [
        {
            "company_number": c.get("company_number"),
            "company_name": c.get("company_name"),
            "incorporated_on": c.get("date_of_creation"),
        }
        for c in data.get("items", [])
    ]


def get_older_companies(limit=30):
    """
    Fetch companies incorporated 2–5 years ago (higher risk of missed filings).
    """
    url = "https://api.company-information.service.gov.uk/advanced-search/companies"

    params = {
        "size": limit,
        "incorporated_from": (datetime.now() - timedelta(days=5*365)).strftime("%Y-%m-%d"),
        "incorporated_to": (datetime.now() - timedelta(days=2*365)).strftime("%Y-%m-%d"),
        "sort_order": "descending",
        "company_status": "active",
    }

    resp = requests.get(url, auth=(API_KEY, ""), params=params, timeout=10)

    if resp.status_code != 200:
        print("API error:", resp.status_code, resp.text)
        return []

    data = resp.json()
    results = []

    for c in data.get("items", []):
        company_number = c.get("company_number")

        # Exclude Northern Ireland companies
        if company_number.startswith("NI"):
            continue

        results.append({
            "company_number": company_number,
            "company_name": c.get("company_name"),
            "incorporated_on": c.get("date_of_creation"),
        })

    return results


if __name__ == "__main__":
    print("Running company scan...")
    companies = get_recent_companies()
    print(f"Found {len(companies)} companies:\n")
    print(json.dumps(companies, indent=2))