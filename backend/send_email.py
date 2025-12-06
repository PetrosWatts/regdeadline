import smtplib
import os
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Load .env
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(ROOT_DIR, ".env"))

EMAIL = os.getenv("GMAIL_USER")
PASSWORD = os.getenv("GMAIL_PASS")


def send_deadline_email(to_email, company_number, deadline_type, deadline_date):
    SUBJECT = f"Upcoming Companies House deadline for {company_number}"
    BODY = f"""
Hi,

This is a reminder that your company's upcoming *{deadline_type.replace('_', ' ')}* is due on **{deadline_date}**.

Company Number: {company_number}

Make sure to file on time to avoid penalties.

— RegDeadline Automated Reminder Service
"""

    msg = MIMEText(BODY, "plain")
    msg["Subject"] = SUBJECT
    msg["From"] = EMAIL
    msg["To"] = to_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL, PASSWORD)
            server.sendmail(EMAIL, to_email, msg.as_string())
        print(f"📧 Email sent to {to_email} ({company_number}: {deadline_type})")
    except Exception as e:
        print("❌ Error sending email:", e)