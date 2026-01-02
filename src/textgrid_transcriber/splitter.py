from __future__ import annotations

import re
import subprocess
from math import ceil, floor
from pathlib import Path

from textgrid import TextGrid

from textgrid_transcriber.project import Segment


def _sanitize_label(label: str) -> str:
    cleaned = re.sub(r"[^\w\-\.]+", "_", label.strip())
    return cleaned or "tier"


def _run_ffmpeg(args: list[str]) -> None:
    subprocess.run(args, check=True)


def split_audio_with_ffmpeg(
    ffmpeg_path: Path,
    audio_path: Path,
    textgrid_path: Path,
    output_dir: Path,
    progress_cb=None,
) -> tuple[Path, list[Segment]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    wav_path = output_dir / f"{audio_path.stem}.wav"

    _run_ffmpeg(
        [
            str(ffmpeg_path),
            "-y",
            "-i",
            str(audio_path),
            "-acodec",
            "pcm_s16le",
            "-ar",
            "44100",
            str(wav_path),
        ]
    )

    tg = TextGrid()
    tg.read(textgrid_path)

    labeled_intervals_by_tier = []
    for tier in tg.tiers:
        labeled_intervals = [
            interval
            for interval in tier
            if (getattr(interval, "mark", "") or "").strip()
        ]
        labeled_intervals_by_tier.append((tier, labeled_intervals))

    total = sum(len(intervals) for _, intervals in labeled_intervals_by_tier)
    completed = 0
    segments: list[Segment] = []

    for tier, labeled_intervals in labeled_intervals_by_tier:
        tier_dir = output_dir / _sanitize_label(tier.name)
        tier_dir.mkdir(parents=True, exist_ok=True)
        padding = max(1, len(str(len(labeled_intervals))))

        for index, interval in enumerate(labeled_intervals, start=1):
            start_ms = int(floor(interval.minTime * 1000))
            end_ms = int(ceil(interval.maxTime * 1000))
            output_name = f"{tier.name}_{index:0{padding}d}_{start_ms}_{end_ms}.wav"
            output_path = tier_dir / output_name
            mark = (getattr(interval, "mark", "") or "").strip()

            _run_ffmpeg(
                [
                    str(ffmpeg_path),
                    "-y",
                    "-ss",
                    f"{start_ms / 1000:.3f}",
                    "-to",
                    f"{end_ms / 1000:.3f}",
                    "-i",
                    str(wav_path),
                    "-acodec",
                    "pcm_s16le",
                    "-ar",
                    "44100",
                    str(output_path),
                ]
            )
            segments.append(
                Segment(
                    tier=str(tier.name),
                    index=index,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    path=str(output_path),
                    mark=mark,
                    transcript="",
                    asr_generated=False,
                    verified=False,
                )
            )
            completed += 1
            if progress_cb:
                progress_cb(completed, total, output_path)

    return output_dir, segments
