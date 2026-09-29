from __future__ import annotations

import re


URL_SEPARATOR = re.compile(r",\s*(?=https?://)", re.IGNORECASE)


def parse_urls(raw_text: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()

    for line in raw_text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        for part in URL_SEPARATOR.split(line):
            url = part.strip()
            if not url or url in seen:
                continue
            seen.add(url)
            urls.append(url)

    return urls
