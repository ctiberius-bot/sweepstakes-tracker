import json
import unittest
from unittest.mock import MagicMock, patch

import validate_kit


def response(payload):
    result = MagicMock()
    result.__enter__.return_value.read.return_value = json.dumps(payload).encode()
    return result


class KitReadinessTests(unittest.TestCase):
    def test_read_only_preflight_reports_public_integration_values(self):
        account = {
            "user": {"email": validate_kit.EXPECTED_ACCOUNT_EMAIL},
            "account": {
                "id": 42,
                "name": "SafeTracker",
                "plan_type": "newsletter",
                "primary_email_address": validate_kit.EXPECTED_ACCOUNT_EMAIL,
                "timezone": {"name": "America/New_York"},
            },
        }
        forms = {
            "forms": [
                {
                    "id": 51,
                    "name": "Winner Signal — Website Signup",
                    "type": "embed",
                    "uid": "abc123",
                    "embed_js": "https://example.kit.com/abc123/index.js",
                    "embed_url": "https://example.kit.com/abc123",
                    "archived": False,
                }
            ]
        }
        subscribers = {
            "subscribers": [{"state": "active"}, {"state": "cancelled"}],
            "pagination": {"has_next_page": False, "total_count": 2},
        }
        templates = {
            "email_templates": [
                {"id": 6, "name": "Text Only", "is_default": True, "category": "HTML"}
            ]
        }

        with patch.object(
            validate_kit.urllib.request,
            "urlopen",
            side_effect=[response(account), response(forms), response(subscribers), response(templates)],
        ) as urlopen:
            result = validate_kit.validate("secret")

        self.assertTrue(result["ready_for_non_sending_integration"])
        self.assertEqual(result["winner_signal_form"]["uid"], "abc123")
        self.assertEqual(result["subscribers"]["states"], {"active": 1, "cancelled": 1})
        self.assertFalse(result["sending_approval_verified"])
        self.assertTrue(all(call.args[0].method == "GET" for call in urlopen.call_args_list))

    def test_rejects_key_for_another_kit_account(self):
        account = {
            "user": {"email": "hello@kitandfile.com"},
            "account": {"primary_email_address": "hello@kitandfile.com"},
        }
        empty = {"forms": [], "subscribers": [], "email_templates": [], "pagination": {}}
        with patch.object(
            validate_kit.urllib.request,
            "urlopen",
            side_effect=[response(account), response(empty), response(empty), response(empty)],
        ):
            with self.assertRaisesRegex(RuntimeError, "dedicated Winner Signal account"):
                validate_kit.validate("wrong-secret")


if __name__ == "__main__":
    unittest.main()
