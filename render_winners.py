#!/usr/bin/env python3
"""Rebuild only the winner archive, leaving unrelated generated pages untouched."""

import json
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

BASE = Path(__file__).parent


def main():
    environment = Environment(
        loader=FileSystemLoader(BASE / "templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    payload = json.loads((BASE / "data" / "winners.json").read_text(encoding="utf-8"))
    rendered = environment.get_template("winners.html.j2").render(
        winners=payload.get("winners", []),
        last_updated=datetime.now().strftime("%B %d, %Y").replace(" 0", " "),
    )
    cleaned = "\n".join(line.rstrip() for line in rendered.splitlines()) + "\n"
    (BASE / "winners.html").write_text(cleaned, encoding="utf-8")
    print(f"Rebuilt winner archive with {len(payload.get('winners', []))} reports.")


if __name__ == "__main__":
    main()
