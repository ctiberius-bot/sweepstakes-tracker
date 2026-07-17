#!/usr/bin/env python3
"""
Basic Sweepstakes Tracker Scraper
=================================
This is a skeleton scraper that can be expanded.
It fetches key pages, extracts prize/winner info (simple regex/ BeautifulSoup),
updates a JSON data file, and can regenerate the HTML.

Requirements:
  pip install requests beautifulsoup4 lxml schedule

Usage:
  python scraper.py                  # one-time run
  python scraper.py --schedule       # run daily at 6 AM local
  python scraper.py --regenerate     # just rebuild HTML from data.json

Legal note: Always respect robots.txt and Terms of Service.
Scraping personal data or aggressive crawling can get you blocked / legal issues.
Only scrape publicly available prize lists and rules pages.
"""

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Install dependencies: pip install requests beautifulsoup4 lxml")
    raise

# ========== CONFIG ==========
DATA_FILE = Path(__file__).parent / "data.json"
HTML_TEMPLATE = Path(__file__).parent.parent / "sweepstakes-tracker.html"  # or copy it here
OUTPUT_HTML = Path(__file__).parent / "index.html"
USER_AGENT = "Mozilla/5.0 (compatible; SweepTrackerBot/1.0; +https://yoursite.com/bot)"
TIMEOUT = 15
HEADERS = {"User-Agent": USER_AGENT}

# Sites to check (expand this list carefully)
SITES_TO_SCRAPE = {
    "mondosweeps": {
        "url": "https://www.mondosweeps.com/",
        "name": "Mondosweeps",
        "selectors": {
            "prizes": "h1, h2, .prize, [class*='prize']",
            "winners": ".winner, [class*='winner']"
        }
    },
    "winstakes": {
        "url": "https://www.winstakes.com/",
        "name": "Winstakes",
        "selectors": {
            "prizes": "h1, h2, .prize",
            "winners": ".winner"
        }
    },
    "prizeloot": {
        "url": "https://www.prizeloot.com/",
        "name": "Prizeloot",
        "selectors": {
            "prizes": "h1, h2, .prize, [class*='cash']",
            "winners": ".winner, [class*='winner']"
        }
    },
    "winloot": {
        "url": "https://www.winloot.com/",
        "name": "Winloot",
        "selectors": {
            "prizes": "h1, h2",
            "winners": "a[href*='Winners']"
        }
    },
    "prizegrab": {
        "url": "https://prizegrab.com/",
        "name": "Prizegrab",
        "selectors": {
            "prizes": "h1, h2, .prize",
            "winners": ".winners, [class*='winner']"
        }
    },
    # Add more carefully. Free samples sites are harder to scrape usefully.
}

def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_updated": None, "sites": {}}

def save_data(data):
    data["last_updated"] = datetime.utcnow().isoformat() + "Z"
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved data to {DATA_FILE}")

def fetch_page(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        return None

def extract_text_snippets(html, keywords=None):
    """Very basic extraction – improve with better selectors or LLM later."""
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    texts = []
    for tag in soup.find_all(["h1", "h2", "h3", "p", "li", "span", "div"]):
        t = tag.get_text(strip=True)
        if len(t) > 15 and len(t) < 300:
            if keywords is None or any(k.lower() in t.lower() for k in keywords):
                texts.append(t)
    return list(dict.fromkeys(texts))[:20]  # unique, limit

def scrape_site(key, config):
    print(f"Scraping {config['name']}...")
    html = fetch_page(config["url"])
    if not html:
        return None

    prizes = extract_text_snippets(html, keywords=["cash", "prize", "$", "win", "giveaway", "daily"])
    winners = extract_text_snippets(html, keywords=["winner", "won", "congrats", "selected"])

    return {
        "name": config["name"],
        "url": config["url"],
        "scraped_at": datetime.utcnow().isoformat() + "Z",
        "prize_snippets": prizes[:10],
        "winner_snippets": winners[:8],
        "raw_status": "ok"
    }

def run_scrape():
    data = load_data()
    if "sites" not in data:
        data["sites"] = {}

    for key, config in SITES_TO_SCRAPE.items():
        result = scrape_site(key, config)
        if result:
            data["sites"][key] = result
        time.sleep(2)  # be polite

    save_data(data)
    print("Scrape complete.")
    return data

def regenerate_html(data=None):
    """Simple example: just update the last-updated timestamp in the existing HTML.
    For a full rebuild you would load a Jinja template or string-replace the JS data array.
    """
    if data is None:
        data = load_data()

    html_path = Path(__file__).parent.parent / "sweepstakes-tracker.html"
    if not html_path.exists():
        print(f"HTML template not found at {html_path}")
        return

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Update the last-updated display
    now_str = datetime.now().strftime("%B %d, %Y")
    html = re.sub(
        r'id="last-updated"[^>]*>.*?</div>',
        f'id="last-updated" class="text-lg font-semibold">{now_str}</div>',
        html,
        count=1
    )
    html = re.sub(
        r'id="footerDate">.*?</strong>',
        f'id="footerDate">{now_str}</strong>',
        html,
        count=1
    )

    # You can also inject scraped snippets into a special "Live Updates" section
    # For production, better to keep data in JSON and have the HTML load it via fetch()
    # or fully rebuild with a template engine.

    out = Path(__file__).parent / "index.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Regenerated {out}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sweepstakes Tracker Scraper")
    parser.add_argument("--schedule", action="store_true", help="Run daily")
    parser.add_argument("--regenerate", action="store_true", help="Only rebuild HTML")
    args = parser.parse_args()

    if args.regenerate:
        regenerate_html()
        return

    data = run_scrape()
    regenerate_html(data)

    if args.schedule:
        try:
            import schedule
            schedule.every().day.at("06:00").do(lambda: (run_scrape(), regenerate_html()))
            print("Scheduled daily at 06:00. Press Ctrl+C to stop.")
            while True:
                schedule.run_pending()
                time.sleep(60)
        except ImportError:
            print("For scheduling: pip install schedule")

if __name__ == "__main__":
    main()
