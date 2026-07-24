#!/usr/bin/env python3
"""Validate that every inventory record produced a complete v1.2 profile."""

import json
from pathlib import Path

BASE = Path(__file__).parent
data = json.loads((BASE / "data.json").read_text(encoding="utf-8"))
sites = data["sites"]
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
    "v1.2",
)

expected = {f"{site['slug']}.html" for site in sites}
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

print(f"Validated {len(sites)} complete v1.2 detail pages.")
