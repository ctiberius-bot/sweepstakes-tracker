#!/usr/bin/env python3
"""Refresh source-backed profile details without guessing missing facts."""

import hashlib
import html
import json
import re
import ssl
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

BASE = Path(__file__).parent
DATA_FILE = BASE / "data.json"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36 "
    "SafeTrackerPublicProfileRefresh/1.2"
)


def fetch(url):
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
        },
    )
    with urlopen(request, timeout=25, context=ssl.create_default_context()) as response:
        body = response.read(2_000_000).decode(
            response.headers.get_content_charset() or "utf-8",
            errors="replace",
        )
        return response.geturl(), response.status, body


def fetch_with_browser(url):
    """Use a real browser for public pages that reject ordinary HTTP clients."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(locale="en-US")
        response = page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        page.wait_for_timeout(1_500)
        body = page.content()
        final_url = page.url
        status = response.status if response else 200
        browser.close()
        return final_url, status, body


def plain_text(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def refresh_mondosweeps(site, body, checked_at):
    cards = re.findall(
        r'<a[^>]+href="(?P<href>/Sweepstakes/[^"]+)"[^>]*>(?P<body>.*?)</a>',
        body,
        flags=re.I | re.S,
    )
    prizes, seen = [], set()
    for href, card_body in cards:
        heading = re.search(r"<h[1-6][^>]*>(.*?)</h[1-6]>", card_body, flags=re.I | re.S)
        if not heading:
            continue
        label = plain_text(heading.group(1))
        if not label or label.casefold() in seen:
            continue
        seen.add(label.casefold())
        frequency = re.search(r"Enter\s+(\d+)x\s+daily", plain_text(card_body), flags=re.I)
        prizes.append(
            {
                "label": label,
                "entry_url": urljoin(site["link"], href),
                "entry_frequency": f"Up to {frequency.group(1)} entries daily" if frequency else "See the official entry page",
                "login_required": "No account login shown; entering requires a valid email address.",
                "last_won": "No prize-specific public winner date found in the homepage snapshot.",
                "next_drawing": "See the promotion's current official rules.",
                "status": "Currently listed",
                "last_verified": checked_at,
            }
        )
    winner_matches = re.findall(
        r"([A-Z][A-Za-z .'-]+)\s+won\s+(\$[\d,]+)\s+on\s+([A-Z][a-z]+\s+\d{1,2})",
        plain_text(body),
    )
    latest_by_prize = {}
    for _, prize, won_on in winner_matches:
        latest_by_prize.setdefault(prize, f"{won_on}, {checked_at[:4]}")
    for prize in prizes:
        if prize["label"] in latest_by_prize:
            prize["last_won"] = latest_by_prize[prize["label"]]
    if prizes:
        site["prize_items"] = prizes
        site["prizes"] = "; ".join(prize["label"] for prize in prizes)
    site["winner_evidence"] = "The public homepage displays recent dated winners; prize-specific pages and rules remain the controlling sources."


def main():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    checked_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    changed_count = 0

    for site in data["sites"]:
        url = site.get("scrape_url") or site.get("link")
        refresh = site.setdefault("profile_refresh", {})
        refresh["checked_at"] = checked_at
        refresh["source_url"] = url
        if not url or url == "#":
            refresh.update(status="not_applicable", changed=False)
            continue
        try:
            try:
                final_url, status_code, body = fetch(url)
            except HTTPError as error:
                if error.code in {401, 403, 429} and site.get("browser_refresh"):
                    try:
                        final_url, status_code, body = fetch_with_browser(url)
                    except Exception:
                        raise error
                else:
                    raise
            digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
            prior_digest = refresh.get("content_hash")
            changed = bool(prior_digest and prior_digest != digest)
            refresh.update(
                status="reachable",
                http_status=status_code,
                final_url=final_url,
                content_hash=digest,
                changed=changed,
                last_success=checked_at,
                error=None,
            )
            changed_count += int(changed)
            if site.get("slug") == "mondosweeps":
                refresh_mondosweeps(site, body, checked_at)
        except HTTPError as error:
            refresh.update(
                status="protected" if error.code in {401, 403, 429} else f"http_{error.code}",
                http_status=error.code,
                changed=False,
                error=f"HTTP {error.code}",
            )
        except (URLError, TimeoutError, ssl.SSLError) as error:
            refresh.update(status="unreachable", changed=False, error=type(error).__name__)

    data["last_profile_refresh"] = checked_at
    DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Checked {len(data['sites'])} public profile sources; {changed_count} source pages changed.")


if __name__ == "__main__":
    main()
