#!/usr/bin/env python3
"""
Simplified Sweepstakes Tracker Rebuilder
========================================
Loads sites from data.json, updates the last_updated timestamp,
and generates a clean index.html using the Jinja2 template.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

BASE = Path(__file__).parent
TEMPLATE_DIR = BASE / "templates"
OUTPUT_HTML = BASE / "index.html"
DATA_FILE = BASE / "data.json"


def main():
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Missing {DATA_FILE}")

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    sites = data.get("sites", [])
    if not sites:
        raise ValueError("No sites found in data.json")

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

    html = template.render(
        sites=sites,
        last_updated=last_updated_str
    )

    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"✓ Successfully rebuilt {OUTPUT_HTML}")
    print(f"  → {len(sites)} sites included")
    print(f"  → Last updated: {last_updated_str}")


if __name__ == "__main__":
    main()
