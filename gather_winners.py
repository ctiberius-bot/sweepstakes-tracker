#!/usr/bin/env python3
"""Collect newly published winner reports from configured source feeds."""

import argparse
import hashlib
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from winner_db import connect, export_json, upsert_reports

BASE = Path(__file__).parent
SOURCES_FILE = BASE / "data" / "winner_sources.json"
STATE_FILE = BASE / "data" / "winner_state.json"
USER_AGENT = "SafeTracker-WinnerMonitor/1.1 (+https://sweeps.safetrackerhub.com/)"


def read_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def node_text(node, tag):
    child = node.find(tag)
    return (child.text or "").strip() if child is not None else ""


def report_id(source_id, guid, link, title):
    identity = guid or link or title
    return hashlib.sha256(f"{source_id}:{identity}".encode()).hexdigest()[:24]


def fetch_rss(source):
    request = urllib.request.Request(source["url"], headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        root = ET.fromstring(response.read())
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
            "published_display": published.strftime("%B %d, %Y").replace(" 0", " "),
            "source_id": source["id"],
            "source_name": source["name"],
            "source_type": "community_report",
            "verification_level": "source_reported",
        })
    return reports


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-only", action="store_true", help="Remember current items without publishing them.")
    args = parser.parse_args()
    sources = read_json(SOURCES_FILE, {"sources": []})["sources"]
    state = read_json(STATE_FILE, {"seen": [], "sent": []})
    seen = set(state.get("seen", []))
    fetched = []
    for source in sources:
        if source.get("type") == "rss":
            fetched.extend(fetch_rss(source))
    fetched.sort(key=lambda report: report["published_at"], reverse=True)
    new_reports = [report for report in fetched if report["id"] not in seen]
    state["seen"] = list(dict.fromkeys([report["id"] for report in fetched] + list(seen)))[:2000]
    with connect() as database:
        upsert_reports(database, fetched)
        if args.seed_only:
            seeded_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            database.executemany(
                "UPDATE winner_reports SET sent_at = COALESCE(sent_at, ?) WHERE id = ?",
                [(seeded_at, report["id"]) for report in fetched],
            )
            database.commit()
        sent_ids = set(state.get("sent", []))
        if sent_ids:
            database.executemany(
                "UPDATE winner_reports SET sent_at = COALESCE(sent_at, ?) WHERE id = ?",
                [(datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), report_id) for report_id in sent_ids],
            )
            database.commit()
        export_json(database)
    write_json(STATE_FILE, state)
    print(json.dumps({
        "new_count": 0 if args.seed_only else len(new_reports),
        "seeded_count": len(fetched) if args.seed_only else 0,
    }))


if __name__ == "__main__":
    main()
