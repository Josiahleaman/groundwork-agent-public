import os
import re
import time
import json
import base64
import requests
import anthropic
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def get_screenshot(url):
    """Opens the site in a real browser and returns a base64 screenshot."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 390, "height": 844})  # iPhone size
            page.goto(url, timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)  # let page settle
            screenshot = page.screenshot(full_page=False)
            browser.close()
            return base64.standard_b64encode(screenshot).decode("utf-8")
    except Exception as e:
        print(f"    (screenshot failed: {e})")
        return None


def get_html_and_email(url):
    """Fetches raw HTML via simple HTTP request."""
    try:
        start = time.time()
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) "
                          "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
        }
        resp = requests.get(url, headers=headers, timeout=15)
        load_time = round(time.time() - start, 2)
        # Extract email from HTML while we have it
        emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", resp.text)
        # Filter out common false positives
        filtered = [e for e in emails if not any(x in e.lower() for x in
                    ["example", "sentry", "wpcf7", "schema", "jquery", "@2x", "png", "svg", "email"])]
        email_found = filtered[0] if filtered else None
        return resp.text[:15000], load_time, resp.status_code, email_found
    except requests.exceptions.Timeout:
        return "", 15, 0, None
    except Exception:
        return None, 0, 0, None


def analyze_and_write(business_name, category, url, rating=None, review_count=None, location=None):
    """
    Fetches HTML + takes a screenshot, sends both to Claude,
    gets back a score, issues, and a personalized cold email.
    """

    if not url:
        return {
            "score": 0,
            "issues": ["No website found"],
            "email": _no_website_email(business_name, category, rating, review_count, location),
            "contact_email": None,
            "has_website": False,
            "flagged": True,
        }

    clean_url = url.split("?")[0]

    # Fetch HTML + extract contact email
    html, load_time, http_status, contact_email = get_html_and_email(clean_url)

    if html is None:
        return {
            "score": -1,
            "issues": ["Could not verify — site blocked our request"],
            "email": "",
            "contact_email": None,
            "has_website": True,
            "flagged": False,
            "unverified": True,
        }

    # Take screenshot
    print(f"    Taking screenshot...")
    screenshot_b64 = get_screenshot(clean_url)

    # If both HTML is empty and screenshot failed, mark as unverified
    if not html.strip() and not screenshot_b64:
        return {
            "score": -1,
            "issues": ["Could not verify — site blocked our request"],
            "email": "",
            "contact_email": None,
            "has_website": True,
            "flagged": False,
            "unverified": True,
        }

    # Build Claude message — always include HTML, optionally include screenshot
    city = location.split(",")[0].strip() if location else "your area"
    rating_line = f"{rating} stars ({review_count} reviews)" if rating else "solid reviews"

    text_prompt = f"""You are reviewing a {category} business website to write a professional cold outreach email.

Business: {business_name}
Location: {city}
Google Rating: {rating_line}
URL: {clean_url}
Mobile load time: {load_time}s
HTTP status: {http_status}
{"You can see a mobile screenshot of the site above." if screenshot_b64 else "No screenshot available."}

HTML (first 15,000 chars):
{html}

---

Do two things:

1. SCORE the website 0-100 (0=terrible, 100=great). Judge on:
   - Visual design quality (from screenshot if available)
   - Mobile friendliness
   - Load speed (over 3s slow, over 6s very slow)
   - HTTPS
   - Professional appearance — would a homeowner trust this business?
   - Clear contact info and services visible

2. Write a professional cold email following this structure EXACTLY:

Subject: Quick question about your website

Hey [use their first name from business name if possible, otherwise just omit],

Came across {business_name} while looking for {category}s in {city}. Looks like you've got {rating_line}.

[1-2 sentences referencing SPECIFIC things you see wrong with THIS site from the screenshot/HTML. Be specific — mention actual visual or technical issues you observe.]

We build websites for trade companies, no cost upfront. If you like the concept we put together for you, it's $2,500 and we hand everything over to you. If not, no hard feelings.


Groundwork Digital

Rules:
- The specific issues must be real things you actually see on this site, not generic
- Sound professional but human, not robotic or overly salesy
- Keep it concise, match the tone of the example
- Include the subject line at the top
- Do NOT use em dashes (—) anywhere in the email, use periods or commas instead

Respond ONLY in this JSON format:
{{
  "score": <number 0-100>,
  "issues": ["specific issue 1", "specific issue 2"],
  "email": "<full email including subject line>"
}}"""

    # Build message content
    content = []
    if screenshot_b64:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": screenshot_b64,
            }
        })
    content.append({"type": "text", "text": text_prompt})

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[{"role": "user", "content": content}]
    )

    raw = message.content[0].text.strip()

    # Parse JSON
    try:
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        score = int(data.get("score", 50))
        issues = data.get("issues", [])
        email = data.get("email", "").strip()
    except Exception:
        score = 50
        issues = ["Could not parse analysis"]
        email = ""

    return {
        "score": score,
        "issues": issues,
        "email": email,
        "contact_email": contact_email,
        "has_website": True,
        "flagged": score < 60,
    }


def _no_website_email(business_name, category, rating=None, review_count=None, location=None):
    city = location.split(",")[0].strip() if location else "your area"
    rating_line = f"{rating} stars ({review_count} reviews)" if rating else "solid reviews"

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": f"""Write a professional cold email to {business_name}, a {category} business with NO website.

Follow this structure:

Subject: Quick question about your website

Came across {business_name} while looking for {category}s in {city}. Looks like you've got {rating_line}.

[1-2 sentences about how not having a website means customers who search online can't find them — costing real jobs]

I build websites for trade companies — I actually put together a concept for you already. No cost to take a look. If you like it, it's $2,500 and I hand everything over to you. If not, no hard feelings.

Worth a 5-minute call?

Groundwork Digital

Keep it professional, human, and concise."""
        }]
    )
    return message.content[0].text.strip()
