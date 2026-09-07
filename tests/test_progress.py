from app.progress import ProgressState, format_bytes_per_second, format_eta, postprocessor_from_hook, progress_from_hook


def test_progress_state_formatting():
    state = ProgressState(current_index=2, total=5, percent=42.345)

    assert state.episode_text == "2/5"
    assert state.percent_text == "42.3%"


def test_progress_hook_updates_download_state():
    state = ProgressState(current_index=1, total=3)
    progress_from_hook(
        {
            "status": "downloading",
            "downloaded_bytes": 50,
            "total_bytes": 100,
            "speed": 2048,
            "eta": 61,
        },
        state,
    )

    assert state.stage == "downloading"
    assert state.percent == 50
    assert state.speed == "2.0 KiB/s"
    assert state.eta == "1:01"


def test_progress_hook_uses_estimated_total_when_total_is_missing():
    state = ProgressState(current_index=1, total=3)
    progress_from_hook(
        {
            "status": "downloading",
            "downloaded_bytes": 25,
            "total_bytes_estimate": 100,
            "speed": None,
            "eta": None,
        },
        state,
    )

    assert state.percent == 25
    assert state.speed == "-"
    assert state.eta == "-"


def test_progress_hook_resets_current_video_on_new_playlist_item():
    state = ProgressState(current_index=1, total=8, title="One", percent=100, stage="completed")
    progress_from_hook(
        {
            "status": "downloading",
            "downloaded_bytes": 10,
            "total_bytes": 100,
            "info_dict": {"playlist_index": 2, "title": "Two"},
        },
        state,
    )

    assert state.current_index == 2
    assert state.title == "Two"
    assert state.stage == "downloading"
    assert state.percent == 10


def test_progress_hook_finished_sets_merging():
    state = ProgressState()
    progress_from_hook({"status": "finished"}, state)

    assert state.stage == "merging"
    assert state.percent == 100


def test_postprocessor_hook_marks_merging_and_completed():
    state = ProgressState(current_index=3, total=8, title="Video", percent=100)

    postprocessor_from_hook({"status": "started"}, state)
    assert state.stage == "merging"
    assert state.stage_label == "Merging audio and video..."
    assert state.completed_count == 2

    postprocessor_from_hook({"status": "finished"}, state)
    assert state.stage == "completed"
    assert state.completed_count == 3


def test_format_helpers_handle_missing_values():
    assert format_bytes_per_second(None) == "-"
    assert format_eta(None) == "-"
