from app.runtime import configured_js_runtime
from app.runtime import ffmpeg_location


def test_configured_js_runtime_uses_deno_path(monkeypatch):
    monkeypatch.setenv("FSD_DENO_PATH", r"C:\Tools\deno.exe")

    assert configured_js_runtime() == {"deno": {"path": r"C:\Tools\deno.exe"}}


def test_configured_js_runtime_is_optional(monkeypatch):
    monkeypatch.delenv("FSD_DENO_PATH", raising=False)

    assert configured_js_runtime() is None


def test_bundled_tool_paths_are_used_in_frozen_mode(tmp_path, monkeypatch):
    tools = tmp_path / "tools"
    tools.mkdir()
    deno = tools / "deno.exe"
    ffmpeg = tools / "ffmpeg.exe"
    deno.write_text("deno")
    ffmpeg.write_text("ffmpeg")
    exe = tmp_path / "fsd.exe"
    exe.write_text("exe")

    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.setattr("sys.executable", str(exe))
    monkeypatch.delenv("FSD_DENO_PATH", raising=False)

    assert configured_js_runtime() == {"deno": {"path": str(deno)}}
    assert ffmpeg_location() == str(tools)
