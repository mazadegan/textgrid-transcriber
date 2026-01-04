#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist/textgrid-transcriber"

if [[ ! -d "$DIST_DIR" ]]; then
  echo "Missing $DIST_DIR. Build first with scripts/build-linux.sh"
  exit 1
fi

APP_DIR="${HOME}/.local/share/applications"
ICON_DIR="${HOME}/.local/share/icons"

mkdir -p "$APP_DIR" "$ICON_DIR"

cp "$ROOT_DIR/linux/textgrid-transcriber.desktop" "$APP_DIR/textgrid-transcriber.desktop"
cp "$ROOT_DIR/assets/icons/app.png" "$ICON_DIR/textgrid-transcriber.png"

echo "Installed desktop entry and icon. You can run: textgrid-transcriber"
