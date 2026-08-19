"""Country outlines and reference cities from Natural Earth, projected to SVG.

Natural Earth data is public domain. Files are downloaded once and cached under
~/.cache/maprot/ so builds are offline after the first run.
"""
from __future__ import annotations

import json
import math
import os
import urllib.request
from pathlib import Path

NE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson"
COUNTRIES = f"{NE}/ne_10m_admin_0_countries.geojson"
PLACES = f"{NE}/ne_10m_populated_places_simple.geojson"


def cache_dir() -> Path:
    d = Path(os.environ.get("MAPROT_CACHE", Path.home() / ".cache" / "maprot"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _fetch(url: str, name: str) -> dict:
    path = cache_dir() / name
    if not path.exists():
        print(f"  fetching {name} (once, then cached)...")
        req = urllib.request.Request(url, headers={"User-Agent": "maprot"})
        with urllib.request.urlopen(req, timeout=180) as r, open(path, "wb") as f:
            f.write(r.read())
    with open(path) as f:
        return json.load(f)


def _rings(geom: dict) -> list[list]:
    if geom["type"] == "MultiPolygon":
        return [r for poly in geom["coordinates"] for r in poly]
    return list(geom["coordinates"])


class Projection:
    """Spherical Mercator fitted to a set of rings, normalised to a fixed height."""

    def __init__(self, rings: list[list], height: float = 1000.0):
        lons = [p[0] for r in rings for p in r]
        lats = [p[1] for r in rings for p in r]
        self.lon_min, self.lon_max = min(lons), max(lons)
        self.lat_min, self.lat_max = min(lats), max(lats)
        self.m_max = self._merc(self.lat_max)
        m_min = self._merc(self.lat_min)
        self.sy = height / (self.m_max - m_min)
        self.h = height
        self.w = math.radians(self.lon_max - self.lon_min) * self.sy

    @staticmethod
    def _merc(lat: float) -> float:
        return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))

    def xy(self, lat: float, lon: float) -> tuple[float, float]:
        return (
            math.radians(lon - self.lon_min) * self.sy,
            (self.m_max - self._merc(lat)) * self.sy,
        )

    def js(self) -> dict:
        return {"LON_MIN": self.lon_min, "M_MAX": self.m_max, "SY": self.sy,
                "W": round(self.w, 1), "H": self.h}


def country(iso_a3: str, height: float = 1000.0):
    """Return (svg_path_strings, Projection) for one country by ISO A3 code."""
    iso = iso_a3.upper()
    data = _fetch(COUNTRIES, "ne_10m_countries.geojson")
    feat = next(
        (f for f in data["features"]
         if iso in (f["properties"].get("ADM0_A3"), f["properties"].get("ISO_A3"),
                    f["properties"].get("SOV_A3"))),
        None,
    )
    if feat is None:
        raise SystemExit(f"maprot: no Natural Earth country matched ISO A3 {iso!r}")

    rings = sorted(_rings(feat["geometry"]), key=len, reverse=True)
    proj = Projection(rings, height)
    paths = []
    for r in rings:
        pts = [proj.xy(lat, lon) for lon, lat in r]
        paths.append("M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z")
    return paths, proj


def reference_cities(iso_a3: str, proj: Projection, limit: int = 8,
                     exclude: set[str] | None = None) -> list[dict]:
    """Biggest cities in the country, for orientation. Labels are placed on the
    side with more room: cities east of centre get left-hand labels."""
    iso = iso_a3.upper()
    exclude = {e.lower() for e in (exclude or set())}
    data = _fetch(PLACES, "ne_10m_places.geojson")
    rows = []
    for f in data["features"]:
        pr = f["properties"]
        if pr.get("adm0_a3") != iso:
            continue
        name = pr.get("name") or ""
        if name.lower() in exclude:
            continue
        lon, lat = f["geometry"]["coordinates"][:2]
        rows.append({"name": name, "lat": lat, "lon": lon,
                     "pop": pr.get("pop_max") or 0})
    rows.sort(key=lambda r: -r["pop"])
    out = []
    mid = proj.w / 2
    for r in rows[:limit]:
        x, _ = proj.xy(r["lat"], r["lon"])
        out.append({"name": r["name"], "lat": r["lat"], "lon": r["lon"],
                    "side": "l" if x > mid else "r"})
    return out
