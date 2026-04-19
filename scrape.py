import os
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

TOKEN = os.getenv("DECODO_TOKEN")
TARGET_URL = "https://www.g2.com/products/slack/reviews"
SCRAPING_URL = "https://scraper-api.decodo.com/v2/scrape"

AUTH_HEADERS = {
    "Authorization": f"Basic {TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def scrape_with_decodo(url: str) -> str | dict:
    try:
        response = requests.post(
            SCRAPING_URL,
            headers=AUTH_HEADERS,
            json={
                "url": url,
                "headless": "html",
                "geo": "United States",
            },
            timeout=60,
        )
        # 1. Automatically raises HTTPError for 4xx or 5xx codes
        response.raise_for_status()

        # 2. Process successful 200 response
        data = response.json()
        results = data.get("results", [])

        if not results:
            return {
                "status_code": 207,
                "message": "Empty results – check your token or target URL",
                "results": [],
            }

        return results[0].get("content", "")

    except requests.exceptions.HTTPError:
        # 3. Handle specific status codes routed here by raise_for_status()
        if response.status_code == 401:
            return "Unauthorised – check your API token"
        if response.status_code == 403:
            return "Access denied – target may be blocked"
        return f"HTTP error occurred: {response.status_code} - {response.text}"

    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
        # 4. Handle network-level issues
        return f"Network error: {exc}"

    except Exception as exc:
        # 5. Catch-all for JSON parsing or other logic errors
        return f"Unexpected error: {exc}"


def extract_reviews(html: str):
    soup = BeautifulSoup(html, "html.parser")
    reviews = []

    for item in soup.select('[itemprop="review"]'):
        rating = item.select_one('[itemprop="ratingValue"]')
        author = item.select_one('[itemprop="author"]')
        body = item.select_one('[itemprop="reviewBody"]')

        full_text = item.get_text(" ", strip=True)

        # Generate a usable title from first sentence/question
        title = full_text.split("?")[0][:80] if full_text else None

        # Clean body text
        body_text = body.get_text(strip=True) if body else full_text

        reviews.append({
            "title": title,
            "rating": rating.get("content") if rating else None,
            "body": body_text[:150] + "..." if body_text else None,
            "author": author.get_text(strip=True) if author else None,
        })

    return reviews


# Scrape the page
html = scrape_with_decodo(TARGET_URL)
print(f"\nRetrieved {len(html):,} characters of HTML\n")

# Parse the reviews
reviews = extract_reviews(html)
print(f"Extracted {len(reviews)} reviews:\n")

for r in reviews[:5]:
    print(f"{r['rating']} – {r['title']}")
    print(f"   by {r['author']}")
    print(f"   {r['body']}")
    print()
