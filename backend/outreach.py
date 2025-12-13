def build_outreach_email(company_number, deadline_type, deadline_date):
    subject = f"Upcoming Companies House deadline for {company_number}"

    body = f"""
Hi,

I was reviewing public Companies House records and noticed that
your company ({company_number}) has an upcoming
{deadline_type.replace('_', ' ')} due on {deadline_date}.

Many small businesses miss this simply because Companies House
doesn’t send proactive reminders.

We built RegDeadline to automatically track filings and notify you
before penalties or strike-off risk.

You can set it up in under 30 seconds here:
👉 https://regdeadline.xyz/pay

No obligation — just a simple safeguard.

Best,
RegDeadline
"""

    return subject.strip(), body.strip()