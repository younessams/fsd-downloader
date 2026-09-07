from app.quality import get_quality, quality_choices


def test_quality_selector_generation_is_dynamic_and_prefers_mp4():
    option = get_quality("720p")

    assert "height<=720" in option.selector
    assert "ext=mp4" in option.selector
    assert "+" in option.selector
    assert option.extension == "mp4"


def test_audio_selector_uses_best_audio():
    option = get_quality("audio")

    assert "bestaudio" in option.selector
    assert option.extension == "m4a"


def test_quality_choices_are_ordered_for_prompt():
    assert [option.key for option in quality_choices()] == ["audio", "360", "480", "720", "1080", "best"]
