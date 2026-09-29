from __future__ import annotations

from pathlib import Path

APP_NAME = "SpiderToMP3"
APP_VERSION = "0.1.2"
WINDOW_TITLE = f"{APP_NAME} {APP_VERSION} - baja canciones sin drama"
DEFAULT_FILENAME_TEMPLATE = "%(title).120s [%(id)s].%(ext)s"
DEFAULT_OUTPUT_DIR = Path.home() / "Music" / APP_NAME
AUDIO_FORMATS = ("mp3", "m4a", "opus", "wav", "flac")
QUALITY_OPTIONS = {
    "mp3": (("Alta (VBR 2)", 2), ("Equilibrada (VBR 5)", 5), ("Compacta (VBR 8)", 8)),
    "m4a": (("Alta (256 kb/s)", 256), ("Equilibrada (192 kb/s)", 192), ("Compacta (128 kb/s)", 128)),
    "opus": (("Alta (160 kb/s)", 160), ("Equilibrada (128 kb/s)", 128), ("Compacta (96 kb/s)", 96)),
    "wav": (("Sin pérdida", None),),
    "flac": (("Sin pérdida", None),),
}
