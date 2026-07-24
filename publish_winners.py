#!/usr/bin/env python3
"""Send unsent winner reports as one Buttondown daily edition."""

import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).parent
WINNERS_FILE = BASE / "data" / "winners.json"
STATE_FILE = BASE / "data" / "winner_state.json"


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    token = os.environ.get("BUTTONDOWN_API_KEY")
    if not token:
        raise SystemExit("BUTTONDOWN_API_KEY is required when new reports exist.")
    winners = json.loads(WINNERS_FILE.read_text(encoding="utf-8")).get("winners", [])
    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    sent = set(state.get("sent", []))
    pending = [winner for winner in winners if winner["id"] not in sent]
    if not pending:
        print("No new winner reports; skipping email.")
        return
    today = datetime.now(timezone.utc).strftime("%B %d, %Y").replace(" 0", " ")
    lines = [
        "# Daily Sweepstakes Winners",
        "",
        f"Here are the new winner reports collected on **{today}**.",
        "",
    ]
    for winner in pending:
        byline = f" — reported by {winner['author']}" if winner.get("author") else ""
        lines.extend([
            f"## [{winner['title']}]({winner['url']})",
            f"{winner['source_name']}{byline} · {winner['published_display']}",
            "",
        ])
    lines.extend([
        "Never pay a fee or provide banking information to claim a legitimate prize.",
        "",
        "[Browse all winner reports](https://sweeps.safetrackerhub.com/winners.html) · [View the safety rankings](https://sweeps.safetrackerhub.com/)",
        "",
        "— SafeTrackerHub Sweepstakes",
    ])
    payload = json.dumps({
        "subject": f"Daily Sweepstakes Winners — {today}",
        "body": "\n".join(lines),
        "status": "about_to_send",
        "slug": datetime.now(timezone.utc).strftime("daily-winners-%Y-%m-%d"),
        "description": "New winner reports gathered from monitored sweepstakes sources.",
    }).encode()
    request = urllib.request.Request(
        "https://api.buttondown.com/v1/emails",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
            "User-Agent": "SafeTrackerHub-WinnerMonitor/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        response.read()
    state["sent"] = list(dict.fromkeys([winner["id"] for winner in pending] + list(sent)))[:2000]
    write_json(STATE_FILE, state)
    print(f"Queued {len(pending)} winner reports for Buttondown.")


if __name__ == "__main__":
    main()
