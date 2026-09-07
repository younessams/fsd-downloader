from pathlib import Path

from app.ui import show_success


def test_success_panel_reports_failed_counter(capsys):
    show_success(42, 3, Path("downloads/Playlist"), failed=12)

    output = capsys.readouterr().out
    assert "Completed with errors" in output
    assert "Completed files:" in output
    assert "42" in output
    assert "Skipped files:" in output
    assert "3" in output
    assert "Failed files:" in output
    assert "12" in output
    assert "Follow me on Instagram" in output
    assert "@_fsd_cr" in output


def test_success_panel_reports_all_failed_state(capsys):
    show_success(0, 0, Path("downloads/Playlist"), failed=57)

    output = capsys.readouterr().out
    assert "Downloads failed" in output
    assert "Failed files:" in output
    assert "57" in output
