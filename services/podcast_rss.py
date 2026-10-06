"""Read public podcast RSS feeds and expose only their published enclosures."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree


MAX_FEED_BYTES = 5 * 1024 * 1024
MAX_EPISODES = 5000


@dataclass(frozen=True)
class PodcastEpisode:
    title: str
    url: str
    guid: str
    published: str = ""


def fetch_rss(feed_url: str) -> list[PodcastEpisode]:
    if not _is_http_url(feed_url):
        raise ValueError("La dirección del podcast debe usar HTTP o HTTPS.")
    request = Request(feed_url, headers={"User-Agent": "SpiderToMP3/0.3.0"})
    with urlopen(request, timeout=10) as response:
        data = response.read(MAX_FEED_BYTES + 1)
        resolved_url = response.geturl()
    if len(data) > MAX_FEED_BYTES:
        raise ValueError("El feed RSS supera el límite de 5 MiB.")
    if not _is_http_url(resolved_url):
        raise ValueError("El feed RSS redirigió a una dirección no permitida.")
    return parse_rss(data, resolved_url)


def parse_rss(data: bytes, feed_url: str) -> list[PodcastEpisode]:
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as exc:
        raise ValueError("El feed no contiene XML válido.") from exc
    if root.tag != "rss":
        raise ValueError("El feed no es un podcast RSS.")
    episodes = []
    seen = set()
    for item in root.findall("./channel/item"):
        for enclosure in item.findall("enclosure"):
            mime = (enclosure.get("type") or "").lower()
            if mime and not mime.startswith("audio/"):
                continue
            url = urljoin(feed_url, enclosure.get("url") or "")
            if not _is_http_url(url) or url in seen:
                continue
            seen.add(url)
            title = (item.findtext("title") or url).strip()
            guid = (item.findtext("guid") or url).strip()
            published = (item.findtext("pubDate") or "").strip()
            episodes.append(PodcastEpisode(title, url, guid, published))
            if len(episodes) > MAX_EPISODES:
                raise ValueError("El feed supera el límite de 5000 episodios.")
    if not episodes:
        raise ValueError("El feed no contiene archivos de audio publicados.")
    return episodes


def _is_http_url(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.hostname) and not any(c.isspace() for c in value)
    except ValueError:
        return False
