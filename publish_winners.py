#!/usr/bin/env python3
"""Render or send one branded edition containing every unsent winner report."""

import argparse
import html
import json
import os
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from newsletter_archive import archive_edition
from winner_db import connect, mark_sent, unsent_reports

BASE = Path(__file__).parent
KIT_BROADCASTS_URL = "https://api.kit.com/v4/broadcasts"
DEFAULT_KIT_SEND_DELAY_MINUTES = 15

TIP_ROTATION = [
    "Never pay a fee, buy gift cards, send cryptocurrency, or wire money to claim a legitimate prize.",
    "Verify a winner notice using the sponsor's official website and rules, not only the link or phone number in the message.",
    "Use a dedicated sweepstakes email address so prize notices and promotional mail stay separate from sensitive accounts.",
    "Save the official rules and confirmation page for prizes you care about; entry pages can disappear after a promotion closes.",
    "Check the response deadline in a potential winner notice, then confirm the sender independently before sharing personal information.",
    "A familiar company name does not authenticate a call, text, or email; scammers routinely impersonate legitimate brands.",
]


def escape(value):
    return html.escape(str(value or ""))


def report_label(report):
    if report.get("source_type") == "operator_announcement":
        return "Official operator announcement"
    return "Community-reported win"


def display_winner(report):
    return report.get("winner_name") or report.get("author") or "Winner not named in public report"


def display_prize(report):
    return report.get("prize") or "Prize details not stated in the public report"


def display_contest(report):
    return report.get("promotion_name") or report.get("raw_title") or "Contest not identified"


def edition_extras(day):
    editorial = json.loads((BASE / "data" / "editorial.json").read_text(encoding="utf-8"))
    available = sorted(
        [
            article
            for article in editorial.get("articles", [])
            if not article.get("newsletter_exclude", False)
        ],
        key=lambda article: (article.get("published", "2026-07-26"), article["slug"]),
    )
    if not available:
        raise RuntimeError("No newsletter guide spotlights are available in data/editorial.json.")

    index = day.toordinal()
    guide = available[(index // 7) % len(available)]
    tips = [
        TIP_ROTATION[index % len(TIP_ROTATION)],
        TIP_ROTATION[(index + 3) % len(TIP_ROTATION)],
    ]
    return guide, tips


def build_email(reports):
    edition_day = datetime.now(timezone.utc).date()
    today = edition_day.strftime("%B %d, %Y").replace(" 0", " ")
    guide, tips = edition_extras(edition_day)
    guide_url = f"https://sweeps.safetrackerhub.com/guides/{guide['slug']}.html"
    official = [report for report in reports if report.get("source_type") == "operator_announcement"]
    community = [report for report in reports if report.get("source_type") != "operator_announcement"]
    subject = f"Winner Signal: {len(reports)} new sweepstakes winner report{'s' if len(reports) != 1 else ''} — {today}"
    preheader = f"New source-linked winner reports from {len(set(r['source_id'] for r in reports))} monitored sources."

    sections = []
    for heading, items in (("Published by sweepstakes operators", official), ("Reported by sweepstakes communities", community)):
        if not items:
            continue
        cards = []
        for report in items:
            winner = escape(display_winner(report))
            prize = escape(display_prize(report))
            contest = escape(display_contest(report))
            cards.append(f"""
              <tr><td style="padding:0 0 12px">
                <table role="presentation" width="100%" style="border:1px solid #d9e4e2;border-radius:10px;background:#ffffff">
                  <tr><td style="padding:16px 18px">
                    <div style="margin-bottom:7px;color:#08756b;font-size:11px;font-weight:800;letter-spacing:.06em;text-transform:uppercase">{escape(report_label(report))}</div>
                    <table role="presentation" width="100%" style="border-collapse:collapse;color:#102a2a;font-size:14px;line-height:1.5">
                      <tr><td width="92" valign="top" style="padding:3px 10px 3px 0;color:#475569;font-weight:800">WHO WON</td><td style="padding:3px 0;font-weight:700">{winner}</td></tr>
                      <tr><td width="92" valign="top" style="padding:3px 10px 3px 0;color:#475569;font-weight:800">WHAT</td><td style="padding:3px 0">{prize}</td></tr>
                      <tr><td width="92" valign="top" style="padding:3px 10px 3px 0;color:#475569;font-weight:800">CONTEST</td><td style="padding:3px 0">{contest}</td></tr>
                    </table>
                    <table role="presentation" cellspacing="0" cellpadding="0" style="margin-top:13px"><tr><td bgcolor="#075e54" style="border-radius:6px;background:#075e54">
                      <a href="{escape(report['source_url'])}" style="display:inline-block;padding:10px 15px;color:#ffffff !important;font-size:13px;font-weight:800;text-decoration:none"><span style="color:#ffffff !important">OPEN ORIGINAL WINNER REPORT</span></a>
                    </td></tr></table>
                    <p style="margin:10px 0 0;color:#64748b;font-size:12px">{escape(report['source_name'])} · {escape(report['reported_at'][:10])}</p>
                  </td></tr>
                </table>
              </td></tr>""")
        sections.append(f"""
          <tr><td style="padding:22px 26px 9px">
            <h2 style="margin:0;color:#102a2a;font-family:Georgia,serif;font-size:20px">{heading}</h2>
          </td></tr>
          <tr><td style="padding:0 26px"><table role="presentation" width="100%">{''.join(cards)}</table></td></tr>""")

    body_html = f"""<!doctype html>
<html><body style="margin:0;background:#eef4f3;font-family:Arial,sans-serif;color:#102a2a">
<div style="display:none;max-height:0;overflow:hidden">{escape(preheader)}</div>
<table role="presentation" width="100%" style="background:#eef4f3"><tr><td align="center" style="padding:24px 10px">
<table role="presentation" width="100%" style="max-width:640px;background:#f8fbfa;border-radius:14px;overflow:hidden">
  <tr><td style="padding:22px 26px;background:#073f3b;border-bottom:5px solid #f0a23b">
    <div style="color:#9ee2d8;font-size:12px;font-weight:800;letter-spacing:.08em;text-transform:uppercase">SafeTracker: Sweepstakes</div>
    <h1 style="margin:6px 0 5px;color:#fff;font-family:Georgia,serif;font-size:29px;line-height:1.15">Winner Signal</h1>
    <p style="margin:0;color:#cce9e5;font-size:14px">Source-linked winner reports. No empty editions. No manufactured claims.</p>
  </td></tr>
  <tr><td style="padding:20px 26px 0;color:#334155;font-size:14px;line-height:1.55">
    We found <strong>{len(reports)} new report{'s' if len(reports) != 1 else ''}</strong> across <strong>{len(set(r['source_id'] for r in reports))} monitored source{'s' if len(set(r['source_id'] for r in reports)) != 1 else ''}</strong>.
  </td></tr>
  {''.join(sections)}
  <tr><td style="padding:20px 26px;background:#edf8f6;border-top:1px solid #cfe7e3">
    <div style="margin-bottom:9px;color:#08756b;font-size:11px;font-weight:800;letter-spacing:.06em;text-transform:uppercase">Two useful reminders</div>
    <ul style="margin:0;padding-left:19px;color:#334155;font-size:14px;line-height:1.55">
      <li style="margin-bottom:7px">{escape(tips[0])}</li>
      <li>{escape(tips[1])}</li>
    </ul>
  </td></tr>
  <tr><td style="padding:20px 26px;background:#ffffff;border-top:1px solid #d9e4e2">
    <div style="margin-bottom:7px;color:#b66512;font-size:11px;font-weight:800;letter-spacing:.06em;text-transform:uppercase">From the SafeTracker guide library</div>
    <a href="{escape(guide_url)}" style="color:#102a2a;font-family:Georgia,serif;font-size:20px;font-weight:800;line-height:1.25;text-decoration:none">{escape(guide['title'])}</a>
    <p style="margin:8px 0 12px;color:#475569;font-size:14px;line-height:1.55">{escape(guide['meta_description'])}</p>
    <a href="{escape(guide_url)}" style="color:#08756b;font-size:14px;font-weight:800;text-decoration:none">Read the guide &#8594;</a>
  </td></tr>
  <tr><td style="padding:18px 26px;background:#fff4df;border-top:1px solid #f4d7a7;color:#5f420d;font-size:13px;line-height:1.5">
    <strong>A real prize never requires gift cards, wire transfers, crypto, or a “processing fee.”</strong>
    A published winner report does not prove that a message claiming you won is genuine.
  </td></tr>
  <tr><td align="center" style="padding:22px 26px">
    <table role="presentation" cellspacing="0" cellpadding="0" align="center"><tr><td bgcolor="#075e54" style="border-radius:7px;background:#075e54">
      <a href="https://sweeps.safetrackerhub.com/winners.html" style="display:inline-block;padding:12px 19px;color:#ffffff !important;font-size:14px;font-weight:800;text-decoration:none"><span style="color:#ffffff !important">SEARCH THE WINNER ARCHIVE</span></a>
    </td></tr></table>
    <p style="margin:15px 0 0;color:#64748b;font-size:11px;line-height:1.5"><strong>Winner Signal by SafeTracker: Sweepstakes</strong><br>SafeTracker links each item to the monitored source and labels operator announcements separately from community reports. You receive Winner Signal only when new reports are found; your email provider places unsubscribe and mailing-address controls below this edition.</p>
  </td></tr>
</table></td></tr></table></body></html>"""

    lines = ["# Winner Signal", "", "By SafeTracker: Sweepstakes", "", preheader, ""]
    for heading, items in (("Published by sweepstakes operators", official), ("Reported by sweepstakes communities", community)):
        if not items:
            continue
        lines.extend([f"## {heading}", ""])
        for report in items:
            lines.extend([
                f"- **Who won:** {display_winner(report)}",
                f"  **What they won:** {display_prize(report)}",
                f"  **Contest:** {display_contest(report)}",
                f"  **Report:** [Open original winner report]({report['source_url']})",
            ])
        lines.append("")
    lines.extend([
        "## Two useful reminders",
        "",
        f"- {tips[0]}",
        f"- {tips[1]}",
        "",
        "## From the SafeTracker guide library",
        "",
        f"[{guide['title']}]({guide_url})",
        "",
        guide["meta_description"],
        "",
    ])
    lines.extend([
        "**Safety reminder:** Never pay a fee or provide banking information to claim a legitimate prize.",
        "",
        "[Search the winner archive](https://sweeps.safetrackerhub.com/winners.html)",
        "",
        "Winner Signal is a free publication from SafeTracker: Sweepstakes. Your email provider includes unsubscribe and mailing-address controls with this edition.",
    ])
    return subject, "\n".join(lines), body_html


def build_kit_payload(subject, body_html, *, draft=False, send_at=None):
    """Build a private Kit broadcast payload for the dedicated account audience."""
    if draft:
        send_at = None
    elif send_at is None:
        raise ValueError("send_at is required for a scheduled Kit broadcast.")
    return {
        "subject": subject,
        "content": body_html,
        "description": "Source-linked winner reports from SafeTracker: Sweepstakes.",
        "preview_text": "New source-linked sweepstakes winner reports.",
        "public": False,
        "send_at": send_at,
    }


def create_kit_broadcast(token, payload):
    request = urllib.request.Request(
        KIT_BROADCASTS_URL,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={
            "X-Kit-Api-Key": token,
            "Content-Type": "application/json",
            "User-Agent": "SafeTracker-WinnerMonitor/2.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Kit API returned HTTP {error.code}: {detail}") from error
    broadcast = result.get("broadcast", result)
    if not broadcast.get("id"):
        raise RuntimeError("Kit API created a broadcast without returning an id.")
    return broadcast


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", type=Path, help="Write a local HTML preview and do not contact a provider.")
    parser.add_argument("--draft", action="store_true", help="Create a provider draft without sending it.")
    args = parser.parse_args()

    with connect() as database:
        pending = unsent_reports(database)
        if not pending:
            print("No unsent winner reports.")
            return
        subject, body, body_html = build_email(pending)

        if args.preview:
            args.preview.parent.mkdir(parents=True, exist_ok=True)
            args.preview.write_text(body_html, encoding="utf-8")
            print(json.dumps({"preview": str(args.preview), "pending_count": len(pending), "subject": subject}))
            return

        provider = "kit"
        token = os.environ.get("KIT_API_KEY")
        if not token:
            raise SystemExit("KIT_API_KEY is required.")
        delay_minutes = int(os.environ.get("KIT_SEND_DELAY_MINUTES", DEFAULT_KIT_SEND_DELAY_MINUTES))
        if delay_minutes < 1:
            raise SystemExit("KIT_SEND_DELAY_MINUTES must be at least 1.")
        send_at = None if args.draft else (
            datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
        ).isoformat()
        broadcast = create_kit_broadcast(
            token,
            build_kit_payload(subject, body_html, draft=args.draft, send_at=send_at),
        )
        provider_id = broadcast["id"]
        provider_status = "draft" if args.draft else "scheduled"
        accepted_at = None
        if not args.draft:
            accepted_at = broadcast.get("send_at")
            if not accepted_at:
                raise RuntimeError(
                    f"Kit created broadcast {provider_id} without a scheduled send time; "
                    "reports remain pending."
                )

        archive_path = None
        if not args.draft:
            # Once the provider has accepted a live edition, mark the reports first.
            # If archive rendering subsequently fails, the job alerts without risking a
            # duplicate newsletter on the next daily run.
            mark_sent(database, [winner["id"] for winner in pending])
            archive_path = archive_edition(
                pending,
                subject,
                accepted_at,
                provider_id,
                provider=provider,
            )
        print(json.dumps({
            "provider": provider,
            "provider_id": provider_id,
            "status": provider_status,
            "accepted_at": accepted_at,
            "archive_path": str(archive_path) if archive_path else None,
            "report_count": len(pending),
        }))


if __name__ == "__main__":
    main()
