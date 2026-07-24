#!/usr/bin/env python3
"""Recompute ScamFactor scores and ranks from the five published criteria."""

import argparse
import json
import ssl
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DATA_FILE = Path(__file__).parent / "data.json"
WEIGHTS = {
    "transparency": 0.30,
    "fulfillment": 0.25,
    "entry_model": 0.20,
    "win_realism": 0.15,
    "marketing": 0.10,
}


def check_site(url):
    if not url or url == "#":
        return "not_applicable"
    request = Request(url, headers={"User-Agent": "SafeTracker weekly site check/1.1"})
    try:
        with urlopen(request, timeout=20, context=ssl.create_default_context()) as response:
            return "reachable" if response.status < 400 else f"http_{response.status}"
    except HTTPError as error:
        if error.code in {401, 403, 429}:
            return "protected"
        return f"http_{error.code}"
    except (URLError, TimeoutError, ssl.SSLError):
        return "unreachable"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-live", action="store_true")
    args = parser.parse_args()
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    scored_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    for site in data["sites"]:
        inputs = site.setdefault(
            "score_inputs",
            {criterion: float(site["score"]) for criterion in WEIGHTS},
        )
        if set(inputs) != set(WEIGHTS):
            raise ValueError(f"{site['name']} must define all five score inputs")
        if any(not 1 <= float(inputs[key]) <= 10 for key in WEIGHTS):
            raise ValueError(f"{site['name']} has a score input outside 1–10")
        status = check_site(site.get("link")) if args.check_live else site.get("weekly_check_status", "not_checked")
        adjustment = 0.5 if status == "unreachable" or status.startswith("http_5") else 0
        weighted = sum(float(inputs[key]) * weight for key, weight in WEIGHTS.items())
        site["score"] = round(min(10, max(1, weighted + adjustment)) * 2) / 2
        site["weekly_check_status"] = status
        site["last_scored"] = scored_at

    data["sites"].sort(key=lambda site: (float(site["score"]), site["name"].casefold()))
    for rank, site in enumerate(data["sites"], start=1):
        site["rank"] = rank
    data["last_rescored"] = scored_at
    DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Rescored and reranked {len(data['sites'])} sites")


if __name__ == "__main__":
    main()
