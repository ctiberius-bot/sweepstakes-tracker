#!/usr/bin/env python3
"""Read-only readiness checks for the dedicated Winner Signal Kit account."""

import json
import os
import urllib.error
import urllib.request
from collections import Counter


API_BASE = "https://api.kit.com/v4"
EXPECTED_ACCOUNT_EMAIL = "sweepstakes-research@safetrackerhub.com"
EXPECTED_FORM_NAMES = ("Winner Signal", "Winner Signal — Website Signup")


def api_get(token, path):
    request = urllib.request.Request(
        f"{API_BASE}{path}",
        method="GET",
        headers={
            "X-Kit-Api-Key": token,
            "Accept": "application/json",
            "User-Agent": "SafeTracker-WinnerSignalPreflight/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Kit API returned HTTP {error.code}: {detail}") from error


def validate(token):
    account_response = api_get(token, "/account")
    forms_response = api_get(token, "/forms?status=active&per_page=1000")
    subscribers_response = api_get(
        token,
        "/subscribers?status=all&include_total_count=true&per_page=1000",
    )
    templates_response = api_get(token, "/email_templates?per_page=1000")

    account = account_response.get("account", {})
    user = account_response.get("user", {})
    identities = {
        str(user.get("email", "")).lower(),
        str(account.get("primary_email_address", "")).lower(),
    }
    identity_matches = EXPECTED_ACCOUNT_EMAIL in identities

    active_forms = [form for form in forms_response.get("forms", []) if not form.get("archived")]
    accepted_form_names = {name.casefold() for name in EXPECTED_FORM_NAMES}
    matching_forms = [
        form
        for form in active_forms
        if str(form.get("name", "")).strip().casefold() in accepted_form_names
    ]
    matching_form = matching_forms[0] if len(matching_forms) == 1 else None
    form_ready = bool(
        matching_form
        and matching_form.get("type") == "embed"
        and matching_form.get("uid")
        and matching_form.get("embed_js")
        and matching_form.get("embed_url")
    )

    subscribers = subscribers_response.get("subscribers", [])
    subscriber_states = dict(
        sorted(Counter(item.get("state", "unknown") for item in subscribers).items())
    )
    subscriber_pagination = subscribers_response.get("pagination", {})
    subscriber_count = subscriber_pagination.get("total_count", len(subscribers))
    subscribers_complete = not subscriber_pagination.get("has_next_page", False)

    templates = templates_response.get("email_templates", [])
    default_templates = [
        {
            "id": template.get("id"),
            "name": template.get("name"),
            "category": template.get("category"),
        }
        for template in templates
        if template.get("is_default")
    ]

    checks = {
        "api_key_valid": True,
        "dedicated_account_identity": identity_matches,
        "one_active_winner_signal_form": len(matching_forms) == 1,
        "winner_signal_form_embed_ready": form_ready,
        "subscriber_snapshot_complete": subscribers_complete,
        "default_email_template_present": len(default_templates) == 1,
    }
    result = {
        "ready_for_non_sending_integration": all(checks.values()),
        "checks": checks,
        "account": {
            "id": account.get("id"),
            "name": account.get("name"),
            "plan_type": account.get("plan_type"),
            "primary_email_address": account.get("primary_email_address"),
            "user_email": user.get("email"),
            "timezone": (account.get("timezone") or {}).get("name"),
        },
        "winner_signal_form": (
            {
                "id": matching_form.get("id"),
                "name": matching_form.get("name"),
                "type": matching_form.get("type"),
                "uid": matching_form.get("uid"),
                "embed_js": matching_form.get("embed_js"),
                "embed_url": matching_form.get("embed_url"),
            }
            if matching_form
            else None
        ),
        "active_forms": [
            {
                "id": form.get("id"),
                "name": form.get("name"),
                "type": form.get("type"),
                "uid": form.get("uid"),
                "embed_js": form.get("embed_js"),
                "embed_url": form.get("embed_url"),
            }
            for form in active_forms
        ],
        "subscribers": {
            "total_count": subscriber_count,
            "states": subscriber_states,
        },
        "default_email_templates": default_templates,
        "sending_approval_verified": False,
        "sending_approval_note": (
            "The public V4 API does not expose the account review banner. "
            "Kit Support approval or removal of the disabled-features banner must be verified separately."
        ),
    }
    if not identity_matches:
        raise RuntimeError("KIT_API_KEY does not belong to the dedicated Winner Signal account.")
    return result


def main():
    token = os.environ.get("KIT_API_KEY")
    if not token:
        raise SystemExit("KIT_API_KEY is required.")
    result = validate(token)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["ready_for_non_sending_integration"]:
        raise SystemExit("Kit preflight is incomplete; see failed checks above.")


if __name__ == "__main__":
    main()
