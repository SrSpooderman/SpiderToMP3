from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
SECRET_RE = re.compile(
    r"(?i)\b(token|api[_-]?key|secret|signature|authorization|cookie)\b(\s*[:=]\s*)([^\s,;]+)"
)


def redact_text(value: str) -> str:
    def redact_url(match: re.Match[str]) -> str:
        raw = match.group(0)
        suffix = raw[len(raw.rstrip(".,;)]}")) :]
        raw = raw.rstrip(".,;)]}")
        try:
            parsed = urlsplit(raw)
            host = parsed.hostname or ""
            if parsed.port is not None:
                host += f":{parsed.port}"
            safe = urlunsplit((parsed.scheme, host, parsed.path, "[oculto]" if parsed.query else "", ""))
            return safe + suffix
        except ValueError:
            return "[URL oculta]" + suffix

    value = URL_RE.sub(redact_url, value)
    value = SECRET_RE.sub(r"\1\2[oculto]", value)
    home = str(Path.home())
    return value.replace(home, "~") if home else value
