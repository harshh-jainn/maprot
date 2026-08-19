"""Turn a board into one self-contained HTML file.

Everything is inlined — photos become data URIs — because the page has to work
offline, behind a share link, and inside sandboxes that block external hosts.
Google Fonts is the one remote dependency, and there are real fallbacks.
"""
from __future__ import annotations

import base64
import json
import math
from datetime import date
from pathlib import Path

from . import geo

TPL = Path(__file__).parent / "templates"
PAD = 46.0          # svg units of breathing room around the country
FAN_THRESHOLD = 30.0  # closer than this and pins would overlap
FAN_RADIUS = 46.0


def _b64(p: Path) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode()


def _fan(places: list[dict]) -> None:
    """Spread pins that sit on top of each other.

    At national scale two venues a kilometre apart are ~3 units apart while a
    pin is ~29 wide, so they must be offset or they are unclickable. Each
    cluster keeps a small anchor dot at the true location with a leader line
    out to the pin. Angles start at straight up and divide the circle, which
    separates neighbouring clusters better than fanning sideways.
    """
    todo = list(places)
    while todo:
        seed = todo.pop(0)
        group = [seed]
        for other in todo[:]:
            if math.hypot(seed["ax"] - other["ax"], seed["ay"] - other["ay"]) < FAN_THRESHOLD:
                group.append(other)
                todo.remove(other)
        if len(group) == 1:
            seed["x"], seed["y"], seed["fanned"] = seed["ax"], seed["ay"], False
            continue
        cx = sum(p["ax"] for p in group) / len(group)
        cy = sum(p["ay"] for p in group) / len(group)
        for i, p in enumerate(group):
            angle = p.get("fan")
            if angle is None:
                angle = -90 + i * (360 / len(group))
            a = math.radians(angle)
            p["x"] = cx + math.cos(a) * FAN_RADIUS
            p["y"] = cy + math.sin(a) * FAN_RADIUS
            p["fanned"] = True


def _graticule(proj: geo.Projection) -> dict:
    lon, lat = [], []
    for v in range(math.ceil(proj.lon_min), math.floor(proj.lon_max) + 1):
        x, _ = proj.xy((proj.lat_min + proj.lat_max) / 2, v)
        lon.append({"x": round(x, 1), "label": f"{v}°"})
    for v in range(math.ceil(proj.lat_min), math.floor(proj.lat_max) + 1):
        _, y = proj.xy(v, proj.lon_min)
        lat.append({"y": round(y, 1), "label": f"{v}°"})
    return {"lon": lon, "lat": lat}


def build(board: dict, board_path: Path, out: Path,
          quality: int | None = None) -> tuple[Path, list[str]]:
    """Render the board. Returns (output path, warnings)."""
    warnings: list[str] = []
    places = [dict(p) for p in board.get("places", [])]
    places.sort(key=lambda p: p.get("n", 0))
    if not places:
        raise SystemExit("maprot: board has no places yet")

    paths, proj = geo.country(board["country"])

    for p in places:
        p["ax"], p["ay"] = [round(v, 1) for v in proj.xy(p["lat"], p["lon"])]
    _fan(places)
    for p in places:
        p["x"], p["y"] = round(p["x"], 1), round(p["y"], 1)

    # reference towns: skip anywhere that already has a pin of its own
    pinned = {(p.get("loc") or "").lower() for p in places}
    pinned |= {p["name"].lower() for p in places}
    towns_cfg = board.get("reference_cities", 8)
    if isinstance(towns_cfg, int):
        towns = geo.reference_cities(board["country"], proj, towns_cfg, exclude=pinned)
    else:
        towns = [dict(t) for t in towns_cfg]
    for t in towns:
        x, y = proj.xy(t["lat"], t["lon"])
        t["x"], t["y"] = round(x, 1), round(y, 1)
        t.setdefault("side", "l" if x > proj.w / 2 else "r")

    # route: one point per locality, in the order the board declares
    by_loc: dict[str, list[tuple[float, float]]] = {}
    for p in places:
        by_loc.setdefault(p.get("loc") or p["name"], []).append((p["ax"], p["ay"]))
    route = []
    for name in board.get("route", []):
        pts = by_loc.get(name)
        if not pts:
            warnings.append(f"route step {name!r} matches no place's 'loc'")
            continue
        route.append({"x": round(sum(a for a, _ in pts) / len(pts), 1),
                      "y": round(sum(b for _, b in pts) / len(pts), 1)})

    # photos -> data URIs
    media = board_path.parent / "media"
    img: dict[str, str] = {}
    for p in places:
        photos = p.get("photos") or []
        if not photos:
            warnings.append(f"place {p['n']} ({p['name']}) has no photos")
        for ph in photos:
            f = media / ph["file"]
            if not f.exists():
                raise SystemExit(f"maprot: missing photo {f}")
            img.setdefault(ph["file"], _b64(f))
        for field in ("one", "unique", "desc"):
            if not (p.get(field) or "").strip():
                warnings.append(f"place {p['n']} ({p['name']}) has an empty '{field}'")

    keep = ("n", "name", "loc", "type", "region", "city", "lat", "lon", "approx",
            "maps_query", "one", "unique", "desc", "facts", "near", "photos",
            "sources", "x", "y", "ax", "ay", "fanned")
    data = {
        "vb": {"x": round(-PAD, 1), "y": round(-PAD - 12, 1),
               "w": round(proj.w + PAD * 2, 1), "h": round(proj.h + PAD * 2 + 12, 1)},
        "graticule": _graticule(proj),
        "places": [{k: p[k] for k in keep if k in p} for p in places],
        "towns": [{k: t[k] for k in ("name", "x", "y", "side")} for t in towns],
        "route": route,
        "notes": board.get("notes"),
        "img": img,
    }

    vb = data["vb"]
    html = (TPL / "page.html").read_text()
    repl = {
        "{{TITLE}}": board.get("title", "maprot board"),
        "{{EYEBROW}}": board.get("eyebrow", "Trip board · collected from reels"),
        "{{SUBTITLE}}": board.get("subtitle", ""),
        "{{UPDATED}}": board.get("updated", date.today().isoformat()),
        "{{VIEWBOX}}": f"{vb['x']} {vb['y']} {vb['w']} {vb['h']}",
        "{{MAP_ALT}}": f"Map of {board.get('title','the area')} with {len(places)} pinned places",
        "{{LAND}}": "\n".join(f'            <path class="land" d="{d}"/>' for d in paths),
        "{{NOTES_TITLE}}": (board.get("notes") or {}).get("title", "Planning notes"),
        "{{NOTES_INTRO}}": (board.get("notes") or {}).get("intro", ""),
        "{{FOOTER}}": board.get("footer", DEFAULT_FOOTER),
        "{{STYLE}}": (TPL / "style.css").read_text(),
        "{{APP}}": (TPL / "app.js").read_text(),
        "{{DATA}}": json.dumps(data, ensure_ascii=False, separators=(",", ":")),
    }
    for k, v in repl.items():
        html = html.replace(k, v)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    return out, warnings


DEFAULT_FOOTER = (
    "Coordinates geocoded from OpenStreetMap and cross-checked against each venue&rsquo;s "
    "listed address; where a venue is not in OpenStreetMap the pin is marked approximate and "
    "its map links search by name instead. Photographs are frames from the linked posts, which "
    "belong to their creators. Prices, hours and rankings are whatever the source claimed when "
    "it was posted &mdash; re-check before you book."
)
