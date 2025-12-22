from utils import load_subscribers, get_company_deadlines, deadline_in_range
from send_email import send_deadline_email
from backend.send_email import send_email, is_suppressed


def main():
    subscribers = load_subscribers()
    reminders = []

    for sub in subscribers:
        company = sub["company_number"]
        email = sub["email"]

        print(f"\nChecking company {company} for {email}...")

        deadlines = get_company_deadlines(company)
        if not deadlines:
            print("  No deadlines returned.")
            continue

        print(f"  Raw deadlines: {deadlines}")

        for deadline_type, date in deadlines.items():
            if deadline_in_range(date, 1000):  # using your wide test window
                reminders.append(
                    {
                        "email": email,
                        "company": company,
                        "deadline_type": deadline_type,
                        "deadline_date": date,
                    }
                )
                print(f"  ✅ {deadline_type} due on {date} is within window.")
                if is_suppressed(email):
                    print(f"  ⛔ Skipping suppressed email: {email}")
                    continue
                
                send_deadline_email(email, company, deadline_type, date)
            else:
                print(f"  ❌ {deadline_type} due on {date} is outside window.")

    print("\nSummary reminders list:")
    print(reminders)
    return reminders


if __name__ == "__main__":
    main()