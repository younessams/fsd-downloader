from dataclasses import dataclass


@dataclass(frozen=True)
class QualityOption:
    key: str
    label: str
    selector: str
    extension: str


QUALITY_OPTIONS = {
    "audio": QualityOption(
        key="audio",
        label="Audio only",
        selector="bestaudio[ext=m4a]/bestaudio/best",
        extension="m4a",
    ),
    "360": QualityOption(
        key="360",
        label="360p",
        selector="bv*[height<=360][ext=mp4]+ba[ext=m4a]/b[height<=360][ext=mp4]/bv*[height<=360]+ba/b[height<=360]/best[height<=360]",
        extension="mp4",
    ),
    "480": QualityOption(
        key="480",
        label="480p",
        selector="bv*[height<=480][ext=mp4]+ba[ext=m4a]/b[height<=480][ext=mp4]/bv*[height<=480]+ba/b[height<=480]/best[height<=480]",
        extension="mp4",
    ),
    "720": QualityOption(
        key="720",
        label="720p",
        selector="bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720][ext=mp4]/bv*[height<=720]+ba/b[height<=720]/best[height<=720]",
        extension="mp4",
    ),
    "1080": QualityOption(
        key="1080",
        label="1080p",
        selector="bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]/bv*[height<=1080]+ba/b[height<=1080]/best[height<=1080]",
        extension="mp4",
    ),
    "best": QualityOption(
        key="best",
        label="Best available",
        selector="bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bestvideo+bestaudio/best",
        extension="mp4",
    ),
}


def get_quality(key: str) -> QualityOption:
    normalized = key.strip().lower().replace("p", "")
    if normalized not in QUALITY_OPTIONS:
        raise ValueError(f"Unsupported quality: {key}")
    return QUALITY_OPTIONS[normalized]


def quality_choices() -> list[QualityOption]:
    return [
        QUALITY_OPTIONS["audio"],
        QUALITY_OPTIONS["360"],
        QUALITY_OPTIONS["480"],
        QUALITY_OPTIONS["720"],
        QUALITY_OPTIONS["1080"],
        QUALITY_OPTIONS["best"],
    ]
