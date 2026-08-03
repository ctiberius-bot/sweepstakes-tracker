#!/usr/bin/env python3
"""Flag existing inventory records for human review without removing them."""

import hashlib
import json
import ssl
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

BASE = Path(__file__).parent
INVENTORY_FILE = BASE / "data.json"
QUEUE_FILE = BASE / "data" / "removal_candidates.json"
USER_AGENT = "SafeTrackerHub-InventoryAudit/1.0 (+https://sweeps.safetrackerhub.com/contact)"


def record_id(slug, url):
    return hashlib.sha256(f"{slug}|{url}".encode("utf-8")).hexdigest()[:16]


def is_public_http_url(url):
    """Return whether an inventory value is a usable public web URL."""
    if not isinstance(url, str):
        return False
    parsed = urlsplit(url.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def check_url(url, timeout=20):
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
    context = ssl.create_default_context()
    try:
        with urlopen(request, timeout=timeout, context=context) as response:
            status = int(response.status)
            final_url = response.geturl()
            response.read(1024)
            return {"result": "reachable" if status < 400 else "http_error", "http_status": status, "final_url": final_url, "error": ""}
    except HTTPError as exc:
        return {
            "result": "gone" if exc.code in {404, 410} else "http_error",
            "http_status": exc.code,
            "final_url": exc.geturl() or url,
            "error": type(exc).__name__,
        }
    except (URLError, TimeoutError, OSError) as exc:
        return {"result": "unreachable", "http_status": 0, "final_url": url, "error": type(exc).__name__}


def main():
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    inventory = json.loads(INVENTORY_FILE.read_text(encoding="utf-8"))
    queue = json.loads(QUEUE_FILE.read_text(encoding="utf-8")) if QUEUE_FILE.exists() else {"schema_version": 1, "candidates": []}
    existing = {item["id"]: item for item in queue.get("candidates", [])}
    active_ids = set()
    checked = 0
    skipped = 0

    for site in inventory.get("sites", []):
        url = site.get("link") or site.get("outbound_url") or site.get("scrape_url")
        if not is_public_http_url(url):
            skipped += 1
            continue
        url = url.strip()
        checked += 1
        item_id = record_id(site.get("slug", ""), url)
        result = check_url(url)
        previous = existing.get(item_id, {})
        failures = int(previous.get("consecutive_failures", 0)) + 1 if result["result"] != "reachable" else 0
        should_review = result["result"] == "gone" or failures >= 2
        if should_review:
            active_ids.add(item_id)
            existing[item_id] = {
                "id": item_id,
                "name": site.get("name", site.get("slug", "Inventory record")),
                "slug": site.get("slug", ""),
                "url": url,
                "reason": (
                    f"Official page returned HTTP {result['http_status']}."
                    if result["http_status"]
                    else f"Official page was unreachable on {failures} consecutive weekly checks."
                ),
                "last_result": result["result"],
                "http_status": result["http_status"],
                "final_url": result["final_url"],
                "error": result["error"],
                "consecutive_failures": failures,
                "first_flagged": previous.get("first_flagged", now),
                "last_checked": now,
                "status": "needs_review",
            }
        elif item_id in existing:
            existing.pop(item_id)

    queue["updated_at"] = now
    queue["candidates"] = sorted(
        (item for key, item in existing.items() if key in active_ids),
        key=lambda item: (-int(item.get("consecutive_failures", 0)), item.get("name", "").casefold()),
    )
    QUEUE_FILE.write_text(json.dumps(queue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"Checked {checked} inventory URLs; skipped {skipped} records without a public HTTP(S) URL; "
        f"{len(queue['candidates'])} require removal review."
    )


if __name__ == "__main__":
    main()
