#!/usr/bin/env bash
set -euo pipefail

PYINSTALLER=${PYINSTALLER:-pyinstaller}
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

$PYINSTALLER \
  --clean \
  --noconfirm \
  pyinstaller/textgrid-transcriber.spec
