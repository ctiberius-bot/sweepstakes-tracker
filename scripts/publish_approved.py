#!/usr/bin/env python3
"""Consume versioned Signal Command manifests into the Sweepstakes tracker.

The transport is deliberately generic: Signal Command owns review state and
emits a tracker-neutral manifest. This adapter owns the Sweepstakes record
shape, ScamFactor rules, generated cards/profiles, and release acknowledgement.
Other trackers can reuse the transport and implement their own adapter.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parents[1]
DATA_FILE = BASE / "data.json"
DEFAULT_API_URL = "https://sc.justsignal.company/api/publications"
PUBLIC_ORIGIN = "https://sweeps.safetrackerhub.com"
TARGET = "sweepstakes"
WEIGHTS = {
    "transparency": 0.30,
    "fulfillment": 0.25,
    "entry_model": 0.20,
    "win_realism": 0.15,
    "marketing": 0.10,
}
PROFILE_FIELDS = {
    "siteType",
    "prizes",
    "draw",
    "unsubscribe",
    "redFlags",
    "entryRequirements",
    "winnerEvidence",
    "marketingIntensity",
    "dataPractices",
}


class PublicationError(ValueError):
    """A manifest cannot safely enter this tracker."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def clean_text(value: Any, label: str, minimum: int = 3, maximum: int = 2000) -> str:
    text = str(value or "").strip()[:maximum]
    if len(text) < minimum:
        raise PublicationError(f"{label} is missing or too short")
    return text


def round_to_half(value: float) -> float:
    return math.floor(value * 2 + 0.5) / 2


def same_domain(url: str, domain: str) -> bool:
    host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    candidate = domain.lower().removeprefix("www.")
    return host == candidate or host.endswith(f".{candidate}")


def validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    if manifest.get("schemaVersion") != 1:
        raise PublicationError("unsupported publication schema version")
    if manifest.get("target") != TARGET or manifest.get("pipeline") != "Sweeps":
        raise PublicationError("publication was sent to the wrong tracker adapter")
    candidate_id = clean_text(manifest.get("candidateId"), "candidateId", 3, 80)
    name = clean_text(manifest.get("name"), "name", 2, 160)
    domain = clean_text(manifest.get("domain"), "domain", 4, 255).lower()
    slug = clean_text(manifest.get("slug"), "slug", 2, 80)
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise PublicationError("slug is not URL-safe")
    official_url = clean_text(manifest.get("officialUrl"), "officialUrl", 10, 500)
    if urlsplit(official_url).scheme != "https" or not same_domain(official_url, domain):
        raise PublicationError("officialUrl must be HTTPS on the candidate domain")

    profile = manifest.get("profile")
    if not isinstance(profile, dict) or set(profile) != PROFILE_FIELDS:
        raise PublicationError("Sweepstakes publication profile fields are incomplete")
    cleaned_profile = {key: clean_text(profile.get(key), key) for key in PROFILE_FIELDS}

    rating = manifest.get("rating")
    if not isinstance(rating, dict) or rating.get("label") != "ScamFactor":
        raise PublicationError("rating must use the ScamFactor adapter")
    if rating.get("min") != 1 or rating.get("max") != 10 or rating.get("lowerIsBetter") is not True:
        raise PublicationError("ScamFactor scale metadata is invalid")
    raw_inputs = rating.get("inputs")
    if not isinstance(raw_inputs, dict) or set(raw_inputs) != set(WEIGHTS):
        raise PublicationError("all five ScamFactor inputs are required")
    score_inputs: dict[str, float] = {}
    rating_evidence: dict[str, str] = {}
    for key, weight in WEIGHTS.items():
        item = raw_inputs.get(key)
        if not isinstance(item, dict) or not math.isclose(float(item.get("weight", -1)), weight):
            raise PublicationError(f"{key} has an invalid weight")
        value = float(item.get("value", 0))
        if not 1 <= value <= 10:
            raise PublicationError(f"{key} is outside the 1–10 range")
        evidence = clean_text(item.get("evidence"), f"{key} evidence", 10)
        score_inputs[key] = value
        rating_evidence[key] = evidence
    calculated_score = round_to_half(sum(score_inputs[key] * weight for key, weight in WEIGHTS.items()))
    if not math.isclose(float(rating.get("score", -1)), calculated_score):
        raise PublicationError("ScamFactor score does not match the weighted inputs")

    publication = manifest.get("publication")
    if not isinstance(publication, dict):
        raise PublicationError("publication metadata is missing")
    requested_at = clean_text(publication.get("requestedAt"), "requestedAt", 10, 40)
    return {
        "candidate_id": candidate_id,
        "name": name,
        "domain": domain,
        "slug": slug,
        "official_url": official_url,
        "profile": cleaned_profile,
        "score": calculated_score,
        "score_inputs": score_inputs,
        "rating_evidence": rating_evidence,
        "requested_at": requested_at,
        "requested_by": clean_text(publication.get("requestedBy"), "requestedBy", 3, 120),
    }


def build_site(manifest: dict[str, Any], checksum: str) -> dict[str, Any]:
    item = validate_manifest(manifest)
    profile = item["profile"]
    return {
        "name": item["name"],
        "score": item["score"],
        "theme": profile["siteType"],
        "prizes": profile["prizes"],
        "draw": profile["draw"],
        "unsub": profile["unsubscribe"],
        "redFlags": profile["redFlags"],
        "link": item["official_url"],
        "scrape_url": item["official_url"],
        "slug": item["slug"],
        "score_inputs": item["score_inputs"],
        "entry_requirements": profile["entryRequirements"],
        "winner_evidence": profile["winnerEvidence"],
        "marketing_intensity": profile["marketingIntensity"],
        "data_practices": profile["dataPractices"],
        "rating_evidence": item["rating_evidence"],
        "weekly_check_status": "not_checked",
        "last_scored": item["requested_at"],
        "profile_refresh": {
            "status": "editorially_verified",
            "checked_at": item["requested_at"],
            "source_url": item["official_url"],
            "changed": False,
            "error": None,
        },
        "publication_source": {
            "system": "signal-command",
            "candidate_id": item["candidate_id"],
            "schema_version": 1,
            "payload_checksum": checksum,
            "approved_at": item["requested_at"],
            "approved_by": item["requested_by"],
        },
    }


def apply_publications(data: dict[str, Any], publications: list[dict[str, Any]]) -> tuple[bool, list[dict[str, str]]]:
    sites = data.setdefault("sites", [])
    changed = False
    results: list[dict[str, str]] = []
    for publication in publications:
        manifest = publication.get("payload")
        checksum = clean_text(publication.get("checksum"), "checksum", 64, 64)
        if not isinstance(manifest, dict) or not re.fullmatch(r"[a-f0-9]{64}", checksum):
            raise PublicationError("publication envelope is invalid")
        site = build_site(manifest, checksum)
        candidate_id = site["publication_source"]["candidate_id"]
        existing_index = next((
            index for index, current in enumerate(sites)
            if current.get("publication_source", {}).get("candidate_id") == candidate_id
            or same_domain(str(current.get("link", "")), str(manifest.get("domain", "")))
        ), None)
        if existing_index is None:
            sites.append(site)
            changed = True
        else:
            current = sites[existing_index]
            if current.get("publication_source", {}).get("payload_checksum") != checksum:
                sites[existing_index] = {**current, **site}
                changed = True
        results.append({
            "candidateId": candidate_id,
            "checksum": checksum,
            "publicationUrl": f"{PUBLIC_ORIGIN}/reviews/{site['slug']}",
        })
    if changed:
        sites.sort(key=lambda site: (float(site["score"]), site["name"].casefold()))
        for rank, site in enumerate(sites, start=1):
            site["rank"] = rank
        data["last_publication_ingest"] = utc_now()
    return changed, results


def api_request(api_url: str, token: str, *, method: str = "GET", body: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = Request(
        api_url,
        data=payload,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "SafeTracker publication adapter/1.0",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Signal Command returned HTTP {error.code}: {detail}") from error
    except (URLError, TimeoutError) as error:
        raise RuntimeError(f"Signal Command could not be reached: {error}") from error


def write_github_output(key: str, value: str) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as stream:
            stream.write(f"{key}={value}\n")


def ingest(args: argparse.Namespace) -> int:
    token = args.token or os.environ.get("SIGNAL_COMMAND_PUBLICATION_TOKEN", "")
    if not token:
        raise RuntimeError("SIGNAL_COMMAND_PUBLICATION_TOKEN is not configured")
    response = api_request(f"{args.api_url}?target={TARGET}", token)
    publications = response.get("publications", [])
    if not isinstance(publications, list):
        raise RuntimeError("Signal Command returned an invalid publication list")
    data = json.loads(args.data_file.read_text(encoding="utf-8"))
    changed, results = apply_publications(data, publications)
    if changed:
        args.data_file.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.results.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    write_github_output("count", str(len(results)))
    write_github_output("changed", "true" if changed else "false")
    print(f"Validated {len(results)} publication(s); inventory changed={changed}")
    return 0


def acknowledge(args: argparse.Namespace) -> int:
    token = args.token or os.environ.get("SIGNAL_COMMAND_PUBLICATION_TOKEN", "")
    if not token:
        raise RuntimeError("SIGNAL_COMMAND_PUBLICATION_TOKEN is not configured")
    results = json.loads(args.results.read_text(encoding="utf-8"))
    for result in results:
        api_request(args.api_url, token, method="POST", body={**result, "status": "published"})
    print(f"Acknowledged {len(results)} published profile(s)")
    return 0


def verify_live(args: argparse.Namespace) -> int:
    results = json.loads(args.results.read_text(encoding="utf-8"))
    deadline = time.monotonic() + args.timeout
    pending = {result["publicationUrl"] for result in results}
    while pending and time.monotonic() < deadline:
        for url in list(pending):
            try:
                request = Request(url, method="GET", headers={"User-Agent": "SafeTracker release verifier/1.0"})
                with urlopen(request, timeout=20) as response:
                    if response.status == 200:
                        pending.remove(url)
            except (HTTPError, URLError, TimeoutError):
                pass
        if pending:
            time.sleep(10)
    if pending:
        raise RuntimeError(f"public profile verification timed out: {', '.join(sorted(pending))}")
    print(f"Verified {len(results)} live profile(s)")
    return 0


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser()
    subcommands = command.add_subparsers(dest="command", required=True)
    for name in ("ingest", "verify", "ack"):
        sub = subcommands.add_parser(name)
        sub.add_argument("--results", type=Path, required=True)
        if name != "verify":
            sub.add_argument("--api-url", default=os.environ.get("SIGNAL_COMMAND_PUBLICATION_URL", DEFAULT_API_URL))
            sub.add_argument("--token", default="")
        if name == "ingest":
            sub.add_argument("--data-file", type=Path, default=DATA_FILE)
        if name == "verify":
            sub.add_argument("--timeout", type=int, default=240)
    return command


def main() -> int:
    args = parser().parse_args()
    if args.command == "ingest":
        return ingest(args)
    if args.command == "verify":
        return verify_live(args)
    return acknowledge(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PublicationError, RuntimeError) as error:
        print(f"Publication failed: {error}", file=sys.stderr)
        raise SystemExit(1)
