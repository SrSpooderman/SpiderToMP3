"""Regenerate hashed dependency locks for the supported build targets."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLATFORMS = {
    "Linux": "x86_64-manylinux_2_34",
    "Windows": "x86_64-pc-windows-msvc",
}


def main() -> None:
    (ROOT / "locks").mkdir(exist_ok=True)
    for system, platform in PLATFORMS.items():
        for version in ("3.12", "3.13"):
            name = f"runtime-{system}-py{version}.txt"
            _compile(name, ["requirements.txt"], version, platform)
        name = f"build-{system}-py3.13.txt"
        _compile(name, ["requirements.txt", "requirements-build.txt"], "3.13", platform)


def _compile(name: str, inputs: list[str], version: str, platform: str) -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "uv",
            "pip",
            "compile",
            *inputs,
            "--python-version",
            version,
            "--python-platform",
            platform,
            "--generate-hashes",
            "--only-binary",
            ":all:",
            "-q",
            "-o",
            f"locks/{name}",
        ],
        check=True,
        cwd=ROOT,
    )
    print(f"Actualizado: locks/{name}")


if __name__ == "__main__":
    main()
