from __future__ import annotations

import argparse
import re
from pathlib import Path

from config import APP_NAME, APP_VERSION


VERSION_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$")


def check_version(version: str = APP_VERSION) -> None:
    match = VERSION_PATTERN.fullmatch(version)
    if not match:
        raise ValueError(f"Versión inválida: {version}")
    if "-" in version:
        identifiers = version.split("-", 1)[1].split(".")
        if any(
            not identifier or (identifier.isdigit() and len(identifier) > 1 and identifier.startswith("0"))
            for identifier in identifiers
        ):
            raise ValueError(f"Versión inválida: {version}")


def check_tag(tag: str, version: str = APP_VERSION) -> None:
    check_version(version)
    if tag != f"v{version}":
        raise ValueError(f"La etiqueta {tag!r} no coincide con v{version}")


def release_notes(changelog: str, version: str = APP_VERSION) -> str:
    heading = f"## [{version}]"
    lines = changelog.splitlines()
    if heading not in lines:
        raise ValueError(f"Faltan las notas de {version} en CHANGELOG.md")
    start = lines.index(heading) + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## [")), len(lines))
    notes = "\n".join(lines[start:end]).strip()
    if not notes:
        raise ValueError(f"Las notas de {version} están vacías")
    return notes + "\n"


def windows_version_resource(version: str = APP_VERSION) -> str:
    check_version(version)
    numbers = tuple(map(int, version.split("-", 1)[0].split("."))) + (0,)
    return f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={numbers!r}, prodvers={numbers!r},
    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0,
    date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('FileDescription', '{APP_NAME}'),
      StringStruct('FileVersion', '{version}'),
      StringStruct('InternalName', '{APP_NAME}'),
      StringStruct('OriginalFilename', '{APP_NAME}.exe'),
      StringStruct('ProductName', '{APP_NAME}'),
      StringStruct('ProductVersion', '{version}'),
    ])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])]),
  ])
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("show", "check-tag", "notes", "windows-resource"))
    parser.add_argument("argument", nargs="?")
    args = parser.parse_args()
    check_version()
    if args.command == "show":
        print(APP_VERSION)
    elif args.command == "check-tag":
        if not args.argument:
            parser.error("check-tag necesita una etiqueta")
        check_tag(args.argument)
    elif args.command == "notes":
        print(release_notes(Path("CHANGELOG.md").read_text(encoding="utf-8")), end="")
    else:
        if not args.argument:
            parser.error("windows-resource necesita una ruta de salida")
        destination = Path(args.argument)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(windows_version_resource(), encoding="utf-8")


if __name__ == "__main__":
    main()
