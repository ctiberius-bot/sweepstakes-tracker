#!/usr/bin/env python3
"""
Simplified Sweepstakes Tracker Rebuilder
========================================
Loads sites from data.json and generates a clean index.html
using the Jinja2 template. No internet required.
"""

import json
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

BASE = Path(__file__).parent
TEMPLATE_DIR = BASE / "templates"
OUTPUT_HTML = BASE / "index.html"
DATA_FILE = BASE / "data.json"


def score_class(score: float) -> str:
    """Return CSS class based on ScamFactor score."""
    try:
        s = float(score)
    except (TypeError, ValueError):
        return "score-5"
    if s <= 2:
        return "score-1"
    elif s <= 4:
        return "score-3"
    elif s <= 6:
        return "score-5"
    elif s <= 8:
        return "score-7"
    else:
        return "score-9"


def main():
    # Load data
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Missing {DATA_FILE}")

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    sites = data.get("sites", [])
    if not sites:
        raise ValueError("No sites found in data.json")

    # Prefer the date from data.json if present, otherwise use today
    last_updated = data.get("last_updated")
    if last_updated:
        try:
            # Handle ISO format
            dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
            last_updated_str = dt.strftime("%B %d, %Y")
        except Exception:
            last_updated_str = datetime.now().strftime("%B %d, %Y")
    else:
        last_updated_str = datetime.now().strftime("%B %d, %Y")

    # Setup Jinja
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"])
    )
    env.globals["score_class"] = score_class

    template = env.get_template("tracker.html.j2")

    html = template.render(
        sites=sites,
        last_updated=last_updated_str,
        themes=[]  # template supports themes but we don't have them yet
    )

    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"✓ Successfully rebuilt {OUTPUT_HTML}")
    print(f"  → {len(sites)} sites included")
    print(f"  → Last updated: {last_updated_str}")


if __name__ == "__main__":
    main()
