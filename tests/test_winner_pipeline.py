import tempfile
import unittest
import json
from datetime import date
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import gather_winners
import publish_winners


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
        self.assertIn("The Winner Signal", html)
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


if __name__ == "__main__":
    unittest.main()
