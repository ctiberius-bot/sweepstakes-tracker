#!/usr/bin/env python3
"""
Simplified Sweepstakes Tracker Rebuilder
========================================
Loads sites from data.json, updates the last_updated timestamp,
and generates a clean index.html using the Jinja2 template.
"""

import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit
from jinja2 import Environment, FileSystemLoader, select_autoescape

BASE = Path(__file__).parent
TEMPLATE_DIR = BASE / "templates"
OUTPUT_HTML = BASE / "index.html"
DATA_FILE = BASE / "data.json"
MONETIZATION_FILE = BASE / "data" / "monetization.json"
REVIEWS_DIR = BASE / "reviews"
SWEEPSTAKES_DIR = BASE / "sweepstakes"
WINNERS_FILE = BASE / "data" / "winners.json"
ACTIVE_SWEEPS_FILE = BASE / "data" / "active_sweepstakes.json"
EDITORIAL_FILE = BASE / "data" / "editorial.json"
GUIDES_DIR = BASE / "guides"
SITE_ORIGIN = "https://sweeps.safetrackerhub.com"
SITE_TYPES = {
    "limited": "A specific sweepstakes with a fixed closing date. It remains in the active inventory until it ends, then moves to the historical record.",
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


def promotion_as_site(promotion):
    """Normalize a fixed-term promotion into the same inventory shape as recurring sweepstakes."""
    value = promotion.get("value") or 0
    frequency = promotion.get("entry_frequency", "One time")
    transparency = 3.5 if "verified listing" in promotion.get("source_name", "").lower() else 4.5
    fulfillment = 4.5
    entry_model = 3.0 if frequency == "One time" else 3.8
    win_realism = 3.2 if value and value <= 5000 else 4.2
    marketing = 4.2
    score_inputs = {
        "transparency": transparency,
        "fulfillment": fulfillment,
        "entry_model": entry_model,
        "win_realism": win_realism,
        "marketing": marketing,
    }
    score = round(transparency * .30 + fulfillment * .25 + entry_model * .20 + win_realism * .15 + marketing * .10, 1)
    closes = date.fromisoformat(promotion["closes"])
    return {
        "name": promotion["title"], "score": score, "theme": "limited",
        "prizes": promotion["prize"],
        "draw": f"{frequency} · Ends {closes.strftime('%B %d, %Y')}",
        "unsub": "This is a limited promotion. Use the organizer’s email opt-out link if entry creates marketing subscriptions.",
        "redFlags": "Limited independent fulfillment history. Confirm the sponsor, eligibility, free entry method, and official rules before submitting personal information.",
        "link": promotion["entry_url"], "scrape_url": promotion["source_url"], "slug": promotion["slug"],
        "score_inputs": score_inputs, "eligibility": promotion["eligibility"],
        "entry_requirements": f"{frequency} entry. Confirm all entry methods and limits in the official rules.",
        "winner_evidence": "No completed fulfillment record is yet available for this open promotion.",
        "marketing_intensity": "Not independently measured. Entry may enroll the visitor in sponsor marketing; review the form carefully.",
        "data_practices": "Data is submitted to the sponsor or its promotion administrator under the rules and privacy terms linked from the entry flow.",
        "prize_items": [{
            "label": promotion["prize_details"], "login_required": "Confirm on the entry page.",
            "last_won": "Promotion still open; no final winner recorded.",
            "next_drawing": promotion.get("closes_time", promotion["closes"]),
            "status": "Open, limited promotion",
            "entry_url": promotion["entry_url"],
            "last_verified": promotion["last_verified"],
        }],
        "profile_refresh": {"status": "manually_verified", "checked_at": promotion["last_verified"], "source_url": promotion["source_url"]},
        "promotion_status": "open", "promotion_format": "limited", "closes": promotion["closes"],
        "source_name": promotion["source_name"],
        "logo_asset": promotion.get("logo_asset", ""),
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
    checked_at = site.get("profile_refresh", {}).get("checked_at", "")
    checked_date = checked_at[:10] if checked_at else "the most recent profile check"
    if site.get("prize_items"):
        return [
            {
                "login_required": site.get("entry_requirements", "Check the official entry page for account requirements."),
                "last_won": "No prize-specific public winner date recorded.",
                "next_drawing": "Not yet recorded; verify the current official rules.",
                "status": f"Verified as listed on {checked_date}",
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
            "status": f"Verified as listed on {checked_date}",
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


def display_date(value):
    """Preserve readable dates and trim timestamps only when they are ISO-formatted."""
    text = str(value or "").strip()
    if len(text) >= 10 and text[4:5] == "-" and text[7:8] == "-":
        return text[:10]
    return text


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
    active_sweeps_data = json.loads(ACTIVE_SWEEPS_FILE.read_text(encoding="utf-8")) if ACTIVE_SWEEPS_FILE.exists() else {"promotions": []}
    today = datetime.now(timezone.utc).date()
    sites = [
        *sites,
        *[
            promotion_as_site(promotion)
            for promotion in active_sweeps_data.get("promotions", [])
            if date.fromisoformat(promotion["closes"]) >= today
        ],
    ]
    monetization = json.loads(MONETIZATION_FILE.read_text(encoding="utf-8")) if MONETIZATION_FILE.exists() else {}
    affiliate_links = monetization.get("affiliate_links", {})
    sites.sort(key=lambda site: (float(site["score"]), site["name"].casefold()))
    for site in sites:
        site["slug"] = site.get("slug") or slugify(site["name"])
        if affiliate_links.get(site["slug"]):
            site["affiliate_url"] = affiliate_links[site["slug"]]
        site["initials"] = site_initials(site["name"])
        site["mark_hue"] = sum(ord(char) for char in site["name"]) % 360
        site["favicon_url"] = favicon_url(site.get("link"))
        site["outbound_url"] = site.get("affiliate_url") or site.get("link")
        site["is_affiliate"] = bool(site.get("affiliate_url"))
        site["placement_tier"] = site.get("placement_tier", "standard")
        site["logo_asset"] = site.get("logo_asset") or (
            "assets/logos/mondosweeps.png" if site["slug"] == "mondosweeps" else
            "assets/logos/winstakes.png" if site["slug"] == "winstakes" else
            ""
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
    env.filters["display_date"] = display_date

    template = env.get_template("tracker.html.j2")
    review_template = env.get_template("review.html.j2")
    sponsorship_template = env.get_template("sponsorships.html.j2")
    site_types_template = env.get_template("site-types.html.j2")
    winners_template = env.get_template("winners.html.j2")
    active_sweepstakes_template = env.get_template("active-sweepstakes.html.j2")
    sweepstakes_detail_template = env.get_template("sweepstakes-detail.html.j2")
    methodology_template = env.get_template("methodology.html.j2")
    contact_template = env.get_template("contact.html.j2")
    about_template = env.get_template("about.html.j2")
    editorial_template = env.get_template("editorial.html.j2")
    guides_template = env.get_template("guides.html.j2")
    editorial_data = json.loads(EDITORIAL_FILE.read_text(encoding="utf-8"))
    editorial_pages = editorial_data.get("articles", [])
    editorial_pages = sorted(
        editorial_pages,
        key=lambda article: (article.get("published", "2026-07-26"), article["title"]),
        reverse=True,
    )

    html = template.render(
        sites=sites,
        editorial_pages=editorial_pages,
        last_updated=last_updated_str,
        last_updated_iso=now.date().isoformat(),
    )

    OUTPUT_HTML.write_text(clean_generated_html(html), encoding="utf-8")
    sponsorship_html = sponsorship_template.render(last_updated=last_updated_str, monetization=monetization)
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
    active_promotions = active_sweeps_data.get("promotions", [])
    today = now.date()
    for promotion in active_promotions:
        close_date = date.fromisoformat(promotion["closes"])
        days_left = (close_date - today).days
        promotion["days_left"] = days_left
        promotion["deadline_label"] = (
            "Ends today" if days_left == 0 else
            "Ends tomorrow" if days_left == 1 else
            f"Ends in {days_left} days" if days_left > 1 else
            "Closed"
        )
        value = promotion.get("value")
        promotion["value_label"] = f"${value:,.0f}" if value else "See prize details"
    active_promotions = sorted(
        [promotion for promotion in active_promotions if promotion["days_left"] >= 0],
        key=lambda item: (item["closes"], -(item.get("value") or 0)),
    )
    categories = sorted({promotion["category"] for promotion in active_promotions})
    frequencies = sorted({promotion["entry_frequency"] for promotion in active_promotions})
    list_schema = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "Active sweepstakes",
        "numberOfItems": len(active_promotions),
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": position,
                "url": f"{SITE_ORIGIN}/sweepstakes/{promotion['slug']}",
                "name": promotion["title"],
            }
            for position, promotion in enumerate(active_promotions, start=1)
        ],
    }
    active_sweeps_html = active_sweepstakes_template.render(
        promotions=active_promotions,
        categories=categories,
        frequencies=frequencies,
        ending_soon_count=sum(1 for promotion in active_promotions if promotion["days_left"] <= 7),
        daily_count=sum(1 for promotion in active_promotions if promotion["entry_frequency"] == "Daily"),
        structured_data=list_schema,
        last_updated=last_updated_str,
    )
    (BASE / "active-sweepstakes.html").write_text(
        clean_generated_html(active_sweeps_html),
        encoding="utf-8",
    )
    collection_pages = [
        ("sweepstakes-ending-soon.html", "Sweepstakes ending soon", "Sweepstakes Ending Soon", "Verified promotions closing within the next seven days, ordered by deadline.", "Find verified sweepstakes ending within seven days.", lambda p: p["days_left"] <= 7),
        ("daily-entry-sweepstakes.html", "Daily-entry sweepstakes", "Daily-Entry Sweepstakes", "Promotions that permit another entry each day. Confirm reset times in the organizer’s rules.", "Browse active daily-entry sweepstakes.", lambda p: p["entry_frequency"] == "Daily"),
        ("cash-sweepstakes.html", "Cash and gift-card sweepstakes", "Cash and Gift-Card Sweepstakes", "Current promotions where the advertised prize includes cash, prepaid cards, or gift cards.", "Browse verified cash and gift-card sweepstakes.", lambda p: p["category"] == "Cash & gift cards"),
        ("travel-sweepstakes.html", "Travel sweepstakes", "Travel Sweepstakes and Trip Giveaways", "Current trip and experience promotions with advertised package values and eligibility details.", "Browse current travel sweepstakes and trip giveaways.", lambda p: p["category"] in {"Travel", "Experiences"}),
        ("vehicle-sweepstakes.html", "Vehicle sweepstakes", "Vehicle Sweepstakes and Giveaways", "Current vehicle and high-value equipment promotions.", "Browse active vehicle sweepstakes and giveaways.", lambda p: p["category"] in {"Vehicles", "Home & outdoors"}),
    ]
    for filename, heading, page_title, introduction, meta_description, predicate in collection_pages:
        subset = [promotion for promotion in active_promotions if predicate(promotion)]
        collection_schema = {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": heading,
            "numberOfItems": len(subset),
            "itemListElement": [
                {"@type": "ListItem", "position": position, "url": f"{SITE_ORIGIN}/sweepstakes/{promotion['slug']}", "name": promotion["title"]}
                for position, promotion in enumerate(subset, start=1)
            ],
        }
        collection_html = active_sweepstakes_template.render(
            promotions=subset,
            categories=sorted({promotion["category"] for promotion in subset}),
            frequencies=sorted({promotion["entry_frequency"] for promotion in subset}),
            ending_soon_count=sum(1 for promotion in subset if promotion["days_left"] <= 7),
            daily_count=sum(1 for promotion in subset if promotion["entry_frequency"] == "Daily"),
            structured_data=collection_schema,
            canonical_url=f"{SITE_ORIGIN}/{filename.removesuffix('.html')}",
            heading=heading,
            page_title=page_title,
            introduction=introduction,
            meta_description=meta_description,
            last_updated=last_updated_str,
        )
        (BASE / filename).write_text(clean_generated_html(collection_html), encoding="utf-8")
    SWEEPSTAKES_DIR.mkdir(exist_ok=True)
    active_slugs = {promotion["slug"] for promotion in active_promotions}
    for existing in SWEEPSTAKES_DIR.glob("*.html"):
        if existing.stem not in active_slugs:
            existing.unlink()
    for promotion in active_promotions:
        promotion_schema = {
            "@context": "https://schema.org",
            "@type": "Event",
            "name": promotion["title"],
            "description": promotion["prize"],
            "endDate": promotion["closes"],
            "eventAttendanceMode": "https://schema.org/OnlineEventAttendanceMode",
            "eventStatus": "https://schema.org/EventScheduled",
            "location": {"@type": "VirtualLocation", "url": promotion["entry_url"]},
            "organizer": {"@type": "Organization", "name": promotion["sponsor"]},
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD", "url": promotion["entry_url"]},
        }
        detail_html = sweepstakes_detail_template.render(
            promotion=promotion,
            structured_data=promotion_schema,
            last_updated=last_updated_str,
        )
        (SWEEPSTAKES_DIR / f"{promotion['slug']}.html").write_text(
            clean_generated_html(detail_html),
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
    about_html = about_template.render(
        last_updated=last_updated_str,
        last_updated_iso=now.date().isoformat(),
    )
    (BASE / "about.html").write_text(
        clean_generated_html(about_html),
        encoding="utf-8",
    )
    guides_schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "Sweepstakes Safety and Strategy Guides",
        "url": f"{SITE_ORIGIN}/guides",
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": len(editorial_pages),
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": position,
                    "url": f"{SITE_ORIGIN}/guides/{article['slug']}",
                    "name": article["title"],
                }
                for position, article in enumerate(editorial_pages, start=1)
            ],
        },
    }
    guides_html = guides_template.render(
        articles=editorial_pages,
        latest=editorial_pages[0] if editorial_pages else None,
        structured_data=guides_schema,
        last_updated=last_updated_str,
    )
    GUIDES_DIR.mkdir(exist_ok=True)
    (GUIDES_DIR / "index.html").write_text(
        clean_generated_html(guides_html),
        encoding="utf-8",
    )
    REVIEWS_DIR.mkdir(exist_ok=True)
    current_review_slugs = {site["slug"] for site in sites}
    for existing in REVIEWS_DIR.glob("*.html"):
        if existing.stem not in current_review_slugs:
            existing.unlink()
    for site in sites:
        theme_guide_slugs = {
            "limited": ["daily-sweepstakes-entry-strategy", "legitimate-sweepstakes-sites", "sweepstakes-taxes"],
            "daily": ["daily-sweepstakes-entry-strategy", "dedicated-sweepstakes-email", "how-sweepstakes-winners-are-verified"],
            "globalizer": ["dedicated-sweepstakes-email", "how-to-spot-sweepstakes-scams", "how-sweepstakes-winners-are-verified"],
            "leadgen": ["how-to-spot-sweepstakes-scams", "dedicated-sweepstakes-email", "legitimate-sweepstakes-sites"],
            "rewards": ["dedicated-sweepstakes-email", "legitimate-sweepstakes-sites", "sweepstakes-taxes"],
            "directory": ["legitimate-sweepstakes-sites", "how-to-spot-sweepstakes-scams", "daily-sweepstakes-entry-strategy"],
            "premium-directory": ["legitimate-sweepstakes-sites", "daily-sweepstakes-entry-strategy", "dedicated-sweepstakes-email"],
            "local-directory": ["legitimate-sweepstakes-sites", "daily-sweepstakes-entry-strategy", "how-sweepstakes-winners-are-verified"],
        }
        profile_guide_slugs = {
            "prizegrab": ["is-prizegrab-legitimate", "daily-sweepstakes-entry-strategy", "dedicated-sweepstakes-email"],
            "publishers-clearing-house-pch": ["pch-winner-notification-scam", "how-to-spot-sweepstakes-scams", "how-sweepstakes-winners-are-verified"],
            "sweepstakes-advantage": ["sweepstakes-advantage-alternatives", "legitimate-sweepstakes-sites", "daily-sweepstakes-entry-strategy"],
            "mondosweeps": ["best-daily-entry-sweepstakes-sites", "daily-sweepstakes-entry-strategy", "dedicated-sweepstakes-email"],
            "winloot-globalizer": ["best-daily-entry-sweepstakes-sites", "how-to-spot-sweepstakes-scams", "dedicated-sweepstakes-email"],
        }
        selected_slugs = profile_guide_slugs.get(site["slug"]) or theme_guide_slugs.get(
            site.get("theme", "other"),
            ["how-to-spot-sweepstakes-scams", "legitimate-sweepstakes-sites", "how-sweepstakes-winners-are-verified"],
        )
        selected_slugs = [*selected_slugs, "2026-sweepstakes-safety-report"]
        related_guides = [article for article in editorial_pages if article["slug"] in selected_slugs]
        review_html = review_template.render(
            site=site,
            related_guides=related_guides,
            last_updated=last_updated_str,
            last_updated_iso=now.date().isoformat(),
        )
        (REVIEWS_DIR / f"{site['slug']}.html").write_text(
            clean_generated_html(review_html),
            encoding="utf-8",
        )
    GUIDES_DIR.mkdir(exist_ok=True)
    current_guide_slugs = {article["slug"] for article in editorial_pages}
    for existing in GUIDES_DIR.glob("*.html"):
        if existing.name != "index.html" and existing.stem not in current_guide_slugs:
            existing.unlink()
    for article in editorial_pages:
        article_html = editorial_template.render(
            article=article,
            editorial_pages=editorial_pages,
            last_updated=last_updated_str,
            last_updated_iso=now.date().isoformat(),
        )
        (GUIDES_DIR / f"{article['slug']}.html").write_text(
            clean_generated_html(article_html),
            encoding="utf-8",
        )
    sitemap_urls = [
        f"{SITE_ORIGIN}/",
        f"{SITE_ORIGIN}/winners",
        f"{SITE_ORIGIN}/active-sweepstakes",
        *[f"{SITE_ORIGIN}/{filename.removesuffix('.html')}" for filename, *_ in collection_pages],
        f"{SITE_ORIGIN}/site-types",
        f"{SITE_ORIGIN}/methodology",
        f"{SITE_ORIGIN}/contact",
        f"{SITE_ORIGIN}/about",
        f"{SITE_ORIGIN}/sponsorships",
        f"{SITE_ORIGIN}/guides",
        *[f"{SITE_ORIGIN}/guides/{article['slug']}" for article in editorial_pages],
        *[f"{SITE_ORIGIN}/reviews/{site['slug']}" for site in sites],
        *[f"{SITE_ORIGIN}/sweepstakes/{promotion['slug']}" for promotion in active_promotions],
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
