from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class DownloadRequest:
    url: str
    playlist_path: tuple[int, ...] = ()
    expected_id: str | None = None


@dataclass(frozen=True)
class DownloadSettings:
    urls: list[str]
    output_dir: Path
    audio_format: str
    audio_quality: int | None
    filename_template: str
    include_playlist: bool
    open_output_dir_when_done: bool
    retry_requests: list[DownloadRequest] = field(default_factory=list)
