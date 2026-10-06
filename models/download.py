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
    preview_only: bool = False
    playlist_limit: int = 200
    network_attempts: int = 2
    duplicate_policy: str = "skip"
    archive_enabled: bool = False
    embed_metadata: bool = False
    embed_cover: bool = False
    metadata_overrides: dict[str, dict[str, str]] = field(default_factory=dict)
