#!/usr/bin/env python3
"""Apply and verify the temporary Buttondown branding for Winner Signal."""

import argparse
import json
import os
import urllib.error
import urllib.request

API_BASE = "https://api.buttondown.com/v1"
TARGET_USERNAME = "safetrackerhub"
TARGET_NEWSLETTER_ID = "578556bf-3096-48bb-a643-23092ecbb24f"
DESIRED_SETTINGS = {
    "name": "Winner Signal",
    "from_name": "Winner Signal by SafeTracker",
    "description": (
        "Source-linked sweepstakes winner reports from SafeTracker: Sweepstakes. "
        "No empty editions and no manufactured winner claims."
    ),
    "subscription_redirect_url": "https://sweeps.safetrackerhub.com/newsletter/thanks.html",
    "subscription_confirmation_redirect_url": (
        "https://sweeps.safetrackerhub.com/newsletter/confirmed.html"
    ),
    "custom_subscription_confirmation_email_subject": (
        "Confirm your Winner Signal subscription"
    ),
    "custom_subscription_confirmation_email_text": (
        "You're one click away from Winner Signal by SafeTracker: Sweepstakes.\n\n"
        "[Confirm my subscription]({{ confirmation_url }})\n\n"
        "We send only when the daily monitor finds new, source-linked winner reports."
    ),
    "tint_color": "#0B5D56",
    "timezone": "America/New_York",
}


def api_request(token, method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        f"{API_BASE}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
            "User-Agent": "SafeTracker-WinnerSignalConfig/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Buttondown API returned HTTP {error.code}: {detail}") from error


def find_newsletter(token):
    newsletter = api_request(token, "GET", f"/newsletters/{TARGET_NEWSLETTER_ID}")
    if newsletter.get("username") != TARGET_USERNAME:
        raise RuntimeError(
            f"Buttondown newsletter {TARGET_NEWSLETTER_ID!r} is not {TARGET_USERNAME!r}."
        )
    return newsletter


def setting_snapshot(newsletter):
    return {field: newsletter.get(field) for field in DESIRED_SETTINGS}


def configure(token, *, apply=False):
    newsletter = find_newsletter(token)
    before = setting_snapshot(newsletter)
    changed_fields = sorted(
        field for field, desired in DESIRED_SETTINGS.items() if before.get(field) != desired
    )
    if apply and changed_fields:
        api_request(
            token,
            "PATCH",
            f"/newsletters/{newsletter['id']}",
            {field: DESIRED_SETTINGS[field] for field in changed_fields},
        )
    verified = api_request(token, "GET", f"/newsletters/{newsletter['id']}")
    after = setting_snapshot(verified)
    remaining = sorted(
        field for field, desired in DESIRED_SETTINGS.items() if after.get(field) != desired
    )
    result = {
        "newsletter_id": str(newsletter["id"]),
        "username": newsletter["username"],
        "apply_requested": apply,
        "changed_fields": changed_fields if apply else [],
        "verified": not remaining,
        "remaining_drift": remaining,
        "settings": after,
    }
    if apply and remaining:
        raise RuntimeError(f"Buttondown settings did not persist: {', '.join(remaining)}")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the approved branding and subscriber redirect settings before verifying them.",
    )
    args = parser.parse_args()
    token = os.environ.get("BUTTONDOWN_API_KEY")
    if not token:
        raise SystemExit("BUTTONDOWN_API_KEY is required.")
    print(json.dumps(configure(token, apply=args.apply), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
