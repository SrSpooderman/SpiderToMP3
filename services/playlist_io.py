"""Import and export simple audio lists without contacting the source sites."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


MAX_LIST_BYTES = 5 * 1024 * 1024
MAX_LIST_ITEMS = 5000
VALID_STATES = {"pendiente", "descargando", "convirtiendo", "completado", "fallido", "cancelado", "omitido"}
CSV_FIELDS = ("title", "url", "status", "path")


@dataclass(frozen=True)
class PlaylistRecord:
    title: str
    url: str = ""
    status: str = "pendiente"
    path: str = ""


def read_playlist(path: Path) -> list[PlaylistRecord]:
    if path.stat().st_size > MAX_LIST_BYTES:
        raise ValueError("La lista supera el límite de 5 MiB.")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames or "url" not in reader.fieldnames:
                raise ValueError("El CSV necesita una columna 'url'.")
            records = [_record(row) for row in reader]
    elif suffix in {".m3u", ".m3u8"}:
        records = _read_m3u(path.read_text(encoding="utf-8-sig"), path.parent)
    else:
        raise ValueError("Elige un archivo .csv, .m3u o .m3u8.")
    if len(records) > MAX_LIST_ITEMS:
        raise ValueError("La lista supera el límite de 5000 elementos.")
    return records


def write_playlist(path: Path, records: list[PlaylistRecord]) -> None:
    if len(records) > MAX_LIST_ITEMS:
        raise ValueError("La lista supera el límite de 5000 elementos.")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for record in records:
                writer.writerow(
                    {
                        "title": _csv_safe_title(record.title),
                        "url": record.url,
                        "status": record.status,
                        "path": record.path,
                    }
                )
    elif suffix in {".m3u", ".m3u8"}:
        lines = ["#EXTM3U"]
        for record in records:
            title = " ".join(record.title.splitlines())
            lines.append(f"#EXTINF:-1,{title}")
            lines.append(
                "#SPIDERTO:"
                + json.dumps(
                    {
                        "title": record.title,
                        "url": record.url,
                        "status": record.status,
                        "path": record.path,
                    },
                    ensure_ascii=False,
                )
            )
            lines.append(record.path or record.url)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        raise ValueError("Elige un archivo .csv, .m3u o .m3u8.")


def _read_m3u(text: str, base: Path) -> list[PlaylistRecord]:
    records = []
    title = ""
    metadata: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#EXTINF:"):
            title = line.partition(",")[2].strip()
        elif line.startswith("#SPIDERTO:"):
            try:
                value = json.loads(line[len("#SPIDERTO:") :])
                metadata = value if isinstance(value, dict) else {}
            except json.JSONDecodeError as exc:
                raise ValueError("La lista M3U contiene metadatos inválidos.") from exc
        elif not line.startswith("#"):
            is_url = _is_http_url(line)
            local = Path(line)
            if not is_url and not local.is_absolute():
                local = (base / local).resolve()
            values = {
                "title": title or Path(line).name,
                "url": line if is_url else "",
                "path": "" if is_url else str(local),
                "status": "pendiente",
            }
            values.update(metadata)
            if values.get("path") and not Path(str(values["path"])).is_absolute():
                values["path"] = str((base / str(values["path"])).resolve())
            records.append(_record(values))
            title = ""
            metadata = {}
            if len(records) > MAX_LIST_ITEMS:
                raise ValueError("La lista supera el límite de 5000 elementos.")
    return records


def _record(values: dict) -> PlaylistRecord:
    url = str(values.get("url") or "").strip()
    path = str(values.get("path") or "").strip()
    if url and not _is_http_url(url):
        raise ValueError("La lista contiene una URL que no es HTTP o HTTPS.")
    if not url and not path:
        raise ValueError("La lista contiene una fila sin URL ni archivo local.")
    status = str(values.get("status") or "pendiente").strip().lower()
    if status not in VALID_STATES or status in {"descargando", "convirtiendo"}:
        status = "pendiente"
    if status == "completado" and not (path and Path(path).is_file()):
        status = "pendiente" if url else "omitido"
    if not url and path:
        status = "completado" if Path(path).is_file() else "omitido"
    title = str(values.get("title") or url or Path(path).name).strip()
    if title.startswith("'") and title[1:].lstrip().startswith(("=", "+", "-", "@")):
        title = title[1:]
    return PlaylistRecord(title, url, status, path)


def _csv_safe_title(title: str) -> str:
    return "'" + title if title.lstrip().startswith(("=", "+", "-", "@")) else title


def _is_http_url(value: str) -> bool:
    try:
        parts = urlsplit(value)
        return (
            parts.scheme in {"http", "https"}
            and bool(parts.hostname)
            and not any(c.isspace() for c in value)
            and (parts.port is None or 0 < parts.port <= 65535)
        )
    except ValueError:
        return False
