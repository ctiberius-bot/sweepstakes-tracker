#!/usr/bin/env python3
"""Notify IndexNow participants about every canonical URL in the generated sitemap."""

import json
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
HOST = "sweeps.safetrackerhub.com"
KEY = "11c63a4b0413df328ccc7bd97d284321"
KEY_LOCATION = f"https://{HOST}/{KEY}.txt"
ENDPOINT = "https://api.indexnow.org/indexnow"


def sitemap_urls():
    root = ET.parse(BASE / "sitemap.xml").getroot()
    namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return [node.text for node in root.findall("s:url/s:loc", namespace) if node.text]


def main():
    urls = sitemap_urls()
    payload = json.dumps({
        "host": HOST,
        "key": KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": urls,
    }).encode("utf-8")
    request = urllib.request.Request(
        ENDPOINT,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.status
    except urllib.error.HTTPError as error:
        status = error.code
        if status not in {200, 202}:
            print(f"IndexNow rejected the submission with HTTP {status}.", file=sys.stderr)
            return 1
    if status not in {200, 202}:
        print(f"Unexpected IndexNow response: HTTP {status}.", file=sys.stderr)
        return 1
    print(f"Submitted {len(urls)} URLs to IndexNow (HTTP {status}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
