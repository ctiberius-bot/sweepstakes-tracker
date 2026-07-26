#!/usr/bin/env python3
"""Validate that every inventory record produced a complete v1.3 profile."""

import json
import re
from datetime import date
from pathlib import Path

BASE = Path(__file__).parent
data = json.loads((BASE / "data.json").read_text(encoding="utf-8"))
sites = data["sites"]
promotions = json.loads((BASE / "data" / "active_sweepstakes.json").read_text(encoding="utf-8"))["promotions"]
editorial_pages = json.loads((BASE / "data" / "editorial.json").read_text(encoding="utf-8"))["articles"]
active_promotions = [promotion for promotion in promotions if date.fromisoformat(promotion["closes"]) >= date.today()]
review_dir = BASE / "reviews"
required_markers = (
    "Inventory record",
    "Known prizes",
    "Pros and cons at a glance",
    "Main concerns and scored signals",
    "Marketing and data practices",
    'id="unsubscribe"',
    "Source and verification links",
    "automated public-source check",
    "v1.4",
)

expected = {f"{site['slug']}.html" for site in sites} | {f"{promotion['slug']}.html" for promotion in active_promotions}
actual = {path.name for path in review_dir.glob("*.html")}
if expected != actual:
    raise SystemExit(f"Profile file mismatch. Missing={sorted(expected - actual)} Extra={sorted(actual - expected)}")

for site in sites:
    path = review_dir / f"{site['slug']}.html"
    page = path.read_text(encoding="utf-8")
    missing = [marker for marker in required_markers if marker not in page]
    if missing:
        raise SystemExit(f"{path.name} is missing: {', '.join(missing)}")
    if site["name"] not in page:
        raise SystemExit(f"{path.name} does not contain its site name")
    if re.search(r"<dt>(?:Last verified|Profile refreshed)</dt><dd>[A-Za-z]+ \d{1,2}, \d{1,3}</dd>", page):
        raise SystemExit(f"{path.name} contains a truncated display date")

for promotion in active_promotions:
    path = review_dir / f"{promotion['slug']}.html"
    page = path.read_text(encoding="utf-8")
    if promotion["title"] not in page or "ScamFactor" not in page:
        raise SystemExit(f"{path.name} is not a complete merged-inventory profile")
    if re.search(r"<dt>(?:Last verified|Profile refreshed)</dt><dd>[A-Za-z]+ \d{1,2}, \d{1,3}</dd>", page):
        raise SystemExit(f"{path.name} contains a truncated display date")

print(f"Validated {len(sites) + len(active_promotions)} merged inventory detail pages.")

sweepstakes_dir = BASE / "sweepstakes"
today = __import__("datetime").date.today()
active = [promotion for promotion in promotions if __import__("datetime").date.fromisoformat(promotion["closes"]) >= today]
expected_sweeps = {f"{promotion['slug']}.html" for promotion in active}
actual_sweeps = {path.name for path in sweepstakes_dir.glob("*.html")}
if expected_sweeps != actual_sweeps:
    raise SystemExit(
        f"Sweepstakes file mismatch. Missing={sorted(expected_sweeps - actual_sweeps)} "
        f"Extra={sorted(actual_sweeps - expected_sweeps)}"
    )
for promotion in active:
    page = (sweepstakes_dir / f"{promotion['slug']}.html").read_text(encoding="utf-8")
    required = (promotion["title"], "Entry deadline", "Prize inventory", "Verification record")
    missing = [marker for marker in required if marker not in page]
    if missing:
        raise SystemExit(f"{promotion['slug']}.html is missing: {', '.join(missing)}")

inventory_page = (BASE / "active-sweepstakes.html").read_text(encoding="utf-8")
if inventory_page.count('class="sweep-card"') != len(active):
    raise SystemExit("Active sweepstakes page does not contain one card per open promotion.")
print(f"Validated {len(active)} active promotion pages and inventory cards.")

guides_dir = BASE / "guides"
expected_guides = {f"{article['slug']}.html" for article in editorial_pages}
actual_guides = {path.name for path in guides_dir.glob("*.html")}
if expected_guides != actual_guides:
    raise SystemExit(
        f"Guide file mismatch. Missing={sorted(expected_guides - actual_guides)} "
        f"Extra={sorted(actual_guides - expected_guides)}"
    )
site_slugs = {site["slug"] for site in sites}
for article in editorial_pages:
    page = (guides_dir / f"{article['slug']}.html").read_text(encoding="utf-8")
    required = (article["title"], article["meta_description"], "Quick check", "Related site profiles")
    missing = [marker for marker in required if marker not in page]
    if missing:
        raise SystemExit(f"{article['slug']}.html is missing: {', '.join(missing)}")
    invalid_profiles = [
        profile["slug"] for profile in article["related_profiles"]
        if profile["slug"] not in site_slugs
    ]
    if invalid_profiles:
        raise SystemExit(f"{article['slug']} contains invalid related profiles: {invalid_profiles}")

for profile_name in expected:
    page = (review_dir / profile_name).read_text(encoding="utf-8")
    if "Guides related to this site" not in page:
        raise SystemExit(f"{profile_name} is missing contextual guide links")

sitemap = (BASE / "sitemap.xml").read_text(encoding="utf-8")
missing_sitemap_guides = [
    article["slug"] for article in editorial_pages
    if f"https://sweeps.safetrackerhub.com/guides/{article['slug']}" not in sitemap
]
if missing_sitemap_guides:
    raise SystemExit(f"Sitemap is missing guides: {missing_sitemap_guides}")
print(f"Validated {len(editorial_pages)} editorial guides and contextual links on {len(expected)} profiles.")
