import tempfile
import unittest
import json
import sqlite3
from datetime import date
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import gather_winners
import newsletter_archive
import publish_winners
import winner_db


class WinnerCollectorTests(unittest.TestCase):
    def test_operator_page_parser_extracts_structured_winner(self):
        source = {
            "id": "example",
            "name": "Example Sweeps",
            "operator": "Example Sweeps",
            "type": "html_regex",
            "url": "https://example.com/winners",
            "max_age_days": 5000,
            "pattern": (
                r"(?P<winner>[A-Za-z][A-Za-z .'-]{1,60}?)"
                r"(?:\s+of\s+(?P<location>[A-Za-z .'-]+,\s*[A-Z]{2}))?"
                r"\s+won\s+(?P<prize>\$[\d,]+)\s+on\s+"
                r"(?P<date>[A-Z][a-z]+\s+\d{1,2}\s+\d{4})"
            ),
        }
        with patch.object(
            gather_winners,
            "fetch_html",
            return_value="<p>Jamie R. of Greenville, SC won $500 on July 29 2026</p>",
        ):
            reports = gather_winners.fetch_html_regex(source)
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["winner_name"], "Jamie R.")
        self.assertEqual(reports[0]["prize"], "$500")
        self.assertEqual(reports[0]["source_type"], "operator_announcement")

    def test_preview_never_requires_delivery_credentials(self):
        reports = [{
            "id": "one",
            "raw_title": "Jamie R. won $500",
            "winner_name": "Jamie R.",
            "prize": "$500",
            "source_id": "example",
            "source_name": "Example Sweeps",
            "source_type": "operator_announcement",
            "source_url": "https://example.com/winners",
            "reported_at": datetime.now(timezone.utc).isoformat(),
            "author": "",
        }]
        subject, _, html = publish_winners.build_email(reports)
        self.assertIn("1 new sweepstakes winner report", subject)
        self.assertIn("Winner Signal", html)
        self.assertTrue(subject.startswith("Winner Signal:"))
        self.assertIn("Winner Signal by SafeTracker: Sweepstakes", html)
        self.assertNotIn("The Winner Signal", html)
        self.assertIn("Official operator announcement", html)
        self.assertIn("Two useful reminders", html)
        self.assertIn("From the SafeTracker guide library", html)
        self.assertIn("Read the guide", html)
        self.assertIn("## Two useful reminders", publish_winners.build_email(reports)[1])

    def test_kit_payload_schedules_a_private_broadcast(self):
        send_at = "2026-08-10T15:30:00+00:00"
        payload = publish_winners.build_kit_payload(
            "Winner Signal",
            "<p>One new report</p>",
            send_at=send_at,
        )
        self.assertEqual(payload["send_at"], send_at)
        self.assertFalse(payload["public"])
        self.assertNotIn("subscriber_filter", payload)

    def test_kit_draft_is_private_and_unscheduled(self):
        payload = publish_winners.build_kit_payload(
            "Winner Signal",
            "<p>One new report</p>",
            draft=True,
            send_at="2026-08-10T15:30:00+00:00",
        )
        self.assertIsNone(payload["send_at"])
        self.assertFalse(payload["public"])

    def test_kit_request_uses_v4_api_key_header(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            "broadcast": {"id": 123, "send_at": "2026-08-10T15:30:00Z"}
        }).encode()
        with patch.object(publish_winners.urllib.request, "urlopen", return_value=response) as urlopen:
            broadcast = publish_winners.create_kit_broadcast(
                "secret-key",
                publish_winners.build_kit_payload(
                    "Winner Signal",
                    "<p>One new report</p>",
                    send_at="2026-08-10T15:30:00+00:00",
                ),
            )
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.kit.com/v4/broadcasts")
        self.assertEqual(request.get_header("X-kit-api-key"), "secret-key")
        self.assertEqual(broadcast["id"], 123)

    def test_successful_edition_rebuilds_first_party_archive(self):
        reports = [{
            "id": "one",
            "raw_title": "Jamie R. won $500",
            "winner_name": "Jamie R.",
            "prize": "$500",
            "promotion_name": "Daily cash drawing",
            "source_id": "example",
            "source_name": "Example Sweeps",
            "source_type": "operator_announcement",
            "source_url": "https://example.com/winners",
            "reported_at": "2026-08-10T12:00:00Z",
            "author": "",
        }]
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            (base / "templates").mkdir()
            (base / "templates" / "newsletter-archive.html.j2").write_text(
                "{% for edition in editions %}{{ edition.subject }} {{ edition.slug }}{% endfor %}",
                encoding="utf-8",
            )
            (base / "templates" / "newsletter-edition.html.j2").write_text(
                "{{ edition.subject }} {% for report in edition.reports %}{{ report.source_url }}{% endfor %}",
                encoding="utf-8",
            )
            (base / "templates" / "newsletter-thanks.html.j2").write_text(
                "Check your inbox", encoding="utf-8"
            )
            (base / "templates" / "newsletter-confirmed.html.j2").write_text(
                "Subscription confirmed", encoding="utf-8"
            )
            path = newsletter_archive.archive_edition(
                reports,
                "1 new sweepstakes winner report — August 10, 2026",
                "2026-08-10T15:30:00Z",
                123,
                base=base,
            )
            newsletter_archive.archive_edition(
                reports,
                "1 new sweepstakes winner report — August 10, 2026",
                "2026-08-10T15:30:00Z",
                123,
                base=base,
            )
            payload = json.loads((base / "data" / "newsletter_editions.json").read_text(encoding="utf-8"))
            self.assertEqual(path.as_posix(), "newsletter/winner-signal-2026-08-10.html")
            self.assertEqual(len(payload["editions"]), 1)
            self.assertIn("winner-signal-2026-08-10", (base / "newsletter" / "index.html").read_text(encoding="utf-8"))
            self.assertIn("https://example.com/winners", (base / path).read_text(encoding="utf-8"))
            self.assertEqual(payload["editions"][0]["delivery_provider"], "unknown")

    def test_new_editorial_guides_enter_newsletter_rotation_automatically(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            (base / "data").mkdir()
            (base / "data" / "editorial.json").write_text(
                json.dumps({
                    "articles": [{
                        "slug": "new-weekly-guide",
                        "title": "A New Weekly Guide",
                        "meta_description": "A newly published guide.",
                        "published": "2026-08-01",
                    }]
                }),
                encoding="utf-8",
            )
            with patch.object(publish_winners, "BASE", base):
                guide, tips = publish_winners.edition_extras(date(2026, 8, 1))
            self.assertEqual(guide["slug"], "new-weekly-guide")
            self.assertEqual(len(tips), 2)

    def test_every_public_signup_placement_uses_shared_provider_config(self):
        homepage = publish_winners.BASE / "index.html"
        pages = [
            publish_winners.BASE / "winners.html",
            publish_winners.BASE / "newsletter" / "index.html",
            publish_winners.BASE / "newsletter" / "winner-signal-2026-08-10.html",
        ]
        homepage_markup = homepage.read_text(encoding="utf-8")
        self.assertIn("winner-signal-config.js", homepage_markup)
        self.assertIn("winner-signal-signup.js", homepage_markup)
        self.assertIn(
            "data-winner-signal-signup",
            (publish_winners.BASE / "assets" / "sweeps-tracker.js").read_text(encoding="utf-8"),
        )
        for page in pages:
            markup = page.read_text(encoding="utf-8")
            self.assertIn("data-winner-signal-signup", markup, page)
            self.assertIn("winner-signal-config.js", markup, page)
            self.assertIn("winner-signal-signup.js", markup, page)
        config = (publish_winners.BASE / "assets" / "winner-signal-config.js").read_text(encoding="utf-8")
        self.assertIn('provider: "kit"', config)
        self.assertNotIn("buttondown.com", config)
        self.assertIn('formUid: "5baaf4cb40"', config)
        self.assertIn(
            'scriptSrc: "https://safetracker-sweepstakes-winner-signal.kit.com/5baaf4cb40/index.js"',
            config,
        )
        self.assertNotIn("KIT_API_KEY", config)

    def test_subscription_status_pages_are_branded_and_private(self):
        thanks = (publish_winners.BASE / "newsletter" / "thanks.html").read_text(encoding="utf-8")
        confirmed = (publish_winners.BASE / "newsletter" / "confirmed.html").read_text(encoding="utf-8")
        self.assertIn('content="noindex,follow"', thanks)
        self.assertIn("Check your inbox", thanks)
        self.assertIn("winners@safetrackerhub.com", thanks)
        self.assertIn('content="noindex,follow"', confirmed)
        self.assertIn("Winner Signal by SafeTracker: Sweepstakes", confirmed)

    def test_workflow_uses_only_kit_for_production_delivery(self):
        workflow = (publish_winners.BASE / ".github" / "workflows" / "daily-winners.yml").read_text(encoding="utf-8")
        self.assertIn("KIT_API_KEY", workflow)
        self.assertNotIn("BUTTONDOWN_API_KEY", workflow)
        self.assertNotIn("WINNER_NEWSLETTER_KIT_CUTOVER", workflow)
        self.assertIn("if: always()", workflow)

    def test_rss_identity_is_stable_when_feed_metadata_changes(self):
        source = {
            "id": "community",
            "name": "Community",
            "type": "rss",
            "url": "https://example.com/feed",
            "homepage": "https://example.com/",
        }
        first = b"""<rss><channel><item>
            <title>A winner report</title>
            <link>https://example.com/thread/123</link>
            <guid>old-guid</guid>
            <pubDate>Mon, 27 Jul 2026 12:00:00 GMT</pubDate>
        </item></channel></rss>"""
        changed = first.replace(b"old-guid", b"new-guid").replace(
            b"27 Jul 2026", b"29 Jul 2026"
        )
        with patch.object(gather_winners, "fetch_bytes", return_value=first):
            first_report = gather_winners.fetch_rss(source)[0]
        with patch.object(gather_winners, "fetch_bytes", return_value=changed):
            changed_report = gather_winners.fetch_rss(source)[0]
        self.assertEqual(first_report["id"], changed_report["id"])

    def test_duplicate_source_urls_preserve_the_sent_record(self):
        database = sqlite3.connect(":memory:")
        database.row_factory = sqlite3.Row
        database.executescript(winner_db.SCHEMA)
        values = (
            "Winner", "", "", "", "", "", None,
            "2026-07-24T00:00:00Z", "source", "Source",
            "community_report", "https://example.com/thread/123",
            "source_reported", "",
        )
        database.execute(
            """
            INSERT INTO winner_reports (
                id, raw_title, winner_name, privacy_label, promotion_name, prize,
                operator, drawing_date, reported_at, source_id, source_name,
                source_type, source_url, verification_level, author,
                first_seen_at, last_seen_at, sent_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("old", *values, "2026-07-24T01:00:00Z", "2026-07-24T01:00:00Z", "2026-07-24T02:00:00Z"),
        )
        database.execute(
            """
            INSERT INTO winner_reports (
                id, raw_title, winner_name, privacy_label, promotion_name, prize,
                operator, drawing_date, reported_at, source_id, source_name,
                source_type, source_url, verification_level, author,
                first_seen_at, last_seen_at, sent_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("new", *values, "2026-07-30T01:00:00Z", "2026-07-30T01:00:00Z", None),
        )
        winner_db.deduplicate_reports(database)
        rows = database.execute("SELECT id, sent_at FROM winner_reports").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "old")
        self.assertEqual(rows[0]["sent_at"], "2026-07-24T02:00:00Z")


if __name__ == "__main__":
    unittest.main()
