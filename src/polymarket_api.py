from __future__ import annotations

import json
import urllib.parse
import urllib.request

from constants import API_BASE


def fetch_positions(user: str) -> list[dict]:
    """Fetch all Polymarket positions for a user with pagination."""
    rows: list[dict] = []
    offset = 0
    while True:
        params = {
            "user": user,
            "sizeThreshold": 0,
            "limit": 500,
            "offset": offset,
            "sortDirection": "DESC",
        }
        url = API_BASE + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            chunk = json.loads(resp.read().decode("utf-8"))
        if not chunk:
            break
        rows.extend(chunk)
        if len(chunk) < 500:
            break
        offset += 500
    return rows
