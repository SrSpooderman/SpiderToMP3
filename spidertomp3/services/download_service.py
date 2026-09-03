from __future__ import annotations

from typing import Any, Callable, Protocol

from yt_dlp import YoutubeDL

from spidertomp3.models import DownloadSettings
from spidertomp3.services.ytdlp_logger import YtdlpLogger

ProgressHook = Callable[[dict[str, Any]], None]


class DownloadEvents(Protocol):
    def emit_log(self, message: str) -> None:
        ...

    def emit_progress(self, value: int) -> None:
        ...

    def emit_current_title(self, title: str) -> None:
        ...

    def emit_item_done(self, title: str) -> None:
        ...

    def should_cancel(self) -> bool:
        ...


class DownloadService:
    def __init__(self, events: DownloadEvents) -> None:
        self.events = events

    def download(self, settings: DownloadSettings) -> None:
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        total = max(len(settings.urls), 1)

        for index, url in enumerate(settings.urls, start=1):
            self._raise_if_cancelled()
            self.events.emit_progress(int(((index - 1) / total) * 100))
            self.events.emit_log(f"\n[{index}/{total}] Preparando: {url}")

            with YoutubeDL(self._options(settings, index, total)) as ydl:
                ydl.download([url])

        self.events.emit_progress(100)

    def _options(
        self,
        settings: DownloadSettings,
        item_index: int,
        total_items: int,
    ) -> dict[str, Any]:
        output = settings.output_dir / settings.filename_template
        return {
            "format": "bestaudio/best",
            "outtmpl": str(output),
            "noplaylist": not settings.include_playlist,
            "ignoreerrors": False,
            "logger": YtdlpLogger(_EventLogSink(self.events)),
            "progress_hooks": [self._progress_hook(item_index, total_items)],
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": settings.audio_format,
                    "preferredquality": str(settings.audio_quality),
                }
            ],
        }

    def _progress_hook(self, item_index: int, total_items: int) -> ProgressHook:
        def hook(status: dict[str, Any]) -> None:
            self._raise_if_cancelled()
            title = _extract_title(status)
            self.events.emit_current_title(title)

            if status.get("status") == "finished":
                self.events.emit_item_done(title)
                self.events.emit_log(f"Listo para convertir: {title}")
                return

            if status.get("status") != "downloading":
                return

            downloaded = status.get("downloaded_bytes") or 0
            total = status.get("total_bytes") or status.get("total_bytes_estimate") or 0
            if not total:
                return

            local_percent = min(max(downloaded / total, 0), 1)
            overall = ((item_index - 1) + local_percent) / max(total_items, 1)
            self.events.emit_progress(int(overall * 100))

        return hook

    def _raise_if_cancelled(self) -> None:
        if self.events.should_cancel():
            raise DownloadCancelled("Descarga cancelada por el usuario.")


class DownloadCancelled(RuntimeError):
    pass


class _EventLogSink:
    def __init__(self, events: DownloadEvents) -> None:
        self.events = events

    def info(self, message: str) -> None:
        self.events.emit_log(message)


def _extract_title(status: dict[str, Any]) -> str:
    info = status.get("info_dict") or {}
    return str(info.get("title") or status.get("filename") or "Audio sin nombre")
