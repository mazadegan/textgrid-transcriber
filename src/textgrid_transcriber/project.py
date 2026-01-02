from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

PROJECT_VERSION = 1
PROJECT_FILENAME = "textgrid_project.json"


@dataclass
class Segment:
    tier: str
    index: int
    start_ms: int
    end_ms: int
    path: str
    mark: str


@dataclass
class Project:
    version: int
    audio_path: str
    textgrid_path: str
    output_dir: str
    batch_asr: bool
    segments: list[Segment]


def _rel_path(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def _abs_path(path_str: str, base: Path) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return (base / path).resolve()


def save_project(project_path: Path, project: Project) -> None:
    base = project_path.parent
    data = {
        "version": project.version,
        "audio_path": _rel_path(Path(project.audio_path), base),
        "textgrid_path": _rel_path(Path(project.textgrid_path), base),
        "output_dir": _rel_path(Path(project.output_dir), base),
        "batch_asr": project.batch_asr,
        "segments": [
            {
                "tier": segment.tier,
                "index": segment.index,
                "start_ms": segment.start_ms,
                "end_ms": segment.end_ms,
                "path": _rel_path(Path(segment.path), base),
                "mark": segment.mark,
            }
            for segment in project.segments
        ],
    }
    project_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_project(project_path: Path) -> Project:
    base = project_path.parent
    data = json.loads(project_path.read_text(encoding="utf-8"))

    segments = [
        Segment(
            tier=segment["tier"],
            index=segment["index"],
            start_ms=segment["start_ms"],
            end_ms=segment["end_ms"],
            path=str(_abs_path(segment["path"], base)),
            mark=segment.get("mark", ""),
        )
        for segment in data.get("segments", [])
    ]

    return Project(
        version=data.get("version", PROJECT_VERSION),
        audio_path=str(_abs_path(data["audio_path"], base)),
        textgrid_path=str(_abs_path(data["textgrid_path"], base)),
        output_dir=str(_abs_path(data["output_dir"], base)),
        batch_asr=data.get("batch_asr", False),
        segments=segments,
    )
