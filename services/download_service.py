from __future__ import annotations

from dataclasses import dataclass
from itertools import islice
from pathlib import Path
import sys
import time
from typing import Any, Protocol

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from models import DownloadRequest, DownloadSettings
from services.ytdlp_logger import YtdlpLogger
from services.error_help import error_help


class DownloadEvents(Protocol):
    def emit_log(self, message: str) -> None: ...
    def emit_progress(self, value: int) -> None: ...
    def emit_current_title(self, title: str) -> None: ...
    def emit_item_state(self, key: str, title: str, state: str, target: dict[str, Any]) -> None: ...
    def should_cancel(self) -> bool: ...
    def ask_duplicate(self, path: Path) -> str: ...


@dataclass(frozen=True)
class DownloadSummary:
    completed: int
    failed: int
    skipped: int = 0


@dataclass(frozen=True)
class Track:
    key: str
    title: str
    retry_request: DownloadRequest
    info: dict[str, Any]
    extra_info: dict[str, Any]
    truncated: bool = False


class DownloadCancelled(RuntimeError):
    pass


class DownloadSkipped(RuntimeError):
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
            self.events.emit_current_title(f"Analizando: {source_url}")
            try:
                truncated = False
                with YoutubeDL(self._options(settings)) as ydl:
                    raw = ydl.extract_info(source_url, download=False, process=False)
                if request.playlist_path:
                    entries = [_entry_at_path(raw, request.playlist_path, request.expected_id)]
                elif not settings.include_playlist or settings.retry_requests:
                    entries = list(islice(_iter_entries(raw), 1))
                else:
                    entries = list(islice(_iter_entries(raw), settings.playlist_limit + 1))
                    if len(entries) > settings.playlist_limit:
                        truncated = True
                        entries = entries[:settings.playlist_limit]
                        self.events.emit_log(
                            f"La lista supera el límite de {settings.playlist_limit} audios; solo se mostrarán los primeros."
                        )
                if not entries:
                    raise ValueError("El enlace no contiene audios descargables.")
            except DownloadCancelled:
                raise
            except Exception as exc:
                key = str(len(tracks) + extraction_failures)
                self.events.emit_item_state(
                    key, source_url, "fallido", {**_target_payload(request, str(exc)), "help": error_help(exc)}
                )
                self.events.emit_log(f"Error al analizar {source_url}: {exc}")
                extraction_failures += 1
                continue

            for entry, extra_info, path in entries:
                key = str(len(tracks) + extraction_failures)
                title = str(entry.get("title") or entry.get("id") or source_url)
                retry_request = _retry_request(entry, source_url, path)
                tracks.append(Track(key, title, retry_request, entry, extra_info, truncated))
                self._titles[key] = title
                self._emit_state(tracks[-1], "pendiente")

        if settings.preview_only:
            return DownloadSummary(0, extraction_failures)

        total = len(tracks) + extraction_failures
        processed = extraction_failures
        completed = 0
        skipped = 0
        for track in tracks:
            self._raise_if_cancelled()
            self.events.emit_current_title(self._titles[track.key])
            self._emit_state(track, "descargando")
            try:
                for attempt in range(1, settings.network_attempts + 1):
                    try:
                        final_path = self._download_track(settings, track, processed, total)
                        break
                    except Exception as exc:
                        if attempt >= settings.network_attempts or not _is_temporary_network_error(exc):
                            raise
                        wait = min(2 ** (attempt - 1), 8)
                        self.events.emit_log(
                            f"Error temporal en {track.title}. Reintento {attempt + 1}/{settings.network_attempts} en {wait} s."
                        )
                        deadline = time.monotonic() + wait
                        while time.monotonic() < deadline:
                            self._raise_if_cancelled()
                            time.sleep(min(0.1, deadline - time.monotonic()))
            except DownloadCancelled:
                self._emit_state(track, "cancelado")
                raise
            except DownloadSkipped as exc:
                skipped += 1
                self._emit_state(track, "omitido", str(exc))
            except Exception as exc:
                self._emit_state(track, "fallido", str(exc), help_text=error_help(exc))
                self.events.emit_log(f"Error en {track.title}: {exc}")
            else:
                completed += 1
                self._emit_state(track, "completado", path=final_path)
            processed += 1
            self._emit_progress(min(99, int(processed / max(total, 1) * 100)))

        self._emit_progress(100)
        return DownloadSummary(completed, total - completed - skipped, skipped)

    def _download_track(
        self, settings: DownloadSettings, track: Track, processed: int, total: int
    ) -> Path:
        with YoutubeDL(self._options(settings, track, processed, total)) as ydl:
            info = ydl.process_ie_result(track.info.copy(), download=False, extra_info=track.extra_info)
            if not isinstance(info, dict):
                raise RuntimeError("yt-dlp no devolvió metadatos del audio.")
            if settings.archive_enabled and ydl.in_download_archive(info):
                raise DownloadSkipped("El ID ya figura en el registro de descargas.")
            destination = Path(ydl.prepare_filename({**info, "ext": settings.audio_format}))
            if destination.exists():
                policy = settings.duplicate_policy
                if policy == "ask":
                    policy = self.events.ask_duplicate(destination)
                if policy == "skip":
                    raise DownloadSkipped(f"Ya existe {destination}")
                if policy == "cancel":
                    raise DownloadCancelled("Descarga cancelada.")
                if policy != "rename":
                    raise RuntimeError("No se recibió una decisión válida para el archivo existente.")
                number = 2
                while True:
                    candidate = destination.with_name(f"{destination.stem} ({number}){destination.suffix}")
                    if not candidate.exists():
                        destination = candidate
                        ydl.params["outtmpl"]["default"] = str(candidate.with_suffix("")) + ".%(ext)s"
                        break
                    number += 1
            source_file = Path(ydl.prepare_filename({**info, "ext": info.get("ext") or settings.audio_format}))
            partial_candidates = (
                Path(str(source_file) + ".part"), Path(str(source_file) + ".ytdl"),
                source_file.with_name(f"{source_file.stem}.temp{source_file.suffix}"), destination,
            )
            new_partial_paths = [str(path) for path in partial_candidates if not path.exists()]
            self._emit_state(track, "descargando", partial_paths=new_partial_paths,
                             candidate_output=destination)
            result = ydl.process_ie_result(info, download=True, extra_info=track.extra_info)
        if result is None:
            raise RuntimeError("yt-dlp no devolvió un audio descargado.")
        final_path = _result_path(result, destination)
        if not final_path.is_file() or final_path.stat().st_size == 0:
            raise RuntimeError(f"No se encontró el audio convertido: {final_path}")
        return final_path

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
        if sys.platform.startswith("linux"):
            options["compat_opts"] = {"no-certifi"}
        if settings.archive_enabled:
            options["download_archive"] = str(settings.output_dir / ".spidertomp3-archive.txt")
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
            downloaded = status.get("downloaded_bytes") or 0
            size = status.get("total_bytes") or status.get("total_bytes_estimate") or 0
            if size:
                fraction = min(max(downloaded / size, 0), 1) * 0.9
                self._emit_progress(int((processed + fraction) / total * 100))
            self._emit_state(track, "descargando", progress={
                "percent": int(downloaded / size * 100) if size else None,
                "speed": status.get("speed"), "eta": status.get("eta"),
            })

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

    def _emit_state(self, track: Track, state: str, error: str = "", path: Path | None = None,
                    progress: dict[str, Any] | None = None, help_text: str = "",
                    partial_paths: list[str] | None = None,
                    candidate_output: Path | None = None) -> None:
        payload = _target_payload(track.retry_request, error)
        payload["duration"] = track.info.get("duration")
        payload["id"] = track.info.get("id")
        payload["source"] = track.extra_info.get("playlist") or track.info.get("extractor_key") or "Enlace"
        payload["truncated"] = track.truncated
        if path is not None:
            payload["path"] = str(path)
        if progress is not None:
            payload["progress"] = progress
        if help_text:
            payload["help"] = help_text
        if partial_paths is not None:
            payload["partial_paths"] = partial_paths
        if candidate_output is not None:
            payload["candidate_output"] = str(candidate_output)
        self.events.emit_item_state(
            track.key, self._titles[track.key], state,
            payload,
        )


def _result_path(result: dict[str, Any], fallback: Path) -> Path:
    downloads = result.get("requested_downloads") or []
    for item in reversed(downloads):
        if isinstance(item, dict) and item.get("filepath"):
            return Path(item["filepath"])
    if result.get("filepath"):
        return Path(result["filepath"])
    return fallback


def _is_temporary_network_error(exc: Exception) -> bool:
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    if not isinstance(exc, DownloadError):
        return False
    message = str(exc).lower()
    return any(marker in message for marker in (
        "timed out", "timeout", "connection reset", "connection refused",
        "temporary failure", "network is unreachable", "http error 429",
        "http error 500", "http error 502", "http error 503", "http error 504",
    ))


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
