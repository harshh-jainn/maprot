"""Frame extraction with ffmpeg.

Two jobs:

*   a contact sheet, so a human (or a vision model) can pick good frames in one
    look instead of scrubbing the video;
*   the chosen frames, centre-cropped and scaled for the page.

Fixed-interval sampling beats ffmpeg's scene detection on this material: a
typical reel is cut every second or so, and handheld shake trips the scene
filter constantly, so "scene changes" are neither scenes nor changes.
"""
from __future__ import annotations

import subprocess
from pathlib import Path


class FrameError(RuntimeError):
    pass


def _ff(args: list[str], timeout: int = 180) -> None:
    r = subprocess.run(["ffmpeg", "-v", "error", *args],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise FrameError((r.stderr or "ffmpeg failed").strip().splitlines()[-1])


def duration(video: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(video)],
        capture_output=True, text=True, timeout=60,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        raise FrameError(f"could not read duration of {video}")


def contact_sheet(video: Path, out: Path, cols: int = 4, rows: int = 3,
                  tile_w: int = 300) -> tuple[Path, list[float]]:
    """One tiled image of `cols*rows` evenly spaced frames.

    Returns the path and the timestamp of each tile, so a pick can be turned
    back into an exact -ss value.
    """
    n = cols * rows
    dur = duration(video)
    fps = n / dur
    out.parent.mkdir(parents=True, exist_ok=True)
    _ff(["-i", str(video),
         "-vf", f"fps={fps:.6f},scale={tile_w}:-1,tile={cols}x{rows}",
         "-frames:v", "1", "-q:v", "3", "-y", str(out)])
    stamps = [round(i * dur / n, 2) for i in range(n)]
    return out, stamps


def still(video: Path, at: float, out: Path, width: int = 460,
          aspect: str = "3:4") -> Path:
    """One frame, centre-cropped to `aspect` then scaled to `width`."""
    out.parent.mkdir(parents=True, exist_ok=True)
    if aspect == "3:4":
        crop = "crop=iw:iw*4/3:0:(ih-iw*4/3)/2"
    elif aspect == "1:1":
        crop = "crop=iw:iw:0:(ih-iw)/2"
    else:
        crop = "crop=iw:ih:0:0"
    _ff(["-ss", str(at), "-i", str(video), "-frames:v", "1",
         "-vf", f"{crop},scale={width}:-1", "-q:v", "4", "-y", str(out)])
    return out


def audio(video: Path, out: Path) -> Path:
    """16 kHz mono WAV — what every speech model wants."""
    out.parent.mkdir(parents=True, exist_ok=True)
    _ff(["-i", str(video), "-vn", "-ac", "1", "-ar", "16000",
         "-c:a", "pcm_s16le", "-y", str(out)])
    return out
