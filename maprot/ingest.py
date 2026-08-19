"""Pull a post's metadata and video with yt-dlp.

The caption is the single most reliable signal for identifying a place: it
usually names the venue outright and often tags its account. Fetch it first and
cheaply, before downloading anything.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


class IngestError(RuntimeError):
    pass


def _run(args: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def have(binary: str) -> bool:
    from shutil import which
    return which(binary) is not None


def post_id(url: str) -> str:
    parts = [p for p in url.split("?")[0].rstrip("/").split("/") if p]
    return parts[-1] if parts else "post"


def metadata(url: str, cookies_from: str | None = None) -> dict:
    """Caption, uploader and duration — no download."""
    args = ["yt-dlp", "-q", "--no-warnings", "--skip-download", "--dump-single-json"]
    if cookies_from:
        args += ["--cookies-from-browser", cookies_from]
    args.append(url)
    r = _run(args)
    if r.returncode != 0:
        err = (r.stderr or "").strip().splitlines()
        hint = ""
        if any("empty media response" in l or "login" in l.lower() for l in err):
            hint = ("\n  This post needs a logged-in session. Re-run with "
                    "--cookies-from chrome (or firefox/safari) if it is yours to read.")
        raise IngestError((err[-1] if err else "yt-dlp failed") + hint)
    d = json.loads(r.stdout)
    return {
        "id": d.get("id") or post_id(url),
        "url": url,
        "uploader": d.get("uploader") or "",
        "handle": d.get("channel") or d.get("uploader_id") or "",
        "caption": d.get("description") or "",
        "duration": d.get("duration") or 0,
        "width": d.get("width"),
        "height": d.get("height"),
    }


def download(url: str, dest: Path, cookies_from: str | None = None) -> Path:
    """Download the video itself. Returns the file path."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    out = dest.with_suffix(".%(ext)s")
    args = ["yt-dlp", "-q", "--no-warnings", "-o", str(out)]
    if cookies_from:
        args += ["--cookies-from-browser", cookies_from]
    args.append(url)
    r = _run(args, timeout=600)
    if r.returncode != 0:
        raise IngestError((r.stderr or "yt-dlp failed").strip().splitlines()[-1])
    hits = sorted(dest.parent.glob(dest.stem + ".*"))
    vids = [h for h in hits if h.suffix.lower() in (".mp4", ".mkv", ".webm", ".mov")]
    if not vids:
        raise IngestError(f"no video file appeared for {url}")
    return vids[0]
