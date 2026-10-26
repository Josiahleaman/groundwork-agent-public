import csv
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)

from scraper import find_leads
from analyzer import analyze_and_write
from reporter import send_report
from sender import send_outreach
from cities import get_todays_cities

MIN_SCORE_THRESHOLD = 60
OUTPUT_FILE = str(Path(__file__).parent / "leads.csv")


def run():
    today_cities = get_todays_cities()
    print(f"\n=== Groundwork Lead Agent — {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
    print(f"Today's cities: {', '.join(today_cities)}\n")

    existing = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing.add(row.get("name", "") + row.get("address", ""))

    new_leads = []
    sent_count = 0
    no_email_count = 0

    for location in today_cities:
        leads = find_leads(location, max_per_category=5)

        for lead in leads:
            key = lead["name"] + str(lead["address"])
            if key in existing:
                print(f"  Skipping (already seen): {lead['name']}")
                continue

            print(f"\nAnalyzing: {lead['name']}")

            result = analyze_and_write(
                business_name=lead["name"],
                category=lead["category"],
                url=lead.get("website"),
                rating=lead.get("rating"),
                review_count=lead.get("review_count"),
                location=lead.get("location"),
            )

            lead["pagespeed_score"] = result["score"]
            lead["site_issues"] = "; ".join(result["issues"])
            lead["has_website"] = result["has_website"]
            lead["outreach_email"] = result["email"]
            lead["contact_email"] = result.get("contact_email", "")
            lead["unverified"] = result.get("unverified", False)
            lead["flagged"] = "YES" if result["flagged"] else "no"
            lead["email_sent"] = "no"

            if result.get("unverified"):
                print(f"  COULDN'T VERIFY — check manually")
            elif result["flagged"]:
                print(f"  LEAD (score: {result['score']}) — attempting to send email...")
                success, reason = send_outreach(lead)
                if success:
                    lead["email_sent"] = "YES"
                    sent_count += 1
                    print(f"  Email sent to {lead['contact_email']}")
                else:
                    print(f"  Email not sent: {reason}")
                    if reason == "no email found":
                        no_email_count += 1
            else:
                print(f"  Site decent (score: {result['score']}) — skipping")

            new_leads.append(lead)
            existing.add(key)

    if not new_leads:
        print("\nNo new leads found this run.")
        return

    fieldnames = [
        "name", "category", "location", "address", "phone", "website",
        "rating", "review_count", "pagespeed_score", "site_issues",
        "has_website", "flagged", "contact_email", "email_sent", "outreach_email"
    ]

    write_header = not os.path.exists(OUTPUT_FILE)
    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerows(new_leads)

    flagged = [l for l in new_leads if l["flagged"] == "YES"]
    unverified = [l for l in new_leads if l.get("unverified")]

    print(f"\n=== Done. {len(new_leads)} checked, {len(flagged)} flagged, {sent_count} emails sent ===\n")

    send_report(flagged, unverified, sent_count, no_email_count)


if __name__ == "__main__":
    run()
