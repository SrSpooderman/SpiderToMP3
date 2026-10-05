from __future__ import annotations

import argparse
import hashlib
import tarfile
from pathlib import Path
from shutil import copy2

from config import APP_VERSION
from scripts.versioning import check_version


ROOT = Path(__file__).resolve().parents[1]
LINUX_CONTENTS = {
    "SpiderToMP3-linux-x86_64": (None, 0o755),
    "install-bazzite.sh": (ROOT / "packaging" / "install-bazzite.sh", 0o755),
    "spidertomp3.desktop": (ROOT / "packaging" / "spidertomp3.desktop", 0o644),
    "spidertomp3.svg": (ROOT / "assets" / "spidertomp3-icon.svg", 0o644),
}


def asset_names(version: str = APP_VERSION) -> tuple[str, str]:
    check_version(version)
    return (
        f"SpiderToMP3-v{version}-windows-x86_64.exe",
        f"SpiderToMP3-v{version}-linux-x86_64.tar.gz",
    )


def prepare(input_dir: Path, output_dir: Path, version: str = APP_VERSION) -> None:
    windows_name, linux_name = asset_names(version)
    windows_input = input_dir / "SpiderToMP3.exe"
    linux_input = input_dir / "SpiderToMP3-linux-x86_64"
    for path in (windows_input, linux_input):
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"Falta el ejecutable: {path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    copy2(windows_input, output_dir / windows_name)
    copy2(ROOT / "packaging" / "uninstall-bazzite.sh", output_dir / "uninstall-bazzite.sh")
    with tarfile.open(output_dir / linux_name, "w:gz") as archive:
        for name, (source, mode) in LINUX_CONTENTS.items():
            path = linux_input if source is None else source
            with path.open("rb") as file:
                info = tarfile.TarInfo(name)
                info.size = path.stat().st_size
                info.mode = mode
                info.mtime = 0
                archive.addfile(info, file)

    checksums = "".join(
        f"{hashlib.sha256((output_dir / name).read_bytes()).hexdigest()}  {name}\n"
        for name in (windows_name, linux_name, "uninstall-bazzite.sh")
    )
    (output_dir / "SHA256SUMS").write_text(checksums, encoding="ascii")
    verify(output_dir, version)


def verify(output_dir: Path, version: str = APP_VERSION) -> None:
    windows_name, linux_name = asset_names(version)
    expected = {windows_name, linux_name, "uninstall-bazzite.sh", "SHA256SUMS"}
    if {path.name for path in output_dir.iterdir()} != expected:
        raise ValueError("Los archivos de la Release no coinciden con los esperados")
    lines = (output_dir / "SHA256SUMS").read_text(encoding="ascii").splitlines()
    checksums = [line.split("  ", 1) for line in lines]
    if len(checksums) != 3 or {name for _, name in checksums} != {windows_name, linux_name, "uninstall-bazzite.sh"}:
        raise ValueError("SHA256SUMS contiene nombres inesperados")
    for digest, name in checksums:
        if hashlib.sha256((output_dir / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"SHA-256 incorrecto: {name}")
    with tarfile.open(output_dir / linux_name, "r:gz") as archive:
        if set(archive.getnames()) != set(LINUX_CONTENTS):
            raise ValueError("Contenido inesperado en el paquete Linux")
        for name, (_, mode) in LINUX_CONTENTS.items():
            if archive.getmember(name).mode != mode:
                raise ValueError(f"Permisos incorrectos en {name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "verify"))
    parser.add_argument("path", type=Path)
    parser.add_argument("output", type=Path, nargs="?")
    args = parser.parse_args()
    if args.command == "prepare":
        if args.output is None:
            parser.error("prepare necesita el directorio de salida")
        prepare(args.path, args.output)
    else:
        verify(args.path)


if __name__ == "__main__":
    main()
