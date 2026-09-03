from __future__ import annotations

from pathlib import Path

APP_NAME = "SpiderToMP3"
WINDOW_TITLE = "SpiderToMP3 - baja canciones sin drama"
DEFAULT_FILENAME_TEMPLATE = "%(title).120s.%(ext)s"
DEFAULT_OUTPUT_DIR = Path.home() / "Music" / APP_NAME
AUDIO_FORMATS = ("mp3", "m4a", "opus", "wav", "flac")
