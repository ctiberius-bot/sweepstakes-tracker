#!/usr/bin/env python3
"""
Simplified Sweepstakes Tracker Rebuilder
========================================
Loads sites from data.json, updates the last_updated timestamp,
and generates a clean index.html using the Jinja2 template.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from jinja2 import Environment, FileSystemLoader, select_autoescape

BASE = Path(__file__).parent
TEMPLATE_DIR = BASE / "templates"
OUTPUT_HTML = BASE / "index.html"
DATA_FILE = BASE / "data.json"
REVIEWS_DIR = BASE / "reviews"
WINNERS_FILE = BASE / "data" / "winners.json"
ACTIVE_SWEEPS_FILE = BASE / "data" / "active_sweepstakes.json"
SITE_ORIGIN = "https://sweeps.safetrackerhub.com"
SITE_TYPES = {
    "app": "An app that helps users discover, save, or manage third-party sweepstakes. It adds convenience, but also another account and data layer.",
    "daily": "An operator offering recurring daily-entry drawings, often with frequent promotional email. Repetition can create more chances, but not necessarily better odds.",
    "directory": "A listing service that sends visitors to sweepstakes run by outside sponsors. Quality, eligibility, privacy, and fulfillment vary by each linked promotion.",
    "globalizer": "A high-volume sweepstakes network using shared marketing and data systems across several brands. Expect frequent entries and heavier promotional follow-up.",
    "leadgen": "A funnel primarily designed to collect consumer information or route visitors to advertisers. Promised rewards may depend on surveys, offers, or extensive qualification steps.",
    "legacy": "A long-established sweepstakes operator with a recognizable brand and documented history. Familiarity lowers some uncertainty but can attract impersonation scams.",
    "local-directory": "A directory emphasizing state, regional, or locally available offers. Availability and sponsor terms can differ substantially by location.",
    "niche": "A sweepstakes or content site aimed at a particular audience or life stage. Offers and marketing are tailored to that segment.",
    "premium-directory": "A listing or organization service with optional paid access, tools, or early listings. Paying for convenience does not improve the underlying odds.",
    "rewards": "A platform where users earn points or cash through surveys, shopping, games, or other tasks, sometimes alongside raffles. Returns are usually modest relative to time spent.",
    "samples": "A product-sampling or freebie program where availability may depend on demographics, brand campaigns, or limited inventory rather than a conventional drawing.",
    "other": "A site or promotion model that does not fit the tracker’s main categories. Its individual profile explains the specific structure and concerns.",
}


def slugify(value):
    """Create stable, URL-safe review filenames from site names."""
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def clean_generated_html(html):
    """Keep generated files stable and free of template-only whitespace."""
    return "\n".join(line.rstrip() for line in html.splitlines()) + "\n"


def site_initials(name):
    words = [
        word for word in re.sub(r"\([^)]*\)", " ", name).split()
        if word.lower() not in {"and", "the", "of"}
    ]
    if len(words) > 1:
        return "".join(word[0] for word in words[:2]).upper()
    return (words[0][:2] if words else "?").upper()


def favicon_url(link):
    if not link or link == "#":
        return ""
    parts = urlsplit(link)
    return f"{parts.scheme}://{parts.netloc}/favicon.ico"


def main():
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Missing {DATA_FILE}")

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    sites = data.get("sites", [])
    if not sites:
        raise ValueError("No sites found in data.json")
    sites.sort(key=lambda site: (float(site["score"]), site["name"].casefold()))
    for site in sites:
        site["slug"] = site.get("slug") or slugify(site["name"])
        site["initials"] = site_initials(site["name"])
        site["mark_hue"] = sum(ord(char) for char in site["name"]) % 360
        site["favicon_url"] = favicon_url(site.get("link"))
    for rank, site in enumerate(sites, start=1):
        site["rank"] = rank

    # Always update the timestamp to now (UTC)
    now = datetime.now(timezone.utc)
    data["last_updated"] = now.isoformat().replace("+00:00", "Z")
    last_updated_str = now.strftime("%B %d, %Y")

    # Write the updated data.json back (clean)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # Setup Jinja
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"])
    )

    template = env.get_template("tracker.html.j2")
    review_template = env.get_template("review.html.j2")
    sponsorship_template = env.get_template("sponsorships.html.j2")
    site_types_template = env.get_template("site-types.html.j2")
    winners_template = env.get_template("winners.html.j2")
    active_sweepstakes_template = env.get_template("active-sweepstakes.html.j2")
    methodology_template = env.get_template("methodology.html.j2")

    html = template.render(
        sites=sites,
        last_updated=last_updated_str,
        last_updated_iso=now.date().isoformat(),
    )

    OUTPUT_HTML.write_text(clean_generated_html(html), encoding="utf-8")
    sponsorship_html = sponsorship_template.render(last_updated=last_updated_str)
    (BASE / "sponsorships.html").write_text(
        clean_generated_html(sponsorship_html),
        encoding="utf-8",
    )
    type_examples = {
        type_name: [site["name"] for site in sites if site.get("theme", "other") == type_name]
        for type_name in SITE_TYPES
    }
    site_types_html = site_types_template.render(
        site_types=SITE_TYPES,
        type_examples=type_examples,
        last_updated=last_updated_str,
    )
    (BASE / "site-types.html").write_text(
        clean_generated_html(site_types_html),
        encoding="utf-8",
    )
    winners_data = json.loads(WINNERS_FILE.read_text(encoding="utf-8")) if WINNERS_FILE.exists() else {"winners": []}
    winners_html = winners_template.render(
        winners=winners_data.get("winners", []),
        last_updated=last_updated_str,
    )
    (BASE / "winners.html").write_text(
        clean_generated_html(winners_html),
        encoding="utf-8",
    )
    active_sweeps_data = json.loads(ACTIVE_SWEEPS_FILE.read_text(encoding="utf-8")) if ACTIVE_SWEEPS_FILE.exists() else {"promotions": []}
    active_sweeps_html = active_sweepstakes_template.render(
        promotions=active_sweeps_data.get("promotions", []),
        last_updated=last_updated_str,
    )
    (BASE / "active-sweepstakes.html").write_text(
        clean_generated_html(active_sweeps_html),
        encoding="utf-8",
    )
    methodology_html = methodology_template.render(
        last_updated=last_updated_str,
        last_updated_iso=now.date().isoformat(),
    )
    (BASE / "methodology.html").write_text(
        clean_generated_html(methodology_html),
        encoding="utf-8",
    )
    REVIEWS_DIR.mkdir(exist_ok=True)
    for site in sites:
        review_html = review_template.render(
            site=site,
            last_updated=last_updated_str,
            last_updated_iso=now.date().isoformat(),
        )
        (REVIEWS_DIR / f"{site['slug']}.html").write_text(
            clean_generated_html(review_html),
            encoding="utf-8",
        )
    sitemap_urls = [
        f"{SITE_ORIGIN}/",
        f"{SITE_ORIGIN}/winners",
        f"{SITE_ORIGIN}/site-types",
        f"{SITE_ORIGIN}/methodology",
        f"{SITE_ORIGIN}/sponsorships",
        *[f"{SITE_ORIGIN}/reviews/{site['slug']}" for site in sites],
    ]
    sitemap = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        *[
            f"  <url><loc>{url}</loc><lastmod>{now.date().isoformat()}</lastmod></url>"
            for url in sitemap_urls
        ],
        "</urlset>",
    ]
    (BASE / "sitemap.xml").write_text("\n".join(sitemap) + "\n", encoding="utf-8")

    print(f"Successfully rebuilt {OUTPUT_HTML}")
    print(f"  {len(sites)} sites and review pages included")
    print(f"  Last updated: {last_updated_str}")


if __name__ == "__main__":
    main()
