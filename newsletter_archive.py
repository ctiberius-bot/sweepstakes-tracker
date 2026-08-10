#!/usr/bin/env python3
"""Persist and render the on-site Winner Signal edition archive."""

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

BASE = Path(__file__).parent
DATA_FILE = Path("data/newsletter_editions.json")
ARCHIVE_DIR = Path("newsletter")


def parse_timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def display_date(value):
    return parse_timestamp(value).strftime("%B %d, %Y").replace(" 0", " ")


def edition_slug(value):
    return f"winner-signal-{parse_timestamp(value).date().isoformat()}"


def report_snapshot(report):
    return {
        "id": report["id"],
        "winner_name": report.get("winner_name") or report.get("author") or "Winner not named in public report",
        "prize": report.get("prize") or "Prize details not stated in the public report",
        "promotion_name": report.get("promotion_name") or report.get("raw_title") or "Contest not identified",
        "source_name": report["source_name"],
        "source_type": report.get("source_type", "community_report"),
        "source_url": report.get("source_url") or report["url"],
        "reported_at": report.get("reported_at") or report["published_at"],
    }


def update_sitemap(editions, base=BASE):
    """Add the archive and edition URLs without rebuilding unrelated site pages."""
    sitemap_path = base / "sitemap.xml"
    if not sitemap_path.exists():
        return
    sitemap = sitemap_path.read_text(encoding="utf-8")
    urls = [("https://sweeps.safetrackerhub.com/newsletter/", None)] + [
        (
            f"https://sweeps.safetrackerhub.com/newsletter/{edition['slug']}.html",
            parse_timestamp(edition["scheduled_at"]).date().isoformat(),
        )
        for edition in editions
    ]
    additions = []
    for url, lastmod in urls:
        if f"<loc>{url}</loc>" in sitemap:
            continue
        lastmod_markup = f"<lastmod>{lastmod}</lastmod>" if lastmod else ""
        additions.append(f"  <url><loc>{url}</loc>{lastmod_markup}</url>")
    if additions:
        sitemap = sitemap.replace("</urlset>", "\n".join(additions) + "\n</urlset>")
        sitemap_path.write_text(sitemap, encoding="utf-8")


def render_archive(base=BASE):
    data_path = base / DATA_FILE
    payload = json.loads(data_path.read_text(encoding="utf-8")) if data_path.exists() else {"schema_version": 1, "editions": []}
    editions = sorted(payload.get("editions", []), key=lambda item: item["scheduled_at"], reverse=True)
    environment = Environment(
        loader=FileSystemLoader(base / "templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    archive_dir = base / ARCHIVE_DIR
    archive_dir.mkdir(parents=True, exist_ok=True)

    for edition in editions:
        rendered = environment.get_template("newsletter-edition.html.j2").render(edition=edition)
        (archive_dir / f"{edition['slug']}.html").write_text(
            "\n".join(line.rstrip() for line in rendered.splitlines()) + "\n",
            encoding="utf-8",
        )

    rendered = environment.get_template("newsletter-archive.html.j2").render(editions=editions)
    (archive_dir / "index.html").write_text(
        "\n".join(line.rstrip() for line in rendered.splitlines()) + "\n",
        encoding="utf-8",
    )
    for template_name, filename in (
        ("newsletter-thanks.html.j2", "thanks.html"),
        ("newsletter-confirmed.html.j2", "confirmed.html"),
    ):
        rendered = environment.get_template(template_name).render()
        (archive_dir / filename).write_text(
            "\n".join(line.rstrip() for line in rendered.splitlines()) + "\n",
            encoding="utf-8",
        )
    update_sitemap(editions, base)
    return editions


def archive_edition(reports, subject, scheduled_at, provider_id, *, provider="unknown", base=BASE):
    data_path = base / DATA_FILE
    payload = json.loads(data_path.read_text(encoding="utf-8")) if data_path.exists() else {"schema_version": 1, "editions": []}
    slug = edition_slug(scheduled_at)
    edition = {
        "slug": slug,
        "subject": subject,
        "scheduled_at": scheduled_at,
        "display_date": display_date(scheduled_at),
        "provider_id": str(provider_id),
        "delivery_provider": provider,
        "report_count": len(reports),
        "source_count": len({report["source_id"] for report in reports}),
        "reports": [report_snapshot(report) for report in reports],
    }
    editions = [item for item in payload.get("editions", []) if item.get("slug") != slug]
    editions.append(edition)
    payload["editions"] = sorted(editions, key=lambda item: item["scheduled_at"], reverse=True)
    payload["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    render_archive(base)
    return ARCHIVE_DIR / f"{slug}.html"


def backfill_buttondown_editions(base=BASE, start_date="2026-08-01"):
    """Backfill editions already verified as delivered by Buttondown."""
    winners_path = base / "data" / "winners.json"
    winners = json.loads(winners_path.read_text(encoding="utf-8")).get("winners", [])
    grouped = defaultdict(list)
    for report in winners:
        sent_at = report.get("sent_at")
        if sent_at and sent_at[:10] >= start_date:
            grouped[sent_at].append(report)
    for sent_at, reports in sorted(grouped.items()):
        date_label = display_date(sent_at)
        count = len(reports)
        subject = (
            f"{count} new sweepstakes winner report{'s' if count != 1 else ''} "
            f"— {date_label}"
        )
        archive_edition(
            reports,
            subject,
            sent_at,
            f"verified-buttondown-backfill-{sent_at[:10]}",
            provider="buttondown",
            base=base,
        )
    return len(grouped)


if __name__ == "__main__":
    backfilled = backfill_buttondown_editions()
    rendered = render_archive()
    print(f"Rebuilt Winner Signal archive with {len(rendered)} editions ({backfilled} verified Buttondown backfills).")
