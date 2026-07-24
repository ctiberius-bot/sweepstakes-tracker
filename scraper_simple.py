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

TYPE_PROFILE_DEFAULTS = {
    "directory": {
        "entry_requirements": "The directory is generally public. Each linked sponsor sets its own account, eligibility, and entry requirements.",
        "winner_evidence": "The directory does not fulfill most prizes; verify winners with each outside sponsor.",
        "marketing_intensity": "Directory newsletters are optional, while marketing varies widely at linked sponsors.",
        "data_practices": "Opening an outside listing moves the visitor to that sponsor's privacy and data-sharing terms.",
    },
    "premium-directory": {
        "entry_requirements": "Basic listings may be public; saved searches, alerts, or early listings can require an account or paid membership.",
        "winner_evidence": "The directory usually does not fulfill prizes; verify with each outside sponsor.",
        "marketing_intensity": "Account notices and membership promotions may supplement normal newsletters.",
        "data_practices": "Directory account data is separate from information submitted to outside sponsors.",
    },
    "local-directory": {
        "entry_requirements": "Listings are usually public, but eligibility and entry requirements depend on location and sponsor.",
        "winner_evidence": "Verify fulfillment with the local sponsor named in each listing.",
        "marketing_intensity": "Newsletter volume is typically moderate; outside sponsors vary.",
        "data_practices": "Local sponsors control the information submitted on their own entry forms.",
    },
    "daily": {
        "entry_requirements": "Most drawings accept an email address and permit repeated daily entries; confirm each promotion's limit.",
        "winner_evidence": "Look for dated winner names or initials on the operator's winners page and in promotion-specific rules.",
        "marketing_intensity": "Daily-entry operators commonly send frequent reminders and promotional messages.",
        "data_practices": "Entry data is used by the operator and may also be governed by promotion-specific terms.",
    },
    "globalizer": {
        "entry_requirements": "A valid email is normally required, with repeated entries or network accounts used for some promotions.",
        "winner_evidence": "Prefer dated operator winner reports and prize-specific rules; large jackpot proof may be less frequent.",
        "marketing_intensity": "Expect high-volume promotional email across related network brands.",
        "data_practices": "Information may be used across an affiliated marketing network; review opt-out and privacy-rights pages.",
    },
    "legacy": {
        "entry_requirements": "An account or email registration may be required for individual promotions.",
        "winner_evidence": "Established operators should provide official winner announcements or fulfillment records.",
        "marketing_intensity": "Promotional mail and email can be frequent even when entry is free.",
        "data_practices": "Review both the operator's account terms and the rules for the specific promotion.",
    },
    "rewards": {
        "entry_requirements": "A member account is required for personalized offers, rewards, and member-only promotions.",
        "winner_evidence": "Separate ordinary rewards redemptions from sweepstakes winner evidence and verify each promotion's rules.",
        "marketing_intensity": "Offer email, app notifications, and task reminders can be frequent.",
        "data_practices": "Profiles, surveys, shopping activity, and offer interactions can create a substantial behavioral-data record.",
    },
    "samples": {
        "entry_requirements": "A member profile, demographic qualification, and delivery address may be required; selection is not guaranteed.",
        "winner_evidence": "Sample fulfillment is campaign-based rather than a conventional drawing; confirm shipment or selection terms.",
        "marketing_intensity": "Product offers, surveys, and campaign notices may be frequent.",
        "data_practices": "Demographic and product-preference data may be shared with participating brands under campaign terms.",
    },
    "app": {
        "entry_requirements": "An app account is usually required. Device permissions, notifications, and sponsor-specific entry terms may also apply.",
        "winner_evidence": "Verify winners through the app operator and the sponsor named in each promotion.",
        "marketing_intensity": "App notifications and promotional email may be frequent.",
        "data_practices": "The app adds an account and device-data layer in addition to each promotion sponsor.",
    },
    "niche": {
        "entry_requirements": "Email registration or a site account may be required; eligibility can be tailored to the site's audience.",
        "winner_evidence": "Look for dated winner announcements and promotion-specific official rules.",
        "marketing_intensity": "Expect audience-targeted promotional email and partner offers.",
        "data_practices": "Review whether information is shared with brands serving the site's niche audience.",
    },
    "leadgen": {
        "entry_requirements": "Email and personal details may be requested before the advertised reward path is fully disclosed.",
        "winner_evidence": "Do not treat an advertised reward as fulfilled without clear rules and attributable winner evidence.",
        "marketing_intensity": "Marketing and follow-up from partners can be intensive.",
        "data_practices": "Information may be shared with advertisers or lead buyers; read consent language before submitting.",
    },
    "other": {
        "entry_requirements": "Requirements vary; verify the official site and promotion rules before providing information.",
        "winner_evidence": "Use operator-owned rules and dated winner evidence whenever available.",
        "marketing_intensity": "Not independently measured; use a dedicated sweepstakes email address.",
        "data_practices": "Review the operator and sponsor privacy terms before submitting personal information.",
    },
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


MONDOSWEEPS_PRIZES = [
    {
        "label": "$1,548,705 lump sum",
        "entry_url": "https://www.mondosweeps.com/Sweepstakes/5000000-Cash-Sweepstakes",
        "entry_frequency": "Up to 3 entries daily",
    },
    {
        "label": "$500,000 Dream Home",
        "entry_frequency": "Up to 3 entries daily",
        "next_drawing": "Promotion closes October 23, 2026; the public rules excerpt does not state the drawing date.",
    },
    {
        "label": "$300,000 cash",
        "entry_url": "https://www.mondosweeps.com/Sweepstakes/300000-Cash-Sweepstakes",
        "entry_frequency": "Up to 3 entries daily",
    },
    {
        "label": "$125,000 cash",
        "entry_url": "https://www.mondosweeps.com/Sweepstakes/125000-Cash-Sweepstakes",
        "entry_frequency": "Up to 3 entries daily",
    },
    {
        "label": "$88,888 Dream Car",
        "entry_url": "https://www.mondosweeps.com/Sweepstakes/88888-Dream-Car",
        "entry_frequency": "Up to 3 entries daily",
    },
    {"label": "$33,333 Dream Vacation", "entry_frequency": "Up to 3 entries daily"},
    {"label": "$10,000 Super Home Theater", "entry_frequency": "Up to 3 entries daily"},
    {
        "label": "$1,000 Amazon Gift Card",
        "entry_url": "https://www.mondosweeps.com/Sweepstakes/sweepstakes-1000-Amazon-G",
        "entry_frequency": "Up to 3 entries daily",
        "last_won": "November 11, 2025",
    },
    {
        "label": "$750 Visa Gift Card",
        "entry_url": "https://www.mondosweeps.com/Sweepstakes/mondosweeps-750-Visa-Gift",
        "entry_frequency": "Up to 3 entries daily",
        "last_won": "July 7, 2026",
    },
    {
        "label": "$100 cash",
        "entry_frequency": "Up to 3 entries daily",
        "last_won": "July 8, 2026",
    },
    {
        "label": "$25 Daily Cash",
        "entry_url": "https://www.mondosweeps.com/Sweepstakes/Daily-Cash-Prize-Giveaway",
        "entry_frequency": "Up to 5 entries daily",
        "last_won": "July 21, 2026",
        "next_drawing": "Daily at midnight Eastern Time",
    },
]


def split_prize_summary(value):
    """Split semicolon-separated inventory without breaking parenthetical notes."""
    items, current, depth = [], [], 0
    for char in value or "":
        if char == "(":
            depth += 1
        elif char == ")" and depth:
            depth -= 1
        if char == ";" and depth == 0:
            item = "".join(current).strip()
            if item:
                items.append(item)
            current = []
        else:
            current.append(char)
    item = "".join(current).strip()
    if item:
        items.append(item)
    return items


def prize_items(site):
    """Turn known prize examples into displayable records with verified entry URLs."""
    if site.get("prize_items"):
        return [
            {
                "login_required": site.get("entry_requirements", "Check the official entry page for account requirements."),
                "last_won": "No prize-specific public winner date recorded.",
                "next_drawing": "Not yet recorded; verify the current official rules.",
                "status": "Known when last verified",
                **item,
            }
            for item in site["prize_items"]
        ]
    if site.get("slug") == "mondosweeps":
        return [
            {
                "login_required": "No account login shown on the public entry form; a valid email is required.",
                "last_won": "No recent public winner located for this specific prize.",
                "next_drawing": "Not clearly stated on the public prize page.",
                "status": "Currently listed",
                **prize,
            }
            for prize in MONDOSWEEPS_PRIZES
        ]
    items = split_prize_summary(site.get("prizes", ""))
    return [
        {
            "label": item,
            "login_required": "Check the official entry page; login requirements are not yet recorded.",
            "last_won": "No prize-specific public winner date recorded.",
            "next_drawing": "Not yet recorded; verify the current official rules.",
            "status": "Known when last verified",
        }
        for item in items
    ] or [
        {
            "label": "No specific prizes are currently recorded.",
            "login_required": "Unknown",
            "last_won": "Not recorded",
            "next_drawing": "Not recorded",
            "status": "No public inventory recorded",
        }
    ]


def signal_summary(label, score):
    score = float(score)
    if score <= 2:
        assessment = "strong"
    elif score <= 4:
        assessment = "generally favorable"
    elif score <= 6:
        assessment = "mixed"
    elif score <= 8:
        assessment = "concerning"
    else:
        assessment = "high concern"
    return {"label": label, "score": score, "assessment": assessment}


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
        site["logo_asset"] = (
            "assets/logos/mondosweeps.png"
            if site["slug"] == "mondosweeps"
            else ""
        )
        defaults = TYPE_PROFILE_DEFAULTS.get(site.get("theme", "other"), TYPE_PROFILE_DEFAULTS["other"])
        for key, value in defaults.items():
            site.setdefault(key, value)
        site["prize_items"] = prize_items(site)
        refresh = site.setdefault("profile_refresh", {})
        refresh.setdefault("status", site.get("weekly_check_status", "not_checked"))
        refresh.setdefault("checked_at", site.get("last_scored", data.get("last_updated")))
        refresh.setdefault("source_url", site.get("scrape_url") or site.get("link"))
        inputs = site.get("score_inputs", {})
        site["risk_signals"] = [
            signal_summary("Transparency", inputs.get("transparency", site["score"])),
            signal_summary("Fulfillment evidence", inputs.get("fulfillment", site["score"])),
            signal_summary("Entry model", inputs.get("entry_model", site["score"])),
            signal_summary("Win realism", inputs.get("win_realism", site["score"])),
            signal_summary("Marketing pressure", inputs.get("marketing", site["score"])),
        ]
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
    contact_template = env.get_template("contact.html.j2")

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
    contact_html = contact_template.render(
        last_updated=last_updated_str,
        last_updated_iso=now.date().isoformat(),
    )
    (BASE / "contact.html").write_text(
        clean_generated_html(contact_html),
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
        f"{SITE_ORIGIN}/contact",
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
