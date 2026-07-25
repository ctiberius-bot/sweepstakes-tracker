import unittest

import discover_candidates as discovery


class DiscoveryTests(unittest.TestCase):
    def test_extracts_relevant_link_and_excludes_privacy(self):
        source = {
            "id": "fixture",
            "name": "Fixture source",
            "url": "https://example.com/directory",
            "kind": "promotion_directory",
        }
        html = """
        <a href="/win-car-sweepstakes">Win a car sweepstakes</a>
        <a href="/privacy">Privacy policy</a>
        """
        candidates = discovery.extract_candidates(html, source)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["candidate_type"], "limited")
        self.assertEqual(candidates[0]["discovered_url"], "https://example.com/win-car-sweepstakes")

    def test_canonical_url_removes_tracking(self):
        url = discovery.canonical_url("HTTPS://Example.COM/promo/?utm_source=x&id=7#entry")
        self.assertEqual(url, "https://example.com/promo?id=7")


if __name__ == "__main__":
    unittest.main()
