from pathlib import Path

import imageio_ffmpeg


def get_ffmpeg_path() -> Path:
    """Return the bundled ffmpeg executable path from imageio-ffmpeg."""
    return Path(imageio_ffmpeg.get_ffmpeg_exe())
