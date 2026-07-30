import tempfile
import unittest
import json
import sqlite3
from datetime import date
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import gather_winners
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

    def test_preview_never_requires_buttondown(self):
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
        self.assertNotIn("The Winner Signal", html)
        self.assertIn("Official operator announcement", html)
        self.assertIn("Two useful reminders", html)
        self.assertIn("From the SafeTracker guide library", html)
        self.assertIn("Read the guide", html)
        self.assertIn("## Two useful reminders", publish_winners.build_email(reports)[1])

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
