import os
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

TRADE_CATEGORIES = [
    "plumber",
    "electrician",
    "hvac contractor",
    "roofing contractor",
    "general contractor",
    "landscaping",
    "pest control",
    "painting contractor",
]

def search_businesses(category, location, max_results=20):
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": f"{category} in {location}",
        "key": GOOGLE_API_KEY,
    }
    results = []
    while len(results) < max_results:
        response = requests.get(url, params=params).json()
        for place in response.get("results", []):
            results.append({
                "name": place.get("name"),
                "address": place.get("formatted_address"),
                "rating": place.get("rating"),
                "review_count": place.get("user_ratings_total", 0),
                "place_id": place.get("place_id"),
                "website": None,
                "phone": None,
            })
        next_page = response.get("next_page_token")
        if not next_page or len(results) >= max_results:
            break
        import time
        time.sleep(2)
        params = {"pagetoken": next_page, "key": GOOGLE_API_KEY}

    return results[:max_results]


def get_place_details(place_id):
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "website,formatted_phone_number",
        "key": GOOGLE_API_KEY,
    }
    response = requests.get(url, params=params).json()
    result = response.get("result", {})
    return {
        "website": result.get("website"),
        "phone": result.get("formatted_phone_number"),
    }


def find_leads(location, max_per_category=10):
    all_leads = []
    for category in TRADE_CATEGORIES:
        print(f"Searching: {category} in {location}...")
        businesses = search_businesses(category, location, max_results=max_per_category)
        for biz in businesses:
            details = get_place_details(biz["place_id"])
            biz["website"] = details["website"]
            biz["phone"] = details["phone"]
            biz["category"] = category
            biz["location"] = location
            all_leads.append(biz)
    return all_leads
