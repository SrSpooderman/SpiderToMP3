from __future__ import annotations

from dataclasses import dataclass
from itertools import islice
from pathlib import Path
from typing import Any, Protocol

from yt_dlp import YoutubeDL

from models import DownloadRequest, DownloadSettings
from services.ytdlp_logger import YtdlpLogger


class DownloadEvents(Protocol):
    def emit_log(self, message: str) -> None: ...
    def emit_progress(self, value: int) -> None: ...
    def emit_current_title(self, title: str) -> None: ...
    def emit_item_state(self, key: str, title: str, state: str, target: dict[str, Any]) -> None: ...
    def should_cancel(self) -> bool: ...


@dataclass(frozen=True)
class DownloadSummary:
    completed: int
    failed: int


@dataclass(frozen=True)
class Track:
    key: str
    title: str
    retry_request: DownloadRequest
    info: dict[str, Any]
    extra_info: dict[str, Any]


class DownloadCancelled(RuntimeError):
    pass


class DownloadService:
    def __init__(self, events: DownloadEvents) -> None:
        self.events = events
        self._last_progress = 0
        self._titles: dict[str, str] = {}

    def download(self, settings: DownloadSettings) -> DownloadSummary:
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        tracks: list[Track] = []
        extraction_failures = 0

        requests = settings.retry_requests or [DownloadRequest(url) for url in settings.urls]
        for request in requests:
            source_url = request.url
            self._raise_if_cancelled()
            try:
                with YoutubeDL(self._options(settings)) as ydl:
                    raw = ydl.extract_info(source_url, download=False, process=False)
                entries = (
                    [_entry_at_path(raw, request.playlist_path, request.expected_id)]
                    if request.playlist_path
                    else list(_iter_entries(raw))
                )
                if not settings.include_playlist or settings.retry_requests:
                    entries = entries[:1]
                if not entries:
                    raise ValueError("El enlace no contiene audios descargables.")
            except DownloadCancelled:
                raise
            except Exception as exc:
                key = str(len(tracks) + extraction_failures)
                self.events.emit_item_state(
                    key, source_url, "fallido", _target_payload(request, str(exc))
                )
                self.events.emit_log(f"Error al analizar {source_url}: {exc}")
                extraction_failures += 1
                continue

            for entry, extra_info, path in entries:
                key = str(len(tracks) + extraction_failures)
                title = str(entry.get("title") or entry.get("id") or source_url)
                retry_request = _retry_request(entry, source_url, path)
                tracks.append(Track(key, title, retry_request, entry, extra_info))
                self._titles[key] = title
                self._emit_state(tracks[-1], "pendiente")

        total = len(tracks) + extraction_failures
        processed = extraction_failures
        completed = 0
        for track in tracks:
            self._raise_if_cancelled()
            self.events.emit_current_title(self._titles[track.key])
            self._emit_state(track, "descargando")
            try:
                with YoutubeDL(self._options(settings, track, processed, total)) as ydl:
                    info = ydl.process_ie_result(
                        track.info.copy(), download=False, extra_info=track.extra_info
                    )
                    if not isinstance(info, dict):
                        raise RuntimeError("yt-dlp no devolvió metadatos del audio.")
                    destination = Path(ydl.prepare_filename({**info, "ext": settings.audio_format}))
                    if destination.exists():
                        raise FileExistsError(f"Ya existe el archivo {destination}")
                    result = ydl.process_ie_result(info, download=True, extra_info=track.extra_info)
                if result is None:
                    raise RuntimeError("yt-dlp no devolvió un audio descargado.")
            except DownloadCancelled:
                self._emit_state(track, "cancelado")
                raise
            except Exception as exc:
                self._emit_state(track, "fallido", str(exc))
                self.events.emit_log(f"Error en {track.title}: {exc}")
            else:
                completed += 1
                self._emit_state(track, "completado")
            processed += 1
            self._emit_progress(min(99, int(processed / max(total, 1) * 100)))

        self._emit_progress(100)
        return DownloadSummary(completed, total - completed)

    def _options(
        self,
        settings: DownloadSettings,
        track: Track | None = None,
        processed: int = 0,
        total: int = 1,
    ) -> dict[str, Any]:
        postprocessor: dict[str, Any] = {
            "key": "FFmpegExtractAudio",
            "preferredcodec": settings.audio_format,
            "nopostoverwrites": True,
        }
        if settings.audio_quality is not None:
            postprocessor["preferredquality"] = str(settings.audio_quality)

        options: dict[str, Any] = {
            "format": "bestaudio/best",
            "outtmpl": str(settings.output_dir / settings.filename_template),
            "noplaylist": not settings.include_playlist,
            "ignoreerrors": False,
            "overwrites": False,
            "quiet": True,
            "socket_timeout": 10,
            "retries": 1,
            "logger": YtdlpLogger(_EventLogSink(self.events)),
            "postprocessors": [postprocessor],
        }
        if track is not None:
            options["progress_hooks"] = [self._progress_hook(track, processed, total)]
            options["postprocessor_hooks"] = [self._postprocessor_hook(track)]
        return options

    def _progress_hook(self, track: Track, processed: int, total: int):
        def hook(status: dict[str, Any]) -> None:
            self._raise_if_cancelled()
            info = status.get("info_dict") or {}
            if info.get("title"):
                self._titles[track.key] = str(info["title"])
            state = status.get("status")
            if state == "finished":
                self._emit_state(track, "convirtiendo")
                return
            if state != "downloading":
                return
            self._emit_state(track, "descargando")
            downloaded = status.get("downloaded_bytes") or 0
            size = status.get("total_bytes") or status.get("total_bytes_estimate") or 0
            if size:
                fraction = min(max(downloaded / size, 0), 1) * 0.9
                self._emit_progress(int((processed + fraction) / total * 100))

        return hook

    def _postprocessor_hook(self, track: Track):
        def hook(status: dict[str, Any]) -> None:
            self._raise_if_cancelled()
            if status.get("postprocessor") == "ExtractAudio":
                self._emit_state(track, "convirtiendo")

        return hook

    def _raise_if_cancelled(self) -> None:
        if self.events.should_cancel():
            raise DownloadCancelled("Descarga cancelada.")

    def _emit_progress(self, value: int) -> None:
        self._last_progress = max(self._last_progress, min(value, 99)) if value < 100 else 100
        self.events.emit_progress(self._last_progress)

    def _emit_state(self, track: Track, state: str, error: str = "") -> None:
        self.events.emit_item_state(
            track.key, self._titles[track.key], state,
            _target_payload(track.retry_request, error),
        )


def _iter_entries(
    raw: dict[str, Any] | None,
    extra: dict[str, Any] | None = None,
    path: tuple[int, ...] = (),
):
    if not raw:
        return
    extra = extra or {}
    if raw.get("_type") in {"playlist", "multi_video"}:
        playlist = str(raw.get("title") or raw.get("id") or "Lista")
        entries = raw.get("entries") or []
        for index, entry in enumerate(entries, 1):
            if entry:
                yield from _iter_entries(
                    entry, {**extra, "playlist": playlist, "playlist_index": index},
                    (*path, index),
                )
    else:
        yield raw, extra, path


def _entry_at_path(
    raw: dict[str, Any] | None, path: tuple[int, ...], expected_id: str | None
):
    info = raw
    extra: dict[str, Any] = {}
    for index in path:
        if not info or info.get("_type") not in {"playlist", "multi_video"} or index < 1:
            raise ValueError("El elemento de la lista ya no está disponible.")
        playlist = str(info.get("title") or info.get("id") or "Lista")
        info = next(islice(info.get("entries") or [], index - 1, index), None)
        extra = {**extra, "playlist": playlist, "playlist_index": index}
    if not info or info.get("_type") in {"playlist", "multi_video"}:
        raise ValueError("El elemento de la lista ya no está disponible.")
    if expected_id is not None and str(info.get("id")) != expected_id:
        raise ValueError("La lista cambió y el audio ya no ocupa la misma posición.")
    return info, extra, path


def _retry_request(
    entry: dict[str, Any], source_url: str, path: tuple[int, ...]
) -> DownloadRequest:
    for value in (entry.get("webpage_url"), entry.get("original_url"), entry.get("url")):
        if isinstance(value, str) and value.startswith(("http://", "https://")) and value != source_url:
            return DownloadRequest(value)
    identifier = str(entry["id"]) if entry.get("id") is not None else None
    return DownloadRequest(source_url, path, identifier if path else None)


def _target_payload(request: DownloadRequest, error: str = "") -> dict[str, Any]:
    payload: dict[str, Any] = {
        "url": request.url, "playlist_path": list(request.playlist_path),
        "expected_id": request.expected_id,
    }
    if error:
        payload["error"] = " ".join(error.split())[:240]
    return payload


class _EventLogSink:
    def __init__(self, events: DownloadEvents) -> None:
        self.events = events

    def info(self, message: str) -> None:
        self.events.emit_log(message)
