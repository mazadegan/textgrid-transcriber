#!/usr/bin/env bash
set -euo pipefail

PYINSTALLER=${PYINSTALLER:-pyinstaller}
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

$PYINSTALLER \
  --clean \
  --noconfirm \
  --distpath dist \
  --workpath build \
  pyinstaller/textgrid-transcriber.spec
