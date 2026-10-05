from __future__ import annotations

import shutil
import tempfile
from pathlib import Path, PureWindowsPath
from urllib.parse import urlsplit

from yt_dlp import YoutubeDL

from config import AUDIO_FORMATS, QUALITY_OPTIONS
from models import DownloadSettings


def validate_settings(settings: DownloadSettings) -> dict[str, str]:
    errors: dict[str, str] = {}
    for index, url in enumerate(settings.urls, 1):
        try:
            parsed = urlsplit(url)
            valid = (parsed.scheme in {"http", "https"} and bool(parsed.hostname)
                     and not any(char.isspace() for char in url))
            if valid and parsed.port is not None:
                valid = 0 < parsed.port <= 65535
        except ValueError:
            valid = False
        if not valid:
            errors["urls"] = f"El enlace {index} no es una URL HTTP o HTTPS válida."
            break
        if parsed.hostname in {"spotify.com", "open.spotify.com", "www.spotify.com"}:
            errors["urls"] = "Los enlaces de Spotify no contienen audio descargable en esta aplicación."
            break

    template = settings.filename_template.strip()
    if not template:
        errors["template"] = "El patrón de nombre no puede estar vacío."
    elif (Path(template).is_absolute() or PureWindowsPath(template).is_absolute()
          or ".." in Path(template).parts or ".." in PureWindowsPath(template).parts):
        errors["template"] = "El patrón debe quedarse dentro de la carpeta de salida."
    elif error := YoutubeDL.validate_outtmpl(template):
        errors["template"] = f"Patrón de nombre inválido: {error}"

    if settings.audio_format not in AUDIO_FORMATS:
        errors["format"] = "El formato de audio no es válido."
    elif settings.audio_quality not in {quality for _, quality in QUALITY_OPTIONS[settings.audio_format]}:
        errors["format"] = "La calidad elegida no corresponde al formato."

    if not 1 <= settings.playlist_limit <= 5000:
        errors["playlist_limit"] = "El límite de la lista debe estar entre 1 y 5000."
    if not 1 <= settings.network_attempts <= 5:
        errors["network_attempts"] = "Los intentos deben estar entre 1 y 5."
    if settings.duplicate_policy not in {"skip", "rename", "ask"}:
        errors["duplicate_policy"] = "La opción para duplicados no es válida."

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        errors["ffmpeg"] = "Instala FFmpeg y ffprobe y añádelos al PATH."

    try:
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=settings.output_dir, prefix=".spidertomp3-", delete=True):
            pass
    except (OSError, ValueError) as exc:
        errors["output"] = f"No se puede escribir en la carpeta de salida: {exc}"

    return errors
