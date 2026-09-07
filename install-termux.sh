#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO="https://github.com/younessams/fsd-downloader.git"
APP_DIR="$HOME/.local/share/fsd-downloader"
VENV="$APP_DIR/.venv"
LAUNCHER="$PREFIX/bin/fsd"

echo
echo "Installing FSD Downloader..."
echo

echo "[1/5] Installing system dependencies..."
pkg update -y
pkg install -y git python ffmpeg nodejs-lts

echo "[2/5] Preparing Android storage..."
if [ ! -d "$HOME/storage/downloads" ]; then
    echo "Android may ask for storage permission."
    termux-setup-storage || true
fi

echo "[3/5] Downloading FSD Downloader..."
mkdir -p "$(dirname "$APP_DIR")"

if [ -d "$APP_DIR/.git" ]; then
    git -C "$APP_DIR" fetch origin main --depth=1
    git -C "$APP_DIR" reset --hard origin/main
else
    rm -rf "$APP_DIR"
    git clone --depth=1 "$REPO" "$APP_DIR"
fi

echo "[4/5] Installing Python dependencies..."
rm -rf "$VENV"
python -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install -r "$APP_DIR/requirements.txt"

echo "[5/5] Creating fsd command..."
cat > "$LAUNCHER" <<'LAUNCHER'
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

APP_DIR="$HOME/.local/share/fsd-downloader"
PYTHON="$APP_DIR/.venv/bin/python"

if [ ! -x "$PYTHON" ]; then
    echo "FSD Downloader installation is incomplete."
    echo "Run the installer again."
    exit 1
fi

cd "$APP_DIR"
exec "$PYTHON" -m app.main "$@"
LAUNCHER

chmod +x "$LAUNCHER"

echo
echo "Installation complete."
"$LAUNCHER" --version
echo
echo "Run:"
echo "  fsd"
echo "  fsd --help"
echo "  fsd --demo"
