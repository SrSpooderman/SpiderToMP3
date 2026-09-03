from __future__ import annotations


def parse_urls(raw_text: str) -> list[str]:
    raw_lines = raw_text.replace(",", "\n").splitlines()
    urls: list[str] = []
    seen: set[str] = set()

    for line in raw_lines:
        url = line.strip()
        if not url or url.startswith("#") or url in seen:
            continue
        seen.add(url)
        urls.append(url)

    return urls
