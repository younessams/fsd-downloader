#!/usr/bin/env bash
set -euo pipefail

if [ -x "./.venv/bin/python" ]; then
  ./.venv/bin/python -m app.main "$@"
else
  python -m app.main "$@"
fi
