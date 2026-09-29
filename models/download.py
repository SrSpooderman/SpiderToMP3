from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DownloadSettings:
    urls: list[str]
    output_dir: Path
    audio_format: str
    audio_quality: int
    filename_template: str
    include_playlist: bool
    open_output_dir_when_done: bool
