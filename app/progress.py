from dataclasses import dataclass
from typing import Any


STAGE_LABELS = {
    "extracting": "Extracting",
    "downloading": "Downloading",
    "merging": "Merging audio and video...",
    "completed": "Completed",
    "error": "Failed",
}


@dataclass
class ProgressState:
    current_index: int = 1
    total: int = 1
    title: str = ""
    stage: str = "extracting"
    percent: float = 0.0
    speed: str = "-"
    eta: str = "-"

    @property
    def episode_text(self) -> str:
        return f"{self.current_index}/{self.total}"

    @property
    def percent_text(self) -> str:
        return f"{self.percent:.1f}%"

    @property
    def stage_label(self) -> str:
        return STAGE_LABELS.get(self.stage, self.stage.title())

    @property
    def completed_count(self) -> int:
        if self.stage == "completed":
            return min(self.current_index, self.total)
        return max(0, min(self.current_index - 1, self.total))


def format_bytes_per_second(value: float | int | None) -> str:
    if not value:
        return "-"
    units = ["B/s", "KiB/s", "MiB/s", "GiB/s"]
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return "-"


def format_eta(seconds: float | int | None) -> str:
    if seconds is None:
        return "-"
    seconds = max(0, int(seconds))
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:d}:{secs:02d}"


def update_item_from_info(data: dict[str, Any], state: ProgressState) -> ProgressState:
    info_dict = data.get("info_dict") or {}
    next_index = int(info_dict.get("playlist_index") or state.current_index or 1)
    if next_index != state.current_index:
        state.current_index = next_index
        state.percent = 0.0
        state.speed = "-"
        state.eta = "-"
        state.stage = "extracting"
    state.title = info_dict.get("title") or state.title
    return state


def progress_from_hook(data: dict[str, Any], state: ProgressState) -> ProgressState:
    update_item_from_info(data, state)
    status = data.get("status")
    if status == "downloading":
        total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
        downloaded = data.get("downloaded_bytes") or 0
        state.percent = min(100.0, (downloaded / total * 100) if total else 0.0)
        state.speed = format_bytes_per_second(data.get("speed"))
        state.eta = format_eta(data.get("eta"))
        state.stage = "downloading"
    elif status == "finished":
        state.percent = 100.0
        state.stage = "merging"
        state.speed = "-"
        state.eta = "-"
    elif status == "error":
        state.stage = "error"
    return state


def postprocessor_from_hook(data: dict[str, Any], state: ProgressState) -> ProgressState:
    update_item_from_info(data, state)
    status = data.get("status")
    if status in {"started", "processing"}:
        state.stage = "merging"
        state.percent = 100.0
        state.speed = "-"
        state.eta = "-"
    elif status == "finished":
        state.stage = "completed"
        state.percent = 100.0
        state.speed = "-"
        state.eta = "-"
    return state
