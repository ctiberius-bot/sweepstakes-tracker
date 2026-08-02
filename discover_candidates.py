#!/usr/bin/env python3
"""Discover possible SafeTracker inventory records without publishing them.

This job intentionally stops at a review queue. External pages are untrusted
discovery signals; they never modify data.json or generated public pages.
"""

import argparse
import hashlib
import json
import os
import re
import ssl
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

BASE = Path(__file__).parent
SOURCES_FILE = BASE / "data" / "discovery_sources.json"
QUEUE_FILE = BASE / "data" / "discovery_candidates.json"
INVENTORY_FILE = BASE / "data.json"
PROMOTIONS_FILE = BASE / "data" / "active_sweepstakes.json"
REPORT_FILE = BASE / "DISCOVERY_REVIEW.md"
USER_AGENT = "SafeTrackerHub-Discovery/1.0 (+https://sweeps.safetrackerhub.com/contact)"
TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "source", "utm_campaign", "utm_content", "utm_medium", "utm_source", "utm_term"}
MATCH_TERMS = re.compile(r"\b(sweepstakes?|giveaways?|contest|instant win|win a|enter to win)\b", re.I)
EXCLUDE_TERMS = re.compile(
    r"\b(login|sign in|privacy|contact|about|newsletter|facebook|instagram|twitter|pinterest|terms of use|"
    r"favorites?|all categories|all sweepstakes|new sweepstakes|expiring sweepstakes|top 30|"
    r"24 hour entry|daily entry|weekly entry|monthly entry|one time entry|instant win games?)\b",
    re.I,
)
LIMITED_TERMS = re.compile(r"\b(win|giveaway|contest|sweepstakes|trip|cash|gift card|car|truck|prize)\b", re.I)
RECURRING_TERMS = re.compile(r"\b(directory|rewards|daily sweepstakes|sweepstakes site|giveaway site|all sweepstakes)\b", re.I)


class LinkCollector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self._href = None
        self._text = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join("".join(self._text).split())))
            self._href = None
            self._text = []


def canonical_url(url):
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return ""
    query = urlencode([(key, value) for key, value in parse_qsl(parts.query) if key.lower() not in TRACKING_KEYS])
    path = re.sub(r"/+", "/", parts.path or "/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path.rstrip("/") or "/", query, ""))


def candidate_id(url):
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def classify(title, url, source=None):
    text = f"{title} {url}"
    # A promotion-directory link is a time-bounded promotion even when its
    # title contains words such as "rewards" or "daily." Persistent operators
    # must be confirmed during review rather than inferred from directory copy.
    if (source or {}).get("kind") == "promotion_directory":
        return "limited"
    if RECURRING_TERMS.search(text):
        return "recurring"
    if LIMITED_TERMS.search(text):
        return "limited"
    return "needs_classification"


def extract_candidates(html, source):
    parser = LinkCollector()
    parser.feed(html)
    found = []
    seen = set()
    for href, title in parser.links:
        resolved = canonical_url(urljoin(source["url"], href))
        evidence = f"{title} {resolved}"
        if not resolved or resolved in seen or len(title) < 5:
            continue
        if "/forum/" in urlsplit(resolved).path.lower():
            continue
        if not MATCH_TERMS.search(evidence) or EXCLUDE_TERMS.search(title):
            continue
        seen.add(resolved)
        found.append({
            "id": candidate_id(resolved),
            "title": title[:180],
            "candidate_type": classify(title, resolved, source),
            "discovered_url": resolved,
            "discovered_domain": urlsplit(resolved).netloc,
            "source_id": source["id"],
            "source_name": source["name"],
            "source_url": source["url"],
        })
    return found


def fetch(url, timeout=30):
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
    context = ssl.create_default_context()
    with urlopen(request, timeout=timeout, context=context) as response:
        content_type = response.headers.get_content_type()
        if content_type not in {"text/html", "application/xhtml+xml"}:
            raise ValueError(f"unsupported content type: {content_type}")
        return response.read(2_000_000).decode(response.headers.get_content_charset() or "utf-8", errors="replace")


def known_urls():
    known = set()
    if INVENTORY_FILE.exists():
        for site in json.loads(INVENTORY_FILE.read_text(encoding="utf-8")).get("sites", []):
            for key in ("link", "scrape_url", "outbound_url"):
                if site.get(key):
                    known.add(canonical_url(site[key]))
    if PROMOTIONS_FILE.exists():
        for promotion in json.loads(PROMOTIONS_FILE.read_text(encoding="utf-8")).get("promotions", []):
            for key in ("entry_url", "rules_url", "source_url"):
                if promotion.get(key):
                    known.add(canonical_url(promotion[key]))
    return known


def merge_queue(discovered, now):
    queue = json.loads(QUEUE_FILE.read_text(encoding="utf-8")) if QUEUE_FILE.exists() else {"schema_version": 1, "candidates": []}
    existing = {item["id"]: item for item in queue.get("candidates", [])}
    known = known_urls()
    new_count = 0
    added = []
    for item in discovered:
        if item["discovered_url"] in known:
            continue
        prior = existing.get(item["id"])
        if prior:
            prior.update({key: value for key, value in item.items() if key not in {"status", "review_notes"}})
            prior["last_seen"] = now
            prior["times_seen"] = int(prior.get("times_seen", 1)) + 1
        else:
            item.update({
                "status": "needs_review",
                "first_seen": now,
                "last_seen": now,
                "times_seen": 1,
                "review_notes": "",
                "verification": {
                    "official_rules_url": "",
                    "official_entry_url": "",
                    "sponsor": "",
                    "closes": "",
                    "free_entry_confirmed": False
                }
            })
            existing[item["id"]] = item
            added.append(dict(item))
            new_count += 1
    queue["updated_at"] = now
    queue["candidates"] = sorted(existing.values(), key=lambda item: (item.get("status") != "needs_review", item.get("first_seen", ""), item["title"].casefold()))
    QUEUE_FILE.write_text(json.dumps(queue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return queue, new_count, added


def write_report(queue, source_results, new_count):
    review = [item for item in queue["candidates"] if item.get("status") == "needs_review"]
    lines = [
        "# SafeTracker discovery review",
        "",
        f"Updated: {queue['updated_at']}",
        "",
        "This is a quarantine queue. Nothing listed here is published or scored automatically.",
        "",
        f"- New candidates this run: **{new_count}**",
        f"- Awaiting review: **{len(review)}**",
        f"- Sources attempted: **{len(source_results)}**",
        "",
        "## Source status",
        "",
        "| Source | Result | Candidates |",
        "|---|---:|---:|",
    ]
    for result in source_results:
        lines.append(f"| {result['name']} | {result['status']} | {result['count']} |")
    lines.extend([
        "",
        "## Review checklist",
        "",
        "Before approving a candidate, verify the official entry page, official rules, sponsor, eligibility, closing date or recurring schedule, free entry method, prize, entry limits, marketing consent, and enough evidence for all five ScamFactor inputs.",
        "",
        "## Candidates awaiting review",
        "",
        "| ID | Type guess | Candidate | Source | First seen |",
        "|---|---|---|---|---|",
    ])
    for item in review[:250]:
        title = item["title"].replace("|", "\\|")
        lines.append(f"| `{item['id']}` | {item['candidate_type']} | [{title}]({item['discovered_url']}) | {item['source_name']} | {item['first_seen'][:10]} |")
    if not review:
        lines.append("| — | — | No candidates awaiting review | — | — |")
    REPORT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-dir", type=Path, help="Read <source-id>.html fixtures instead of the network")
    parser.add_argument("--run-output", type=Path, help="Write a machine-readable record of this discovery run")
    args = parser.parse_args()
    started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    sources = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))["sources"]
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    discovered = []
    results = []
    for source in sources:
        try:
            if args.fixture_dir:
                html = (args.fixture_dir / f"{source['id']}.html").read_text(encoding="utf-8")
            else:
                html = fetch(source["url"])
            items = extract_candidates(html, source)
            discovered.extend(items)
            results.append({"name": source["name"], "status": "ok", "count": len(items)})
        except (OSError, HTTPError, URLError, ValueError) as exc:
            results.append({"name": source["name"], "status": f"error: {type(exc).__name__}", "count": 0})
    queue, new_count, added = merge_queue(discovered, now)
    write_report(queue, results, new_count)
    review_total = sum(1 for item in queue["candidates"] if item["status"] == "needs_review")
    if args.run_output:
        run_id = os.environ.get("GITHUB_RUN_ID") or f"local-{int(datetime.now(timezone.utc).timestamp())}"
        repository = os.environ.get("GITHUB_REPOSITORY", "ctiberius-bot/sweepstakes-tracker")
        server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
        payload = {
            "jobId": "sweeps-daily-discovery",
            "providerRunId": run_id,
            "trigger": os.environ.get("GITHUB_EVENT_NAME", "manual"),
            "status": "completed",
            "conclusion": "success",
            "startedAt": started_at,
            "completedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "candidatesSeen": len(discovered),
            "candidatesAdded": new_count,
            "quarantineTotal": review_total,
            "sourceResults": results,
            "addedItems": [{
                "id": item["id"],
                "title": item["title"],
                "domain": item["discovered_domain"],
                "source": item["source_name"],
                "url": item["discovered_url"],
            } for item in added],
            "runUrl": f"{server}/{repository}/actions/runs/{run_id}",
            "summary": f"Discovery completed: {len(discovered)} candidate links scanned; {new_count} added; {review_total} awaiting review.",
        }
        args.run_output.parent.mkdir(parents=True, exist_ok=True)
        args.run_output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Discovered {len(discovered)} links; {new_count} new; {sum(1 for item in queue['candidates'] if item['status'] == 'needs_review')} awaiting review.")
    for result in results:
        print(f"  {result['name']}: {result['status']} ({result['count']})")


if __name__ == "__main__":
    main()
