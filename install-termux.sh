#!/usr/bin/env bash
set -euo pipefail

echo "Installing FSD Downloader for Termux..."
pkg update
pkg install -y python ffmpeg

if [ ! -d "$HOME/storage" ]; then
  echo "Grant storage access when prompted:"
  termux-setup-storage || true
fi

python -m venv .venv || {
  echo "venv is unavailable, installing requirements for the current Python instead."
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
  echo "Ready. Run with: ./run-termux.sh"
  exit 0
}

./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt
chmod +x run-termux.sh

echo
echo "Ready. Run with:"
echo "  ./run-termux.sh"
echo "  ./run-termux.sh 'https://example.com/video' -q 720"
