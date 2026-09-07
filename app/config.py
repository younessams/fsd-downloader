from pathlib import Path
import os
import sys

APP_NAME = "FSD Downloader"
INSTAGRAM = "@_fsd_cr"
LOG_FILE = "fsd-downloader-debug.log"


def app_version() -> str:
    from . import __version__

    return __version__


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def local_app_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / APP_NAME
    return Path.home() / f".{APP_NAME.replace(' ', '-').lower()}"


def default_log_dir() -> Path:
    return local_app_data_dir() / "logs"


def default_download_dir() -> Path:
    """Return a sensible default download folder for Windows and Termux."""
    shared = Path.home() / "storage" / "downloads"
    if shared.exists():
        return shared / "FSD Downloader"
    if is_frozen() and os.name == "nt":
        return Path.home() / "Downloads" / "FSD Downloader"
    return Path.cwd() / "downloads"
