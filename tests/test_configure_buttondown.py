import json
import unittest
from unittest.mock import MagicMock, patch

import configure_buttondown


class ButtondownConfigurationTests(unittest.TestCase):
    def test_approved_brand_and_redirects_are_explicit(self):
        settings = configure_buttondown.DESIRED_SETTINGS
        self.assertEqual(settings["name"], "Winner Signal")
        self.assertEqual(settings["from_name"], "Winner Signal by SafeTracker")
        self.assertEqual(
            settings["subscription_redirect_url"],
            "https://sweeps.safetrackerhub.com/newsletter/thanks.html",
        )
        self.assertEqual(
            settings["subscription_confirmation_redirect_url"],
            "https://sweeps.safetrackerhub.com/newsletter/confirmed.html",
        )
        self.assertIn(
            "{{ confirmation_url }}",
            settings["custom_subscription_confirmation_email_text"],
        )

    def test_apply_patches_only_drift_then_verifies(self):
        current = {
            "id": "newsletter-123",
            "username": "safetrackerhub",
            **configure_buttondown.DESIRED_SETTINGS,
            "from_name": "SafeTrackerHub Sweepstakes",
        }
        verified = {**current, "from_name": "Winner Signal by SafeTracker"}

        def response(payload):
            result = MagicMock()
            result.__enter__.return_value.read.return_value = json.dumps(payload).encode()
            return result

        with patch.object(
            configure_buttondown.urllib.request,
            "urlopen",
            side_effect=[response({"results": [current]}), response(verified), response(verified)],
        ) as urlopen:
            result = configure_buttondown.configure("secret", apply=True)

        patch_request = urlopen.call_args_list[1].args[0]
        self.assertEqual(patch_request.get_method(), "PATCH")
        self.assertEqual(
            json.loads(patch_request.data.decode()),
            {"from_name": "Winner Signal by SafeTracker"},
        )
        self.assertEqual(result["changed_fields"], ["from_name"])
        self.assertTrue(result["verified"])


if __name__ == "__main__":
    unittest.main()
