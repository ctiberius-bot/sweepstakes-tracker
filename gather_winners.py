#!/usr/bin/env python3
"""Collect winner reports from community feeds and official operator pages."""

import argparse
import hashlib
import html
import json
import re
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path

from winner_db import connect, export_json, unsent_reports, upsert_reports

BASE = Path(__file__).parent
SOURCES_FILE = BASE / "data" / "winner_sources.json"
STATE_FILE = BASE / "data" / "winner_state.json"
STATUS_FILE = BASE / "data" / "winner_source_status.json"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        value = " ".join(data.split())
        if value:
            self.parts.append(value)

    def text(self):
        return " ".join(self.parts)


def read_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fetch_bytes(url):
    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
    })
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def fetch_html(url):
    try:
        return fetch_bytes(url).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        if error.code not in (403, 429):
            raise
    # Several sweepstakes operators serve their public winner pages only after
    # a normal browser challenge. The scheduled runner installs Chromium for
    # this read-only fallback; it never enters a promotion or submits a form.
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(user_agent=USER_AGENT, locale="en-US")
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2500)
        content = page.locator("body").inner_text()
        browser.close()
    return content


def node_text(node, tag):
    child = node.find(tag)
    return (child.text or "").strip() if child is not None else ""


def report_id(source_id, *parts):
    identity = ":".join(str(part).strip().lower() for part in parts if part)
    return hashlib.sha256(f"{source_id}:{identity}".encode()).hexdigest()[:24]


def display_date(value):
    return value.strftime("%B %d, %Y").replace(" 0", " ")


def parse_public_date(value, now):
    cleaned = re.sub(r"\s+", " ", value.replace(",", " ")).strip()
    for date_format in ("%B %d %Y", "%b %d %Y", "%B %d", "%b %d"):
        try:
            parsed = datetime.strptime(cleaned, date_format).replace(tzinfo=timezone.utc)
            if "%Y" not in date_format:
                parsed = parsed.replace(year=now.year)
                if parsed > now + timedelta(days=7):
                    parsed = parsed.replace(year=now.year - 1)
            return parsed
        except ValueError:
            continue
    raise ValueError(f"Unsupported winner date: {value}")


def fetch_rss(source):
    root = ET.fromstring(fetch_bytes(source["url"]))
    reports = []
    for item in root.findall("./channel/item"):
        title = node_text(item, "title")
        link = node_text(item, "link")
        guid = node_text(item, "guid")
        author = node_text(item, "{http://purl.org/dc/elements/1.1/}creator")
        try:
            published = parsedate_to_datetime(node_text(item, "pubDate")).astimezone(timezone.utc)
        except (TypeError, ValueError):
            published = datetime.now(timezone.utc)
        reports.append({
            "id": report_id(source["id"], guid, link, title),
            "title": title or "Winner report",
            "url": link or source["homepage"],
            "author": author,
            "published_at": published.isoformat().replace("+00:00", "Z"),
            "published_display": display_date(published),
            "source_id": source["id"],
            "source_name": source["name"],
            "source_type": "community_report",
            "verification_level": "source_reported",
        })
    return reports


def fetch_html_regex(source):
    parser = TextExtractor()
    parser.feed(fetch_html(source["url"]))
    page_text = html.unescape(parser.text())
    now = datetime.now(timezone.utc)
    maximum_age = timedelta(days=int(source.get("max_age_days", 45)))
    reports = []
    for match in re.finditer(source["pattern"], page_text, re.IGNORECASE):
        values = {key: (value or "").strip() for key, value in match.groupdict().items()}
        try:
            published = parse_public_date(values["date"], now)
        except (KeyError, ValueError):
            continue
        if now - published > maximum_age or published > now + timedelta(days=1):
            continue
        winner = values.get("winner", "")
        location = values.get("location", "")
        prize = values.get("prize", "")
        promotion = values.get("promotion", "") or prize
        title = f"{winner} won {prize}".strip()
        if location:
            title += f" ({location})"
        reports.append({
            "id": report_id(source["id"], winner, location, prize, published.date().isoformat()),
            "title": title,
            "winner_name": winner,
            "privacy_label": winner,
            "promotion_name": promotion,
            "prize": prize,
            "operator": source.get("operator", source["name"]),
            "drawing_date": published.date().isoformat(),
            "url": source.get("report_url", source["url"]),
            "author": "",
            "published_at": published.isoformat().replace("+00:00", "Z"),
            "published_display": display_date(published),
            "source_id": source["id"],
            "source_name": source["name"],
            "source_type": "operator_announcement",
            "verification_level": "operator_published",
        })
    unique = {report["id"]: report for report in reports}
    if source.get("require_matches") and not unique:
        excerpt = re.sub(r"\s+", " ", page_text).strip()[:300]
        raise ValueError(f"Winner page loaded, but no expected records matched. Page excerpt: {excerpt}")
    return list(unique.values())


def collect(source):
    if source["type"] == "rss":
        return fetch_rss(source)
    if source["type"] == "html_regex":
        return fetch_html_regex(source)
    raise ValueError(f"Unknown source type: {source['type']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-only", action="store_true", help="Remember current items without publishing them.")
    args = parser.parse_args()
    sources = read_json(SOURCES_FILE, {"sources": []})["sources"]
    state = read_json(STATE_FILE, {"seen": [], "sent": []})
    seen = set(state.get("seen", []))
    fetched = []
    checks = []
    checked_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    for source in sources:
        try:
            reports = collect(source)
            fetched.extend(reports)
            checks.append({
                "source_id": source["id"], "source_name": source["name"],
                "status": "ok", "reports_found": len(reports), "checked_at": checked_at,
            })
        except Exception as error:  # A broken source must not erase healthy-source results.
            checks.append({
                "source_id": source["id"], "source_name": source["name"],
                "status": "error", "reports_found": 0, "checked_at": checked_at,
                "error": f"{type(error).__name__}: {error}"[:500],
            })

    if sources and not any(check["status"] == "ok" for check in checks):
        write_json(STATUS_FILE, {"checked_at": checked_at, "sources": checks})
        raise SystemExit("Every configured winner source failed.")

    fetched.sort(key=lambda report: report["published_at"], reverse=True)
    new_reports = [report for report in fetched if report["id"] not in seen]
    state["seen"] = list(dict.fromkeys([report["id"] for report in fetched] + list(seen)))[:5000]
    with connect() as database:
        upsert_reports(database, fetched)
        if args.seed_only:
            seeded_at = checked_at
            database.executemany(
                "UPDATE winner_reports SET sent_at = COALESCE(sent_at, ?) WHERE id = ?",
                [(seeded_at, report["id"]) for report in fetched],
            )
            database.commit()
        sent_ids = set(state.get("sent", []))
        if sent_ids:
            database.executemany(
                "UPDATE winner_reports SET sent_at = COALESCE(sent_at, ?) WHERE id = ?",
                [(checked_at, item_id) for item_id in sent_ids],
            )
            database.commit()
        pending_count = len(unsent_reports(database))
        export_json(database)
    write_json(STATE_FILE, state)
    write_json(STATUS_FILE, {"checked_at": checked_at, "sources": checks})
    print(json.dumps({
        "new_count": 0 if args.seed_only else len(new_reports),
        "pending_count": 0 if args.seed_only else pending_count,
        "seeded_count": len(fetched) if args.seed_only else 0,
        "source_errors": sum(check["status"] == "error" for check in checks),
    }))


if __name__ == "__main__":
    main()
