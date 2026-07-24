#!/usr/bin/env python3
"""Send unsent winner reports as one Buttondown daily edition."""

import os
import urllib.request
from datetime import datetime, timezone
from winner_db import connect, mark_sent, unsent_reports


def main():
    token = os.environ.get("BUTTONDOWN_API_KEY")
    if not token:
        raise SystemExit("BUTTONDOWN_API_KEY is required when new reports exist.")
    database = connect()
    pending = unsent_reports(database)
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
            f"## [{winner['raw_title']}]({winner['source_url']})",
            f"{winner['source_name']}{byline} · {winner['reported_at'][:10]}",
            "",
        ])
    lines.extend([
        "Never pay a fee or provide banking information to claim a legitimate prize.",
        "",
        "[Browse all winner reports](https://sweeps.safetrackerhub.com/winners.html) · [View the safety rankings](https://sweeps.safetrackerhub.com/)",
        "",
        "— SafeTracker: Sweepstakes",
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
            "User-Agent": "SafeTracker-WinnerMonitor/1.1",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        response.read()
    mark_sent(database, [winner["id"] for winner in pending])
    database.close()
    print(f"Queued {len(pending)} winner reports for Buttondown.")


if __name__ == "__main__":
    main()
