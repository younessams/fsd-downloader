from __future__ import annotations

import argparse
import logging
from pathlib import Path

from rich.traceback import install as install_rich_traceback

from .config import APP_NAME, app_version
from .downloader import Downloader, FSDDownloaderError, main_exit_code, run_demo
from .quality import get_quality
from .ui import ask_url, banner, choose_quality, console, show_error, show_playlist_info, show_success, show_video_info


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="fsd", description="FSD Downloader CLI")
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {app_version()}")
    parser.add_argument("url", nargs="?", help="Video, playlist, or series URL")
    parser.add_argument("-q", "--quality", choices=["audio", "360", "480", "720", "1080", "best"], help="Download quality")
    parser.add_argument("-o", "--output", type=Path, help="Output directory")
    parser.add_argument("--demo", action="store_true", help="Run a local UI/progress demo without network calls")
    parser.add_argument("--debug-traceback", action="store_true", help="Show Python tracebacks for development")
    return parser.parse_args()


def run() -> int:
    args = parse_args()
    if args.debug_traceback:
        install_rich_traceback(show_locals=False)

    banner()
    try:
        if args.demo:
            summary = run_demo()
            show_success(summary.completed, summary.skipped, summary.output_folder, summary.failed)
            return 0

        url = ask_url(args.url)
        quality = get_quality(args.quality) if args.quality else choose_quality()
        downloader = Downloader(args.output)
        with console.status("[bold cyan]Extracting information...[/bold cyan]", spinner="dots"):
            info = downloader.fetch_info(url)
        if info.is_playlist:
            show_playlist_info(info.title, info.total)
        else:
            show_video_info(info.title)
        summary = downloader.download(url, quality, info)
        show_success(summary.completed, summary.skipped, summary.output_folder, summary.failed)
        return 0
    except KeyboardInterrupt:
        show_error("Cancelled by user.")
        return 130
    except FSDDownloaderError as error:
        show_error(error.user_message, error.hints)
        return main_exit_code(error)
    except Exception as error:
        logging.exception("Unexpected failure")
        show_error("Unexpected error.", ("See fsd-downloader-debug.log for technical details.",))
        return main_exit_code(error)


if __name__ == "__main__":
    raise SystemExit(run())
