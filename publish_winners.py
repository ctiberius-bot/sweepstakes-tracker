#!/usr/bin/env python3
"""Render or send one branded edition containing every unsent winner report."""

import argparse
import html
import json
import os
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from winner_db import connect, mark_sent, unsent_reports

BASE = Path(__file__).parent

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
    subject = f"{len(reports)} new sweepstakes winner report{'s' if len(reports) != 1 else ''} — {today}"
    preheader = f"New source-linked winner reports from {len(set(r['source_id'] for r in reports))} monitored sources."

    sections = []
    for heading, items in (("Published by sweepstakes operators", official), ("Reported by sweepstakes communities", community)):
        if not items:
            continue
        cards = []
        for report in items:
            prize = escape(report.get("prize"))
            winner = escape(report.get("winner_name") or report.get("raw_title"))
            detail = f'<p style="margin:6px 0 0;color:#334155;font-size:14px;line-height:1.45">{prize}</p>' if prize else ""
            author = f" · {escape(report.get('author'))}" if report.get("author") else ""
            cards.append(f"""
              <tr><td style="padding:0 0 12px">
                <table role="presentation" width="100%" style="border:1px solid #d9e4e2;border-radius:10px;background:#ffffff">
                  <tr><td style="padding:16px 18px">
                    <div style="margin-bottom:7px;color:#08756b;font-size:11px;font-weight:800;letter-spacing:.06em;text-transform:uppercase">{escape(report_label(report))}</div>
                    <a href="{escape(report['source_url'])}" style="color:#102a2a;font-size:17px;font-weight:800;line-height:1.3;text-decoration:none">{winner}</a>
                    {detail}
                    <p style="margin:8px 0 0;color:#64748b;font-size:12px">{escape(report['source_name'])}{author} · {escape(report['reported_at'][:10])}</p>
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
    <a href="https://sweeps.safetrackerhub.com/winners.html" style="display:inline-block;padding:11px 18px;border-radius:7px;background:#08756b;color:#fff;font-size:14px;font-weight:800;text-decoration:none">Search the winner archive</a>
    <p style="margin:15px 0 0;color:#64748b;font-size:11px;line-height:1.5">SafeTracker links each item to the monitored source and labels operator announcements separately from community reports.</p>
  </td></tr>
</table></td></tr></table></body></html>"""

    lines = ["# Winner Signal", "", preheader, ""]
    for heading, items in (("Published by sweepstakes operators", official), ("Reported by sweepstakes communities", community)):
        if not items:
            continue
        lines.extend([f"## {heading}", ""])
        for report in items:
            title = report.get("winner_name") or report["raw_title"]
            prize = f" — {report['prize']}" if report.get("prize") else ""
            lines.append(f"- [{title}{prize}]({report['source_url']}) · {report['source_name']} · {report['reported_at'][:10]}")
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
    ])
    return subject, "\n".join(lines), body_html


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", type=Path, help="Write a local HTML preview and do not contact Buttondown.")
    parser.add_argument("--draft", action="store_true", help="Create a Buttondown draft without sending it.")
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

        token = os.environ.get("BUTTONDOWN_API_KEY")
        if not token:
            raise SystemExit("BUTTONDOWN_API_KEY is required.")
        payload = json.dumps({
            "subject": subject,
            "body": "<!-- buttondown-editor-mode: fancy -->" + body_html,
            "status": "draft" if args.draft else "about_to_send",
            "slug": datetime.now(timezone.utc).strftime("winner-signal-%Y-%m-%d"),
            "description": "Source-linked winner reports from SafeTracker: Sweepstakes.",
        }).encode()
        request = urllib.request.Request(
            "https://api.buttondown.com/v1/emails",
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Token {token}",
                "Content-Type": "application/json",
                "User-Agent": "SafeTracker-WinnerMonitor/1.2",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Buttondown API returned HTTP {error.code}: {detail}") from error
        if not args.draft:
            accepted_statuses = {"about_to_send", "in_flight", "sent"}
            if result.get("status") not in accepted_statuses:
                raise RuntimeError(
                    f"Buttondown created email {result.get('id', 'without an id')} "
                    f"with unexpected status {result.get('status')!r}; reports remain pending."
                )
            mark_sent(database, [winner["id"] for winner in pending])
        print(json.dumps({
            "buttondown_id": result.get("id"),
            "status": "draft" if args.draft else "queued",
            "report_count": len(pending),
        }))


if __name__ == "__main__":
    main()
