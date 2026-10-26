import os
import smtplib
from pathlib import Path
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")


def send_report(leads, unverified=None, sent_count=0, no_email_count=0):
    """Emails a clean report of flagged leads to yourself."""

    if not leads:
        print("No leads to report.")
        return

    date_str = datetime.now().strftime("%B %d, %Y")
    count = len(leads)

    # Builds the HTML email body
    lead_blocks = ""
    for i, lead in enumerate(leads, 1):
        contact = lead.get("contact_email") or lead.get("phone") or "No contact found"
        score = lead.get("pagespeed_score", "N/A")
        issues = lead.get("site_issues", "")
        email_body = lead.get("outreach_email", "").replace("\n", "<br>")
        website = lead.get("website", "No website")

        lead_blocks += f"""
        <div style="background:#f9f9f9; border-left:4px solid #2563eb; padding:20px; margin-bottom:30px; border-radius:4px;">
            <h2 style="margin:0 0 4px 0; color:#1e293b;">#{i} — {lead['name']} {"<span style='background:#dcfce7;color:#166534;font-size:12px;padding:2px 8px;border-radius:12px;margin-left:8px;'>✓ Email Sent</span>" if lead.get("email_sent") == "YES" else "<span style='background:#fef9c3;color:#854d0e;font-size:12px;padding:2px 8px;border-radius:12px;margin-left:8px;'>No Email Found</span>"}</h2>
            <p style="margin:0 0 12px 0; color:#64748b; font-size:14px;">
                {lead['category'].title()} · {lead['location']} · Score: <strong>{score}/100</strong>
            </p>

            <table style="font-size:14px; color:#374151; margin-bottom:16px;">
                <tr><td style="padding:2px 12px 2px 0;"><strong>Website:</strong></td><td><a href="{website}" style="color:#2563eb;">{website}</a></td></tr>
                <tr><td style="padding:2px 12px 2px 0;"><strong>Contact:</strong></td><td>{contact}</td></tr>
                <tr><td style="padding:2px 12px 2px 0;"><strong>Phone:</strong></td><td>{lead.get('phone') or 'N/A'}</td></tr>
                <tr><td style="padding:2px 12px 2px 0;"><strong>Google Rating:</strong></td><td>{lead.get('rating', 'N/A')} ⭐ ({lead.get('review_count', 0)} reviews)</td></tr>
            </table>

            <p style="font-size:13px; color:#6b7280; margin-bottom:12px;"><strong>Issues found:</strong> {issues}</p>

            <div style="background:white; border:1px solid #e2e8f0; border-radius:4px; padding:16px; font-size:14px; color:#1e293b; line-height:1.6;">
                <p style="margin:0 0 8px 0; font-size:12px; text-transform:uppercase; color:#94a3b8; letter-spacing:0.05em;">READY-TO-SEND EMAIL</p>
                {email_body}
            </div>
        </div>
        """

    # Build unverified section
    unverified_block = ""
    if unverified:
        rows = ""
        for u in unverified:
            rows += f"""<tr>
                <td style="padding:8px 12px; border-bottom:1px solid #f1f5f9;"><strong>{u['name']}</strong></td>
                <td style="padding:8px 12px; border-bottom:1px solid #f1f5f9;">{u['category'].title()}</td>
                <td style="padding:8px 12px; border-bottom:1px solid #f1f5f9;">{u['location']}</td>
                <td style="padding:8px 12px; border-bottom:1px solid #f1f5f9;"><a href="{u.get('website','')}" style="color:#2563eb;">{u.get('website','N/A')}</a></td>
                <td style="padding:8px 12px; border-bottom:1px solid #f1f5f9;">{u.get('phone','N/A')}</td>
            </tr>"""
        unverified_block = f"""
        <div style="margin-top:40px;">
            <h2 style="color:#92400e; font-size:16px; margin-bottom:12px;">Couldn't Verify — Check Manually ({len(unverified)})</h2>
            <p style="font-size:13px; color:#78716c; margin-bottom:12px;">These sites blocked our request. Open them yourself and decide if they're worth reaching out to.</p>
            <table style="width:100%; border-collapse:collapse; font-size:13px; color:#374151;">
                <tr style="background:#fef3c7;">
                    <th style="padding:8px 12px; text-align:left;">Business</th>
                    <th style="padding:8px 12px; text-align:left;">Category</th>
                    <th style="padding:8px 12px; text-align:left;">Location</th>
                    <th style="padding:8px 12px; text-align:left;">Website</th>
                    <th style="padding:8px 12px; text-align:left;">Phone</th>
                </tr>
                {rows}
            </table>
        </div>"""

    html = f"""
    <html><body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width:700px; margin:0 auto; padding:20px; color:#1e293b;">

        <div style="background:#2563eb; color:white; padding:24px; border-radius:8px; margin-bottom:30px;">
            <h1 style="margin:0 0 4px 0; font-size:22px;">Groundwork Digital — Lead Report</h1>
            <p style="margin:0; opacity:0.85;">{date_str} · {count} lead{"s" if count != 1 else ""} found · {sent_count} email{"s" if sent_count != 1 else ""} sent · {no_email_count} need manual follow-up</p>
        </div>

        {lead_blocks}

        {unverified_block}

        <p style="font-size:12px; color:#94a3b8; text-align:center; margin-top:40px;">
            Sent automatically by the Groundwork Lead Agent
        </p>
    </body></html>
    """

    # Build the email
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🎯 {count} New Lead{'s' if count != 1 else ''} — {date_str}"
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = GMAIL_ADDRESS  # sends report to yourself
    msg.attach(MIMEText(html, "html"))

    # Send via Gmail SMTP
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, GMAIL_ADDRESS, msg.as_string())
        print(f"✅ Report emailed to {GMAIL_ADDRESS} — {count} leads")
    except Exception as e:
        print(f"❌ Email failed: {e}")
