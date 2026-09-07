from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .config import LOG_FILE, default_download_dir, default_log_dir
from .progress import ProgressState, postprocessor_from_hook, progress_from_hook
from .quality import QualityOption
from .runtime import configured_js_runtime, ffmpeg_location

try:
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import sanitize_filename as yt_sanitize_filename
except ImportError:  # pragma: no cover - handled at runtime
    YoutubeDL = None
    yt_sanitize_filename = None


class FSDDownloaderError(Exception):
    user_message = "Something went wrong."
    hints: tuple[str, ...] = ()


class InvalidURLError(FSDDownloaderError):
    user_message = "Invalid URL."
    hints = ("Check the link and try again.",)


class UnavailableVideoError(FSDDownloaderError):
    user_message = "This video or playlist is unavailable."
    hints = ("It may be private, removed, region-blocked, or temporarily unavailable.",)


class MissingFFmpegError(FSDDownloaderError):
    user_message = "FFmpeg is missing."
    hints = ("Install FFmpeg and make sure the ffmpeg command is available on PATH.",)


class MissingYtDlpError(FSDDownloaderError):
    user_message = "yt-dlp is not installed."
    hints = ("Run the installer script or install requirements with python -m pip install -r requirements.txt.",)


class NetworkFailureError(FSDDownloaderError):
    user_message = "Network failure."
    hints = ("Check your internet connection and try again.",)


class UnsupportedQualityError(FSDDownloaderError):
    user_message = "The selected quality is not available for this URL."
    hints = ("Try Best available or a lower resolution.",)


@dataclass
class MediaInfo:
    title: str
    is_playlist: bool
    total: int
    entries: list[dict[str, Any]]


@dataclass
class DownloadSummary:
    completed: int
    skipped: int
    failed: int
    output_folder: Path

    @property
    def has_failures(self) -> bool:
        return self.failed > 0


@dataclass
class PlaylistPreflight:
    total: int
    skipped: int
    pending: list[tuple[int, dict[str, Any]]]

    @property
    def need_download(self) -> int:
        return len(self.pending)


class YtDlpLogger:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def debug(self, message: str) -> None:
        logging.debug("yt-dlp: %s", message)
        self.messages.append(("debug", message))

    def warning(self, message: str) -> None:
        logging.warning("yt-dlp: %s", message)
        self.messages.append(("warning", message))

    def error(self, message: str) -> None:
        logging.error("yt-dlp: %s", message)
        self.messages.append(("error", message))


def configure_logging(base_dir: Path | None = None) -> Path:
    log_dir = base_dir or default_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / LOG_FILE
    logging.basicConfig(
        filename=log_path,
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return log_path


def sanitize_filename(name: str, fallback: str = "download") -> str:
    if yt_sanitize_filename:
        cleaned = yt_sanitize_filename(name, restricted=True)
    else:
        cleaned = "".join(char for char in name if char.isalnum() or char in " ._-").strip()
    cleaned = cleaned.strip(" ._-")
    return cleaned[:180] or fallback


def is_probably_url(value: str) -> bool:
    return value.startswith(("http://", "https://"))


def require_dependencies(quality: QualityOption) -> None:
    if YoutubeDL is None:
        raise MissingYtDlpError()
    if quality.key != "audio" and not ffmpeg_location() and shutil.which("ffmpeg") is None:
        raise MissingFFmpegError()


def build_output_template(root: Path, collection_name: str | None, extension: str) -> str:
    folder = root / sanitize_filename(collection_name or "Single Videos", "Single Videos")
    return str(folder / f"%(title).180B.%(ext)s")


def entry_video_id(entry: dict[str, Any]) -> str | None:
    video_id = entry.get("id") or entry.get("display_id")
    return str(video_id) if video_id else None


def item_url(entry: dict[str, Any], fallback_url: str) -> str:
    video_id = entry_video_id(entry)
    extractor_key = str(entry.get("ie_key") or entry.get("extractor_key") or "").lower()
    if video_id and "youtube" in extractor_key:
        return f"https://www.youtube.com/watch?v={video_id}"
    url = entry.get("webpage_url") or entry.get("url") or fallback_url
    if isinstance(url, str) and url.startswith(("http://", "https://")):
        return url
    if extractor_key and url:
        return f"{extractor_key}:{url}"
    return fallback_url


def normalize_info(info: dict[str, Any]) -> MediaInfo:
    entries = [entry for entry in info.get("entries") or [] if entry]
    is_playlist = bool(entries)
    if is_playlist:
        title = info.get("title") or "Playlist"
        total = int(info.get("playlist_count") or len(entries))
        return MediaInfo(title=title, is_playlist=True, total=total, entries=entries)
    return MediaInfo(title=info.get("title") or "Video", is_playlist=False, total=1, entries=[info])


def classify_download_error(error: Exception) -> FSDDownloaderError:
    text = str(error).lower()
    logging.exception("Download failed")
    if "unsupported url" in text or "not a valid url" in text:
        return InvalidURLError()
    if "requested format is not available" in text or "format is not available" in text:
        return UnsupportedQualityError()
    if any(term in text for term in ("unavailable", "private", "removed", "copyright", "blocked")):
        return UnavailableVideoError()
    if any(term in text for term in ("network", "timed out", "connection", "temporary failure")):
        return NetworkFailureError()
    wrapped = FSDDownloaderError(str(error))
    wrapped.user_message = "Download failed."
    wrapped.hints = ("See fsd-downloader-debug.log for technical details.",)
    return wrapped


def base_ydl_options(quality: QualityOption, output_template: str, output_folder: Path) -> dict[str, Any]:
    options: dict[str, Any] = {
        "format": quality.selector,
        "outtmpl": output_template,
        "continuedl": True,
        "nooverwrites": True,
        "ignoreerrors": False,
        "retries": 5,
        "fragment_retries": 5,
        "merge_output_format": "mp4",
        "download_archive": str(output_folder / ".fsd-downloader-archive.txt"),
        "quiet": True,
        "noprogress": True,
        "logger": YtDlpLogger(),
    }
    js_runtime = configured_js_runtime()
    if js_runtime:
        options["js_runtimes"] = js_runtime
    location = ffmpeg_location()
    if location:
        options["ffmpeg_location"] = location
    return options


class Downloader:
    def __init__(self, download_dir: Path | None = None) -> None:
        self.download_dir = download_dir or default_download_dir()
        self.download_dir.mkdir(parents=True, exist_ok=True)
        configure_logging()

    def fetch_info(self, url: str) -> MediaInfo:
        if not is_probably_url(url):
            raise InvalidURLError()
        if YoutubeDL is None:
            raise MissingYtDlpError()
        try:
            with YoutubeDL({"quiet": True, "extract_flat": "in_playlist", "skip_download": True, "logger": YtDlpLogger()}) as ydl:
                return normalize_info(ydl.extract_info(url, download=False))
        except Exception as error:
            raise classify_download_error(error) from None

    def download(self, url: str, quality: QualityOption, info: MediaInfo) -> DownloadSummary:
        require_dependencies(quality)
        output_template = build_output_template(
            self.download_dir,
            info.title if info.is_playlist else "Single Videos",
            quality.extension,
        )
        output_folder = Path(output_template).parent
        output_folder.mkdir(parents=True, exist_ok=True)
        state = ProgressState(total=info.total, title=info.title)
        completed = 0
        skipped = 0
        failed = 0
        entries = list(enumerate(info.entries, start=1))
        if info.is_playlist:
            preflight = playlist_preflight(info.entries, output_folder)
            skipped = preflight.skipped
            entries = preflight.pending

        current_progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.fields[stage]}[/bold cyan]", justify="left"),
            BarColumn(),
            TextColumn("{task.percentage:>5.1f}%"),
            expand=True,
        )
        current_task_id = current_progress.add_task("current", total=100, stage=state.stage_label)

        overall_progress = Progress(
            TextColumn("[dim]Processed[/dim]"),
            BarColumn(),
            TextColumn("[dim]{task.completed:.0f}/{task.total:.0f}[/dim]"),
            expand=True,
        )
        overall_task_id = overall_progress.add_task("overall", total=info.total, completed=0)

        def render_progress() -> Panel:
            details = Table.grid(expand=True)
            details.add_column(ratio=1)
            details.add_column(ratio=1)
            details.add_row("[bold]Playlist[/bold]", info.title if info.is_playlist else "Single video")
            details.add_row("[bold]Episode[/bold]", state.episode_text)
            details.add_row("[bold]Quality[/bold]", quality.label)
            details.add_row("[bold]Speed[/bold]", state.speed)
            details.add_row("[bold]ETA[/bold]", state.eta)

            title = state.title or "Preparing download..."
            return Panel(
                Group(
                    details,
                    "",
                    f"[bold white]{title}[/bold white]",
                    current_progress,
                    overall_progress,
                ),
                title="FSD Downloader",
                border_style="cyan",
            )

        def refresh_tasks() -> None:
            current_progress.update(current_task_id, completed=state.percent, stage=state.stage_label)
            overall_progress.update(overall_task_id, completed=completed + skipped + failed)

        def render_preflight() -> Panel:
            details = Table.grid(expand=True)
            details.add_column(ratio=1)
            details.add_column(ratio=1)
            details.add_row("[bold]Checking playlist[/bold]", info.title)
            details.add_row("[bold]Episodes[/bold]", str(info.total))
            details.add_row("[bold]Already downloaded[/bold]", str(skipped))
            details.add_row("[bold]Need download[/bold]", str(len(entries)))
            return Panel(details, title="FSD Downloader", border_style="cyan")

        live_display: dict[str, Live] = {}

        def hook(data: dict[str, Any]) -> None:
            progress_from_hook(data, state)
            refresh_tasks()
            if "live" in live_display:
                live_display["live"].update(render_progress())

        def postprocessor_hook(data: dict[str, Any]) -> None:
            postprocessor_from_hook(data, state)
            refresh_tasks()
            if "live" in live_display:
                live_display["live"].update(render_progress())

        options = base_ydl_options(quality, output_template, output_folder)
        options["progress_hooks"] = [hook]
        options["postprocessor_hooks"] = [postprocessor_hook]
        try:
            refresh_tasks()
            initial_view = render_preflight() if info.is_playlist else render_progress()
            with Live(initial_view, refresh_per_second=8) as live:
                live_display["live"] = live
                if info.is_playlist:
                    live.update(render_preflight())
                for index, entry in entries:
                    state.current_index = index
                    state.title = entry.get("title") or f"Episode {index}"
                    state.stage = "extracting"
                    state.percent = 0.0
                    state.speed = "-"
                    state.eta = "-"
                    refresh_tasks()
                    live.update(render_progress())

                    before_files = set(output_folder.glob(f"*.{quality.extension}"))
                    before_archive = archive_entries(output_folder)
                    try:
                        with YoutubeDL(options) as ydl:
                            result = ydl.download([item_url(entry, url)])
                    except Exception as item_error:
                        failed += 1
                        state.stage = "error"
                        state.percent = 0.0
                        state.speed = "-"
                        state.eta = "-"
                        logging.exception("Failed playlist item %s: %s", index, state.title)
                        refresh_tasks()
                        live.update(render_progress())
                        continue

                    after_files = set(output_folder.glob(f"*.{quality.extension}"))
                    after_archive = archive_entries(output_folder)
                    if result != 0:
                        failed += 1
                        state.stage = "error"
                    elif len(after_files - before_files) > 0:
                        completed += 1
                        state.stage = "completed"
                        state.percent = 100.0
                    elif len(after_archive) > len(before_archive):
                        completed += 1
                        state.stage = "completed"
                        state.percent = 100.0
                    else:
                        skipped += 1
                        state.stage = "completed"
                        state.percent = 100.0
                    state.speed = "-"
                    state.eta = "-"
                    refresh_tasks()
                    live.update(render_progress())
        except Exception as error:
            raise classify_download_error(error) from None

        return DownloadSummary(completed=completed, skipped=skipped, failed=failed, output_folder=output_folder)


def archive_entries(output_folder: Path) -> set[str]:
    archive = output_folder / ".fsd-downloader-archive.txt"
    if not archive.exists():
        return set()
    return {line.strip() for line in archive.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()}


def archive_video_ids(output_folder: Path) -> set[str]:
    ids = set()
    for line in archive_entries(output_folder):
        parts = line.split()
        if parts:
            ids.add(parts[-1])
    return ids


def playlist_preflight(entries: list[dict[str, Any]], output_folder: Path) -> PlaylistPreflight:
    archived_ids = archive_video_ids(output_folder)
    pending = []
    skipped = 0
    for index, entry in enumerate(entries, start=1):
        video_id = entry_video_id(entry)
        if video_id and video_id in archived_ids:
            skipped += 1
        else:
            pending.append((index, entry))
    return PlaylistPreflight(total=len(entries), skipped=skipped, pending=pending)


def run_demo() -> DownloadSummary:
    import time

    root = default_download_dir() / "Demo Playlist"
    root.mkdir(parents=True, exist_ok=True)
    state = ProgressState(total=3, title="SMALL X - Example Video Title")
    quality_label = "480p"
    current_progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.fields[stage]}[/bold cyan]"),
        BarColumn(),
        TextColumn("{task.percentage:>5.1f}%"),
        expand=True,
    )
    current_task_id = current_progress.add_task("current", total=100, stage=state.stage_label)
    overall_progress = Progress(
        TextColumn("[dim]Processed[/dim]"),
        BarColumn(),
        TextColumn("[dim]{task.completed:.0f}/{task.total:.0f}[/dim]"),
        expand=True,
    )
    overall_task_id = overall_progress.add_task("overall", total=3, completed=0)

    def render_demo() -> Panel:
        details = Table.grid(expand=True)
        details.add_column(ratio=1)
        details.add_column(ratio=1)
        details.add_row("[bold]Playlist[/bold]", "Demo Playlist")
        details.add_row("[bold]Episode[/bold]", state.episode_text)
        details.add_row("[bold]Quality[/bold]", quality_label)
        details.add_row("[bold]Speed[/bold]", state.speed)
        details.add_row("[bold]ETA[/bold]", state.eta)
        return Panel(
            Group(
                details,
                "",
                f"[bold white]{state.title}[/bold white]",
                current_progress,
                overall_progress,
            ),
            title="FSD Downloader",
            border_style="cyan",
        )

    def refresh_demo() -> None:
        current_progress.update(current_task_id, completed=state.percent, stage=state.stage_label)
        overall_progress.update(overall_task_id, completed=state.completed_count)

    with Live(render_demo(), refresh_per_second=12) as live:
        for episode in range(1, 4):
            state.current_index = episode
            state.title = f"SMALL X - Demo Video {episode}"
            state.stage = "extracting"
            state.percent = 0
            state.speed = "-"
            state.eta = "-"
            refresh_demo()
            live.update(render_demo())
            time.sleep(0.15)
            for percent in range(0, 101, 10):
                state.stage = "downloading"
                state.percent = percent
                state.speed = "2.4 MiB/s"
                state.eta = "0:18" if percent < 100 else "-"
                refresh_demo()
                live.update(render_demo())
                time.sleep(0.04)
            state.stage = "merging"
            state.percent = 100
            state.speed = "-"
            state.eta = "-"
            refresh_demo()
            live.update(render_demo())
            time.sleep(0.15)
            state.stage = "completed"
            refresh_demo()
            live.update(render_demo())
            time.sleep(0.08)
        time.sleep(0.15)
    return DownloadSummary(completed=3, skipped=0, failed=0, output_folder=root)


def main_exit_code(error: Exception) -> int:
    if isinstance(error, FSDDownloaderError):
        return 2
    return 1
