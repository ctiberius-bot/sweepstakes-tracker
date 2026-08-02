#!/usr/bin/env python3
"""Send one GitHub Actions discovery outcome to Signal Command."""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def fallback_payload(step_outcome):
    run_id = os.environ["GITHUB_RUN_ID"]
    repository = os.environ.get("GITHUB_REPOSITORY", "ctiberius-bot/sweepstakes-tracker")
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    conclusion = "success" if step_outcome == "success" else "failure"
    return {
        "jobId": "sweeps-daily-discovery",
        "providerRunId": run_id,
        "trigger": os.environ.get("GITHUB_EVENT_NAME", "schedule"),
        "status": "completed",
        "conclusion": conclusion,
        "startedAt": now(),
        "completedAt": now(),
        "candidatesSeen": 0,
        "candidatesAdded": 0,
        "quarantineTotal": 0,
        "sourceResults": [],
        "addedItems": [],
        "runUrl": f"{server}/{repository}/actions/runs/{run_id}",
        "summary": "Discovery step failed before a result record was written." if conclusion == "failure" else "Discovery completed without a result record.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    endpoint = os.environ["SIGNAL_COMMAND_DISCOVERY_URL"]
    token = os.environ["SIGNAL_COMMAND_PUBLICATION_TOKEN"]
    outcome = os.environ.get("DISCOVERY_STEP_OUTCOME", "failure")
    payload = json.loads(args.path.read_text(encoding="utf-8")) if args.path.exists() else fallback_payload(outcome)
    if outcome != "success":
        payload["conclusion"] = "failure"
        payload["summary"] = "Discovery step failed. See the linked GitHub Actions run."
    body = json.dumps(payload).encode("utf-8")
    request = Request(endpoint, data=body, method="POST", headers={
        "authorization": f"Bearer {token}",
        "content-type": "application/json",
        "user-agent": "SafeTrackerHub-Discovery-Reporter/1.0",
    })
    with urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))
        if not result.get("ok"):
            raise RuntimeError(f"Signal Command rejected discovery run: {result}")
        print(f"Signal Command recorded discovery run {result['providerRunId']} with {result['candidatesAdded']} additions.")


if __name__ == "__main__":
    main()
