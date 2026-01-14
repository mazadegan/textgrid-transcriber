# TextGrid Transcriber

A small, cross-platform desktop app for splitting audio based on a Praat TextGrid and transcribing
the split segments manually or in conjunction with Google Cloud Speech-to-Text.

## Requirements

- Python 3.12+
- A Google Cloud service account key (Optional, for ASR assistance)

## FFmpeg

Audio conversion and splitting uses FFmpeg via `imageio-ffmpeg`, which downloads
the FFmpeg binary on first run and caches it for later use.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Optional (uv):

```bash
uv venv
source .venv/bin/activate
uv pip install -e .
```

## Run

```bash
textgrid-transcriber
```

Or run the module directly:

```bash
python -m textgrid_transcriber.main
```

## Usage

1. Select an audio file and its matching TextGrid.
2. Click **Split** to generate per-segment audio in a `splits/` folder.
3. Select a segment to play it, edit the transcript, and mark it verified.
4. Use **Set Google Credentials…** before running ASR if you want automatic transcription.

## Packaging (PyInstaller)

Build on each target OS (PyInstaller cannot cross-compile).

macOS:
```bash
scripts/build-macos.sh
```

Linux:
```bash
scripts/build-linux.sh
```

Windows (PowerShell):
```powershell
scripts/build-windows.ps1
```

## Linux desktop entry

After building on Linux, you can install a desktop entry and icon:

```bash
linux/install-linux.sh
```

## Linux runtime dependencies

If the app fails to start with a Qt "xcb" plugin error, install:

```bash
sudo apt update
sudo apt install -y libxcb-cursor0 libxkbcommon-x11-0 libxcb-xinerama0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0
```
