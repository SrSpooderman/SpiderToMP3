"""User-initiated MusicBrainz recording lookup with a conservative rate limit."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_URL = "https://musicbrainz.org/ws/2/recording/"
USER_AGENT = "SpiderToMP3/0.3.0 (https://github.com/SrSpooderman/SpiderToMP3)"
_last_request = 0.0


@dataclass(frozen=True)
class RecordingMatch:
    recording_id: str
    title: str
    artist: str
    album: str
    score: int


def search_recordings(title: str, artist: str = "") -> list[RecordingMatch]:
    global _last_request
    title = title.strip()
    artist = artist.strip()
    if not title:
        raise ValueError("Hace falta un título para buscar en MusicBrainz.")
    query = f'recording:"{_escape(title)}"'
    if artist:
        query += f' AND artist:"{_escape(artist)}"'
    params = urlencode({"query": query, "fmt": "json", "limit": 5})
    wait = 1.1 - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    request = Request(f"{API_URL}?{params}", headers={"User-Agent": USER_AGENT})
    _last_request = time.monotonic()
    with urlopen(request, timeout=10) as response:
        data = response.read(512 * 1024 + 1)
    if len(data) > 512 * 1024:
        raise ValueError("MusicBrainz devolvió demasiados datos.")
    return parse_recordings(data)


def parse_recordings(data: bytes) -> list[RecordingMatch]:
    try:
        payload = json.loads(data)
        entries = payload["recordings"]
        if not isinstance(entries, list):
            raise TypeError
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError("MusicBrainz devolvió una respuesta inválida.") from exc
    matches = []
    for item in entries[:5]:
        if not isinstance(item, dict) or not item.get("id") or not item.get("title"):
            continue
        credits = item.get("artist-credit") or []
        artist = "".join(
            part if isinstance(part, str) else str(part.get("name") or "") if isinstance(part, dict) else ""
            for part in credits
        ).strip()
        releases = item.get("releases") or []
        album = str(releases[0].get("title") or "") if releases and isinstance(releases[0], dict) else ""
        try:
            score = int(item.get("score") or 0)
        except (ValueError, TypeError):
            score = 0
        matches.append(RecordingMatch(str(item["id"]), str(item["title"]), artist, album, score))
    return matches


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
