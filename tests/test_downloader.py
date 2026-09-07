from pathlib import Path

import pytest

from app.downloader import (
    DownloadSummary,
    Downloader,
    InvalidURLError,
    MissingFFmpegError,
    YtDlpLogger,
    archive_video_ids,
    build_output_template,
    classify_download_error,
    entry_video_id,
    item_url,
    normalize_info,
    playlist_preflight,
    require_dependencies,
    sanitize_filename,
)
from app.downloader import MediaInfo
from app.quality import get_quality


def test_filename_sanitization_removes_unsafe_characters():
    result = sanitize_filename('bad:/\\*?"<>| name')

    assert result
    assert ":" not in result
    assert "\\" not in result
    assert "/" not in result


def test_playlist_handling_counts_entries():
    media = normalize_info(
        {
            "title": "My Series",
            "entries": [{"title": "Episode 1"}, {"title": "Episode 2"}],
        }
    )

    assert media.is_playlist is True
    assert media.title == "My Series"
    assert media.total == 2


def test_single_video_handling():
    media = normalize_info({"title": "Only One"})

    assert media.is_playlist is False
    assert media.total == 1
    assert media.entries[0]["title"] == "Only One"


def test_output_template_uses_organized_folder():
    template = build_output_template(Path("downloads"), "A Playlist", "mp4")

    assert "A_Playlist" in template or "A Playlist" in template
    assert "%(title).180B.%(ext)s" in template


def test_error_classification_for_invalid_url():
    error = classify_download_error(Exception("Unsupported URL: nope"))

    assert isinstance(error, InvalidURLError)


def test_missing_ffmpeg_error_for_video_quality(monkeypatch):
    monkeypatch.setattr("app.downloader.YoutubeDL", object())
    monkeypatch.setattr("app.downloader.shutil.which", lambda _: None)

    with pytest.raises(MissingFFmpegError):
        require_dependencies(get_quality("720"))


def test_item_url_builds_youtube_watch_url_when_available():
    entry = {"id": "abc123", "url": "https://example.com/video"}

    assert item_url(entry, "https://fallback.test") == "https://example.com/video"


def test_item_url_prefers_youtube_id_for_flat_playlist_entry():
    entry = {"id": "abc123", "url": "abc123", "ie_key": "Youtube"}

    assert item_url(entry, "https://fallback.test") == "https://www.youtube.com/watch?v=abc123"


def test_yt_dlp_logger_routes_messages_without_printing(capsys):
    logger = YtDlpLogger()

    logger.warning("raw warning")
    logger.error("raw error")
    logger.debug("raw debug")

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert ("warning", "raw warning") in logger.messages


def test_mixed_playlist_accounting_without_network(tmp_path, monkeypatch):
    output_folder = tmp_path / "Playlist"
    output_folder.mkdir()
    (output_folder / ".fsd-downloader-archive.txt").write_text("youtube archived-id\n", encoding="utf-8")
    calls = []
    media = MediaInfo(
        title="Playlist",
        is_playlist=True,
        total=5,
        entries=[
            {"id": "success-id", "title": "Successful", "webpage_url": "https://video.test/success"},
            {"id": "archived-id", "title": "Archived", "webpage_url": "https://video.test/archived"},
            {"id": "unavailable-id", "title": "Unavailable", "webpage_url": "https://video.test/unavailable"},
            {"id": "extract-id", "title": "Extraction", "webpage_url": "https://video.test/extractfail"},
            {"id": "network-id", "title": "Network", "webpage_url": "https://video.test/networkfail"},
        ],
    )

    class FakeYoutubeDL:
        def __init__(self, options):
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def download(self, urls):
            url = urls[0]
            calls.append(url)
            if url.endswith("success"):
                (tmp_path / "Playlist" / "Successful.mp4").write_text("ok")
                return 0
            if url.endswith("unavailable"):
                return 1
            if url.endswith("extractfail"):
                raise Exception("Unable to extract data")
            if url.endswith("networkfail"):
                raise Exception("Connection timed out")
            return 1

    monkeypatch.setattr("app.downloader.YoutubeDL", FakeYoutubeDL)
    monkeypatch.setattr("app.downloader.shutil.which", lambda _: "ffmpeg.exe")

    summary = Downloader(tmp_path).download("https://playlist.test", get_quality("480"), media)

    assert summary.completed == 1
    assert summary.skipped == 1
    assert summary.failed == 3
    assert summary.has_failures is True
    assert len(calls) == 4
    assert "https://video.test/archived" not in calls


def test_all_items_failed_playlist_accounting_without_network(tmp_path, monkeypatch):
    media = MediaInfo(
        title="Broken Playlist",
        is_playlist=True,
        total=2,
        entries=[
            {"title": "One", "webpage_url": "https://video.test/one"},
            {"title": "Two", "webpage_url": "https://video.test/two"},
        ],
    )

    class FakeYoutubeDL:
        def __init__(self, options):
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def download(self, urls):
            return 1

    monkeypatch.setattr("app.downloader.YoutubeDL", FakeYoutubeDL)
    monkeypatch.setattr("app.downloader.shutil.which", lambda _: "ffmpeg.exe")

    summary = Downloader(tmp_path).download("https://playlist.test", get_quality("480"), media)

    assert isinstance(summary, DownloadSummary)
    assert summary.completed == 0
    assert summary.skipped == 0
    assert summary.failed == 2


def test_archive_video_ids_preserves_existing_archive_format(tmp_path):
    output_folder = tmp_path / "Playlist"
    output_folder.mkdir()
    (output_folder / ".fsd-downloader-archive.txt").write_text(
        "youtube first-id\nvimeo second-id\n",
        encoding="utf-8",
    )

    assert archive_video_ids(output_folder) == {"first-id", "second-id"}


def test_large_playlist_preflight_skips_56_of_57_by_id(tmp_path):
    output_folder = tmp_path / "Playlist"
    output_folder.mkdir()
    entries = [{"id": f"id-{index}", "title": f"Video {index}"} for index in range(57)]
    archived = "\n".join(f"youtube id-{index}" for index in range(56))
    (output_folder / ".fsd-downloader-archive.txt").write_text(archived, encoding="utf-8")

    preflight = playlist_preflight(entries, output_folder)

    assert preflight.total == 57
    assert preflight.skipped == 56
    assert preflight.need_download == 1
    assert preflight.pending[0][0] == 57
    assert entry_video_id(preflight.pending[0][1]) == "id-56"


def test_archived_entries_do_not_invoke_full_download_and_missing_entry_is_processed(tmp_path, monkeypatch):
    output_folder = tmp_path / "Big_Playlist"
    output_folder.mkdir()
    entries = [{"id": f"id-{index}", "title": f"Video {index}", "webpage_url": f"https://video.test/{index}"} for index in range(57)]
    (output_folder / ".fsd-downloader-archive.txt").write_text(
        "\n".join(f"youtube id-{index}" for index in range(56)),
        encoding="utf-8",
    )
    calls = []
    media = MediaInfo(title="Big Playlist", is_playlist=True, total=57, entries=entries)

    class FakeYoutubeDL:
        def __init__(self, options):
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def download(self, urls):
            calls.extend(urls)
            (output_folder / "Video 56.mp4").write_text("ok")
            return 0

    monkeypatch.setattr("app.downloader.YoutubeDL", FakeYoutubeDL)
    monkeypatch.setattr("app.downloader.shutil.which", lambda _: "ffmpeg.exe")

    summary = Downloader(tmp_path).download("https://playlist.test", get_quality("480"), media)

    assert summary.completed == 1
    assert summary.skipped == 56
    assert summary.failed == 0
    assert calls == ["https://video.test/56"]


def test_failed_previous_item_is_retried_when_not_in_archive(tmp_path, monkeypatch):
    output_folder = tmp_path / "Big_Playlist"
    output_folder.mkdir()
    entries = [{"id": f"id-{index}", "title": f"Video {index}", "webpage_url": f"https://video.test/{index}"} for index in range(57)]
    (output_folder / ".fsd-downloader-archive.txt").write_text(
        "\n".join(f"youtube id-{index}" for index in range(56)),
        encoding="utf-8",
    )
    calls = []
    media = MediaInfo(title="Big Playlist", is_playlist=True, total=57, entries=entries)

    class FakeYoutubeDL:
        def __init__(self, options):
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def download(self, urls):
            calls.extend(urls)
            return 1

    monkeypatch.setattr("app.downloader.YoutubeDL", FakeYoutubeDL)
    monkeypatch.setattr("app.downloader.shutil.which", lambda _: "ffmpeg.exe")

    summary = Downloader(tmp_path).download("https://playlist.test", get_quality("480"), media)

    assert summary.completed == 0
    assert summary.skipped == 56
    assert summary.failed == 1
    assert calls == ["https://video.test/56"]


def test_title_change_with_same_video_id_still_skips(tmp_path):
    output_folder = tmp_path / "Playlist"
    output_folder.mkdir()
    (output_folder / ".fsd-downloader-archive.txt").write_text("youtube stable-id\n", encoding="utf-8")

    preflight = playlist_preflight([{"id": "stable-id", "title": "New Title"}], output_folder)

    assert preflight.skipped == 1
    assert preflight.pending == []


def test_same_title_with_different_ids_does_not_skip(tmp_path):
    output_folder = tmp_path / "Playlist"
    output_folder.mkdir()
    (output_folder / ".fsd-downloader-archive.txt").write_text("youtube first-id\n", encoding="utf-8")

    preflight = playlist_preflight([{"id": "second-id", "title": "Same Title"}], output_folder)

    assert preflight.skipped == 0
    assert preflight.need_download == 1
