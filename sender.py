import os
import csv
import smtplib
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
CONTACTED_FILE = str(Path(__file__).parent / "contacted.csv")


def already_contacted(business_name, address):
    if not Path(CONTACTED_FILE).exists():
        return False
    with open(CONTACTED_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["name"] == business_name and row["address"] == address:
                return True
    return False


def log_contacted(business_name, address, contact_email):
    write_header = not Path(CONTACTED_FILE).exists()
    with open(CONTACTED_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "address", "contact_email", "date"])
        if write_header:
            writer.writeheader()
        from datetime import date
        writer.writerow({
            "name": business_name,
            "address": address,
            "contact_email": contact_email,
            "date": date.today().isoformat(),
        })


def send_outreach(lead):
    """Send cold email directly to the business. Returns True if sent."""
    contact_email = lead.get("contact_email")
    email_body = lead.get("outreach_email", "").strip()

    if not contact_email:
        return False, "no email found"

    if not email_body:
        return False, "no email body"

    if already_contacted(lead["name"], lead.get("address", "")):
        return False, "already contacted"

    # Parse subject line and body
    lines = email_body.splitlines()
    subject = "Quick question about your website"
    body_lines = lines

    if lines and lines[0].lower().startswith("subject:"):
        subject = lines[0].split(":", 1)[1].strip()
        body_lines = lines[1:]

    body_text = "\n".join(body_lines).strip()

    # Build email
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Groundwork Digital <{GMAIL_ADDRESS}>"
    msg["To"] = contact_email
    msg["Reply-To"] = GMAIL_ADDRESS

    # Plain text version
    msg.attach(MIMEText(body_text, "plain"))

    # Send
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, contact_email, msg.as_string())

        log_contacted(lead["name"], lead.get("address", ""), contact_email)
        return True, "sent"

    except Exception as e:
        return False, str(e)
