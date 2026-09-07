# FSD Downloader

FSD Downloader is a simple, polished command-line downloader for videos, playlists, and series links. It uses Python, yt-dlp, FFmpeg, Deno/EJS, and Rich under the hood while keeping the user experience clean and compact.

Follow me on Instagram: **@_fsd_cr**

## Platform Support

- Windows 10/11 x64: supported, including standalone portable builds.
- Android Termux: source mode is supported with the shared Python core.
- GUI/Electron: intentionally not included.

## Features

- Download a single video URL or a playlist/series URL.
- Detect video vs playlist and show playlist title plus episode count.
- Quality choices: `audio`, `360`, `480`, `720`, `1080`, `best`.
- Dynamic yt-dlp format selectors, no hardcoded format IDs.
- MP4 output is preferred for video downloads.
- FFmpeg is used for video/audio merging.
- Deno plus `yt-dlp-ejs` support helps yt-dlp handle modern JavaScript challenge flows.
- Rich progress UI shows current episode, title, selected quality, stage, percentage, speed, ETA, and processed count.
- Fast archive-based resume checks playlist video IDs before full per-video extraction.
- Final counters distinguish completed, skipped, and failed downloads.
- Technical warnings/errors are written to the debug log instead of raw output leaking into the normal UI.

## Counters

- `completed`: newly downloaded/finalized in this run.
- `skipped`: already completed/archive-present.
- `failed`: attempted but unavailable, extraction failed, network failed, or similar.

## Default Locations

Standalone Windows builds save downloads to:

```text
%USERPROFILE%\Downloads\FSD Downloader
```

Example playlist folder:

```text
%USERPROFILE%\Downloads\FSD Downloader\Tom_and_jerry_tales_S2
```

Debug logs are written to:

```text
%LOCALAPPDATA%\FSD Downloader\logs\fsd-downloader-debug.log
```

## Windows Installation

A public GitHub Release has not been created yet. When the repository and release assets exist, the installer command will use this placeholder shape:

```powershell
irm <FSD_DOWNLOADER_INSTALLER_URL> | iex
```

The public one-command installer script is `install-windows.ps1`.

The release installer is designed to install into:

```text
%LOCALAPPDATA%\Programs\FSD Downloader
```

It exposes the command:

```powershell
fsd
```

The standalone Windows build does not require users to install Python, pip, yt-dlp, Rich, FFmpeg, ffprobe, or Deno globally.

## Usage

```powershell
fsd
fsd "https://example.com/video-or-playlist" -q 480
fsd --version
fsd --help
```

## Developer Setup

Windows source/development mode:

```powershell
.\install-dev-windows.ps1
.\run-windows.ps1 --demo
.\run-windows.ps1 "https://example.com/video-or-playlist" -q best
```

Run checks:

```powershell
.\.venv\Scripts\python.exe -m py_compile (Get-ChildItem -Path app -Filter *.py | ForEach-Object { $_.FullName }) .\fsd.py
.\.venv\Scripts\python.exe -m pytest
```

## Build Windows Package

Build a reproducible Windows x64 onedir package and ZIP:

```powershell
.\build-windows.ps1
```

Expected local artifacts:

```text
release\fsd-downloader-v1.0.0-windows-x64.zip
release\SHA256SUMS.txt
```

Build artifacts are intentionally ignored by Git.

## Android Termux

In Termux:

```bash
pkg install git
termux-setup-storage
cd fsd-downloader
chmod +x install-termux.sh run-termux.sh
./install-termux.sh
./run-termux.sh --demo
```

When Termux shared storage is available, downloads are saved under Android shared downloads.

## Uninstall

The Windows release uninstall script removes installed application files and the `fsd` launcher/PATH integration:

```powershell
.\uninstall-windows.ps1
```

Downloaded media is preserved by default. Logs/config are also preserved unless a future command explicitly says otherwise.

## Legal

Only download content that you own, that is licensed for download, or that you otherwise have permission or a legal right to download. FSD Downloader is a wrapper around yt-dlp and does not grant rights to third-party media.

## Version

```text
FSD Downloader 1.0.0
```
