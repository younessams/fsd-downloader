from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def bundled_tool_path(name: str) -> Path | None:
    root = app_root()
    candidates = [
        root / "tools" / name,
        root / "_internal" / "tools" / name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    found = shutil.which(name)
    return Path(found) if found else None


def ffmpeg_location() -> str | None:
    ffmpeg = bundled_tool_path("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    return str(ffmpeg.parent) if ffmpeg else None


def configured_js_runtime() -> dict[str, dict[str, str]] | None:
    """Return a yt-dlp Python API js_runtimes config, if configured."""
    deno = bundled_tool_path("deno.exe" if os.name == "nt" else "deno")
    if deno:
        return {"deno": {"path": str(deno)}}
    deno_path = os.environ.get("FSD_DENO_PATH")
    if deno_path:
        return {"deno": {"path": str(Path(deno_path))}}
    return None
