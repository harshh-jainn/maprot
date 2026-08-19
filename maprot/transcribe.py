"""Optional speech-to-text.

Deliberately optional. In testing, captions and frames identified places
correctly every time, while transcription alone was wrong in instructive ways:
it heard a restaurant called "Café Chill" as "Cafe Chin", put it in the wrong
city, and hallucinated a repeating loop over the trailing music. Useful for
narrated detail; not a source of truth for names or places.

Backends, in preference order:
  mlx-whisper      Apple Silicon, fastest here
  faster-whisper   cross-platform CPU/CUDA
"""
from __future__ import annotations

import platform
import subprocess
from pathlib import Path


def available() -> str | None:
    """Which backend we can actually use, if any."""
    from importlib.util import find_spec
    if platform.machine() == "arm64" and platform.system() == "Darwin":
        if find_spec("mlx_whisper"):
            return "mlx"
    if find_spec("faster_whisper"):
        return "faster"
    from shutil import which
    if which("uvx"):
        return "uvx-mlx" if platform.machine() == "arm64" else None
    return None


def install_hint() -> str:
    if platform.machine() == "arm64" and platform.system() == "Darwin":
        return "pip install 'maprot[mlx]'   (or: uv tool install mlx-whisper)"
    return "pip install 'maprot[whisper]'"


def run(wav: Path, model: str = "large-v3-turbo", language: str | None = None) -> str:
    """Return plain text, or '' if no backend is installed."""
    backend = available()
    if backend is None:
        print(f"  no transcription backend; skipping. Install with: {install_hint()}")
        return ""

    if backend == "mlx":
        import mlx_whisper
        res = mlx_whisper.transcribe(
            str(wav), path_or_hf_repo=f"mlx-community/whisper-{model}",
            language=language)
        return (res.get("text") or "").strip()

    if backend == "faster":
        from faster_whisper import WhisperModel
        m = WhisperModel(model, device="auto", compute_type="auto")
        segs, _ = m.transcribe(str(wav), language=language)
        return " ".join(s.text.strip() for s in segs).strip()

    if backend == "uvx-mlx":
        args = ["uvx", "--from", "mlx-whisper", "mlx_whisper", str(wav),
                "--model", f"mlx-community/whisper-{model}",
                "--output-format", "txt", "--output-dir", str(wav.parent)]
        if language:
            args += ["--language", language]
        r = subprocess.run(args, capture_output=True, text=True, timeout=1800)
        txt = wav.with_suffix(".txt")
        if r.returncode == 0 and txt.exists():
            return txt.read_text().strip()
        print("  transcription via uvx failed; skipping")
    return ""
