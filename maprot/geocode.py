"""Nominatim (OpenStreetMap) geocoding, with a courteous rate limit."""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request

ENDPOINT = "https://nominatim.openstreetmap.org/search"
UA = "maprot/0.1 (https://github.com/harshh-jainn/maprot)"
_last = [0.0]


def lookup(query: str, limit: int = 3) -> list[dict]:
    """Geocode a free-text query. Returns [] rather than raising."""
    wait = 1.1 - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.time()

    url = ENDPOINT + "?" + urllib.parse.urlencode(
        {"q": query, "format": "json", "limit": limit, "addressdetails": 1}
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            rows = json.load(r)
    except Exception as e:  # network flake, rate limit, malformed reply
        print(f"  geocode failed for {query!r}: {e}")
        return []
    return [
        {"lat": float(x["lat"]), "lon": float(x["lon"]),
         "type": x.get("type"), "display": x.get("display_name", "")}
        for x in rows
    ]


def best(name: str, locality: str = "", country: str = "") -> dict | None:
    """Try the most specific query first, then widen. Marks 'approx' when the
    venue itself could not be found and we fell back to its locality."""
    tries = [q for q in (
        ", ".join(p for p in (name, locality, country) if p),
        ", ".join(p for p in (name, country) if p),
    ) if q]
    for q in tries:
        hits = lookup(q, limit=1)
        if hits:
            return {**hits[0], "approx": False, "query": q}
    if locality:
        hits = lookup(", ".join(p for p in (locality, country) if p), limit=1)
        if hits:
            return {**hits[0], "approx": True, "query": locality}
    return None
