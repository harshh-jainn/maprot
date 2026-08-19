"""The board file: a plain JSON document you can hand-edit or diff."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

SCHEMA = 1


def slugify(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", s.lower()).strip()
    return re.sub(r"[\s_]+", "-", s) or "place"


def new_board(slug: str, title: str, country: str) -> dict:
    return {
        "schema": SCHEMA,
        "slug": slug,
        "title": title,
        "subtitle": "Places worth building an itinerary around.",
        "country": country.upper(),
        "updated": date.today().isoformat(),
        "route": [],
        "reference_cities": 8,
        "places": [],
        "notes": None,
    }


def path_for(slug_or_path: str) -> Path:
    p = Path(slug_or_path)
    if p.suffix == ".json":
        return p
    return Path("boards") / p / "board.json"


def load(slug_or_path: str) -> tuple[dict, Path]:
    p = path_for(slug_or_path)
    if not p.exists():
        raise SystemExit(f"maprot: no board at {p}. Run `maprot init` first.")
    with open(p) as f:
        board = json.load(f)
    if board.get("schema", 1) > SCHEMA:
        raise SystemExit(f"maprot: {p} was written by a newer maprot")
    return board, p


def save(board: dict, p: Path) -> None:
    board["updated"] = date.today().isoformat()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(board, f, indent=2, ensure_ascii=False)
        f.write("\n")


def media_dir(board_path: Path) -> Path:
    d = board_path.parent / "media"
    d.mkdir(parents=True, exist_ok=True)
    return d


def work_dir(board_path: Path) -> Path:
    d = board_path.parent / "work"
    d.mkdir(parents=True, exist_ok=True)
    return d


def next_n(board: dict) -> int:
    return max((p.get("n", 0) for p in board["places"]), default=0) + 1


def find_place(board: dict, needle: str) -> dict | None:
    """Match a place by number, exact name, or slug fragment."""
    if needle.isdigit():
        return next((p for p in board["places"] if p["n"] == int(needle)), None)
    low = needle.lower()
    return next(
        (p for p in board["places"]
         if low == p["name"].lower() or low in slugify(p["name"])),
        None,
    )


EDITORIAL = ("one", "unique", "desc")


def incomplete(place: dict) -> list[str]:
    """Which human-written fields are still empty."""
    return [f for f in EDITORIAL if not (place.get(f) or "").strip()]
