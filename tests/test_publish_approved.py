import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "publish_approved.py"
SPEC = importlib.util.spec_from_file_location("publish_approved", MODULE_PATH)
publisher = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(publisher)


def manifest():
    inputs = {
        "transparency": {"label": "Transparency", "weight": .30, "value": 4, "evidence": "Official rules identify the operator."},
        "fulfillment": {"label": "Fulfillment", "weight": .25, "value": 6, "evidence": "Only limited dated winner evidence was found."},
        "entry_model": {"label": "Entry", "weight": .20, "value": 5, "evidence": "The public form states that entry is free."},
        "win_realism": {"label": "Realism", "weight": .15, "value": 5, "evidence": "Prize and drawing cadence are documented."},
        "marketing": {"label": "Marketing", "weight": .10, "value": 7, "evidence": "The form includes partner marketing consent."},
    }
    return {
        "schemaVersion": 1,
        "target": "sweepstakes",
        "pipeline": "Sweeps",
        "candidateId": "SW-TEST0001",
        "name": "Example Sweeps",
        "domain": "example.com",
        "slug": "example-sweeps",
        "officialUrl": "https://www.example.com/",
        "profile": {
            "siteType": "daily",
            "prizes": "Recurring gift-card drawings",
            "draw": "Daily drawings",
            "unsubscribe": "Use the footer opt-out link",
            "redFlags": "Partner marketing consent is presented during entry.",
            "entryRequirements": "A valid email address is required.",
            "winnerEvidence": "A dated winner page was located.",
            "marketingIntensity": "Frequent reminder email is expected.",
            "dataPractices": "Entry data may be shared with named partners.",
        },
        "rating": {"label": "ScamFactor", "min": 1, "max": 10, "lowerIsBetter": True, "score": 5.0, "inputs": inputs},
        "publication": {"requestedAt": "2026-08-02T12:00:00Z", "requestedBy": "reviewer"},
    }


class PublicationAdapterTest(unittest.TestCase):
    def test_adds_complete_ranked_site_and_is_idempotent(self):
        data = {"sites": [{"name": "Existing", "score": 2, "rank": 1, "link": "https://existing.example/"}]}
        envelope = [{"checksum": "a" * 64, "payload": manifest()}]
        changed, results = publisher.apply_publications(data, envelope)
        self.assertTrue(changed)
        self.assertEqual(results[0]["publicationUrl"], "https://sweeps.safetrackerhub.com/reviews/example-sweeps")
        added = next(site for site in data["sites"] if site["name"] == "Example Sweeps")
        self.assertEqual(added["score"], 5.0)
        self.assertEqual(added["publication_source"]["candidate_id"], "SW-TEST0001")
        self.assertEqual(added["score_inputs"]["transparency"], 4.0)
        changed_again, _ = publisher.apply_publications(data, envelope)
        self.assertFalse(changed_again)

    def test_rejects_tampered_score(self):
        payload = manifest()
        payload["rating"]["score"] = 1
        with self.assertRaises(publisher.PublicationError):
            publisher.build_site(payload, "b" * 64)

    def test_rejects_cross_domain_official_url(self):
        payload = manifest()
        payload["officialUrl"] = "https://attacker.example/"
        with self.assertRaises(publisher.PublicationError):
            publisher.build_site(payload, "c" * 64)


if __name__ == "__main__":
    unittest.main()
