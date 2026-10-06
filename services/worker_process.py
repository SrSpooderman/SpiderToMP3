from __future__ import annotations

import json
import os
import socket
import sys
import traceback
from pathlib import Path
from typing import Any

from models import DownloadRequest, DownloadSettings
from services.download_service import DownloadCancelled, DownloadService


def settings_to_payload(settings: DownloadSettings) -> dict[str, Any]:
    return {
        "urls": settings.urls,
        "output_dir": str(settings.output_dir),
        "audio_format": settings.audio_format,
        "audio_quality": settings.audio_quality,
        "filename_template": settings.filename_template,
        "include_playlist": settings.include_playlist,
        "open_output_dir_when_done": settings.open_output_dir_when_done,
        "retry_requests": [
            {"url": request.url, "playlist_path": list(request.playlist_path), "expected_id": request.expected_id}
            for request in settings.retry_requests
        ],
        "preview_only": settings.preview_only,
        "playlist_limit": settings.playlist_limit,
        "network_attempts": settings.network_attempts,
        "duplicate_policy": settings.duplicate_policy,
        "archive_enabled": settings.archive_enabled,
        "embed_metadata": settings.embed_metadata,
        "embed_cover": settings.embed_cover,
        "metadata_overrides": settings.metadata_overrides,
    }


def settings_from_payload(payload: dict[str, Any]) -> DownloadSettings:
    return DownloadSettings(
        urls=payload["urls"],
        output_dir=Path(payload["output_dir"]),
        audio_format=payload["audio_format"],
        audio_quality=payload["audio_quality"],
        filename_template=payload["filename_template"],
        include_playlist=payload["include_playlist"],
        open_output_dir_when_done=payload["open_output_dir_when_done"],
        retry_requests=[
            DownloadRequest(item["url"], tuple(item.get("playlist_path", ())), item.get("expected_id"))
            for item in payload.get("retry_requests", [])
        ],
        preview_only=bool(payload.get("preview_only", False)),
        playlist_limit=int(payload.get("playlist_limit", 200)),
        network_attempts=int(payload.get("network_attempts", 2)),
        duplicate_policy=str(payload.get("duplicate_policy", "skip")),
        archive_enabled=bool(payload.get("archive_enabled", False)),
        embed_metadata=bool(payload.get("embed_metadata", False)),
        embed_cover=bool(payload.get("embed_cover", False)),
        metadata_overrides=dict(payload.get("metadata_overrides") or {}),
    )


class SocketEvents:
    def __init__(self, connection: socket.socket) -> None:
        self.connection = connection

    def _send(self, event: str, *values: Any) -> None:
        message = json.dumps({"event": event, "values": values}, ensure_ascii=False) + "\n"
        self.connection.sendall(message.encode("utf-8"))

    def emit_log(self, message: str) -> None:
        self._send("log", message)

    def emit_progress(self, value: int) -> None:
        self._send("progress", value)

    def emit_current_title(self, title: str) -> None:
        self._send("current_title", title)

    def emit_item_state(self, key: str, title: str, state: str, target: dict[str, Any]) -> None:
        self._send("item_state", key, title, state, target)

    def should_cancel(self) -> bool:
        return False

    def ask_duplicate(self, path: Path) -> str:
        self._send("duplicate_question", str(path))
        with self.connection.makefile("r", encoding="utf-8") as reader:
            answer = json.loads(reader.readline())
        return str(answer.get("decision", "cancel"))


def main() -> int:
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")
    port = int(os.environ["SPIDER_WORKER_PORT"])
    token = os.environ["SPIDER_WORKER_TOKEN"]
    with socket.create_connection(("127.0.0.1", port), timeout=15) as connection:
        connection.settimeout(None)
        connection.sendall((token + "\n").encode("utf-8"))
        with connection.makefile("r", encoding="utf-8") as reader:
            settings = settings_from_payload(json.loads(reader.readline()))
        events = SocketEvents(connection)
        try:
            summary = DownloadService(events).download(settings)
        except DownloadCancelled:
            events._send("finished", False, "Descarga cancelada.")
            return 1
        except Exception as exc:
            events.emit_log(traceback.format_exc())
            events._send("finished", False, str(exc) or "Error durante la descarga.")
            return 1

        message = (
            f"Vista previa: {summary.failed} enlaces fallidos."
            if settings.preview_only
            else f"Finalizado: {summary.completed} completados, {summary.skipped} omitidos, {summary.failed} fallidos."
        )
        events._send("finished", summary.failed == 0, message)
        return 0 if summary.failed == 0 else 1
