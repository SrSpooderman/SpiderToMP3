from __future__ import annotations

import hashlib
import hmac
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path

from config import APP_VERSION


REPOSITORY = "SrSpooderman/SpiderToMP3"
LATEST_RELEASE_URL = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
MAX_ASSET_BYTES = 512 * 1024 * 1024
LINUX_PACKAGE_FILES = {
    "SpiderToMP3-linux-x86_64",
    "install-bazzite.sh",
    "spidertomp3.desktop",
    "spidertomp3.svg",
}
VERSION_RE = re.compile(r"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z.-]+))?$")


class UpdateError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReleaseUpdate:
    version: str
    notes: str
    page_url: str
    asset_name: str
    asset_url: str
    asset_size: int
    checksums_url: str


def is_newer_version(candidate: str, current: str = APP_VERSION) -> bool:
    latest_match = VERSION_RE.fullmatch(candidate)
    current_match = VERSION_RE.fullmatch(current)
    if latest_match is None or current_match is None:
        raise UpdateError("La versión de la Release no tiene un formato válido.")
    latest_numbers = tuple(int(value) for value in latest_match.groups()[:3])
    current_numbers = tuple(int(value) for value in current_match.groups()[:3])
    return latest_numbers > current_numbers or (
        latest_numbers == current_numbers
        and current_match.group(4) is not None
        and latest_match.group(4) is None
    )


def _asset_url(tag: str, name: str) -> str:
    return f"https://github.com/{REPOSITORY}/releases/download/{tag}/{name}"


def release_from_json(data: bytes, system: str | None = None, current: str = APP_VERSION) -> ReleaseUpdate | None:
    try:
        payload = json.loads(data)
        if not isinstance(payload, dict) or payload.get("draft") or payload.get("prerelease"):
            raise UpdateError("La respuesta no es una Release estable.")
        tag = payload["tag_name"]
        if not isinstance(tag, str) or not tag.startswith("v"):
            raise UpdateError("La Release no tiene una etiqueta válida.")
        version = tag[1:]
        if "-" in version:
            raise UpdateError("La Release no es una versión estable.")
        if not is_newer_version(version, current):
            return None
        if platform.machine().lower() not in {"x86_64", "amd64"}:
            raise UpdateError("No hay actualización automática para esta arquitectura.")
        system = system or platform.system()
        if system == "Windows":
            asset_name = f"SpiderToMP3-v{version}-windows-x86_64.exe"
        elif system == "Linux":
            asset_name = f"SpiderToMP3-v{version}-linux-x86_64.tar.gz"
        else:
            raise UpdateError("La actualización automática no está disponible en este sistema.")
        assets = {asset["name"]: asset for asset in payload["assets"]}
        asset = assets[asset_name]
        checksums = assets["SHA256SUMS"]
        for item, name in ((asset, asset_name), (checksums, "SHA256SUMS")):
            if item["browser_download_url"] != _asset_url(tag, name):
                raise UpdateError("La Release contiene una URL de descarga inesperada.")
        size = int(asset["size"])
        if not 0 < size <= MAX_ASSET_BYTES:
            raise UpdateError("El tamaño del ejecutable no es válido.")
        return ReleaseUpdate(
            version=version,
            notes=str(payload.get("body") or ""),
            page_url=f"https://github.com/{REPOSITORY}/releases/tag/{tag}",
            asset_name=asset_name,
            asset_url=asset["browser_download_url"],
            asset_size=size,
            checksums_url=checksums["browser_download_url"],
        )
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        raise UpdateError("La Release no contiene los archivos esperados.") from exc


def expected_checksum(data: bytes, asset_name: str) -> str:
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError as exc:
        raise UpdateError("SHA256SUMS no es un archivo de texto válido.") from exc
    for line in text.splitlines():
        digest, separator, name = line.partition("  ")
        if separator and name == asset_name and re.fullmatch(r"[0-9a-fA-F]{64}", digest):
            return digest.lower()
    raise UpdateError("SHA256SUMS no contiene el ejecutable seleccionado.")


def verify_download(path: Path, release: ReleaseUpdate, checksum: str) -> None:
    if path.stat().st_size != release.asset_size:
        raise UpdateError("La descarga está incompleta.")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if not hmac.compare_digest(digest.hexdigest(), checksum):
        raise UpdateError("La suma SHA-256 de la descarga no coincide.")


def prepare_linux_package(archive_path: Path, staging_dir: Path) -> None:
    try:
        with tarfile.open(archive_path, "r:gz") as archive:
            members = archive.getmembers()
            if {member.name for member in members} != LINUX_PACKAGE_FILES or len(members) != len(LINUX_PACKAGE_FILES):
                raise UpdateError("El paquete Linux contiene archivos inesperados.")
            if (any(not member.isfile() or member.size <= 0 or member.size > MAX_ASSET_BYTES for member in members)
                    or sum(member.size for member in members) > MAX_ASSET_BYTES):
                raise UpdateError("El paquete Linux contiene archivos no válidos.")
            for member in members:
                source = archive.extractfile(member)
                if source is None:
                    raise UpdateError("No se pudo leer el paquete Linux.")
                with source, (staging_dir / member.name).open("wb") as target:
                    shutil.copyfileobj(source, target)
        (staging_dir / "SpiderToMP3-linux-x86_64").chmod(0o755)
    except (OSError, tarfile.TarError) as exc:
        raise UpdateError("No se pudo preparar el paquete Linux.") from exc


LINUX_HELPER = """#!/bin/sh
set -eu
old_pid=$1
stage=$2
target=$3
installed=$4
count=0
while kill -0 "$old_pid" 2>/dev/null; do
    count=$((count + 1))
    [ "$count" -le 300 ] || exit 1
    sleep 0.2
done
new_file="${target}.new.$$"
backup="${target}.previous"
install -m 755 "$stage/SpiderToMP3-linux-x86_64" "$new_file"
cp -p "$target" "$backup"
mv -f "$new_file" "$target"
if [ "$installed" = yes ]; then
    install -Dm644 "$stage/spidertomp3.svg" "$HOME/.local/share/icons/hicolor/scalable/apps/spidertomp3.svg"
    install -Dm644 "$stage/spidertomp3.desktop" "$HOME/.local/share/applications/spidertomp3.desktop"
    sed -i "s|^Exec=.*|Exec=$target|" "$HOME/.local/share/applications/spidertomp3.desktop"
fi
PYINSTALLER_RESET_ENVIRONMENT=1 "$target" >/dev/null 2>&1 &
rm -rf -- "$stage"
"""


WINDOWS_HELPER = r"""param(
    [Parameter(Mandatory=$true)][int]$OldPid,
    [Parameter(Mandatory=$true)][string]$Staged,
    [Parameter(Mandatory=$true)][string]$Target
)
$ErrorActionPreference = 'Stop'
try { Wait-Process -Id $OldPid -Timeout 60 -ErrorAction SilentlyContinue } catch {}
$backup = "$Target.previous.$PID"
$pending = "$Target.new.$PID"
for ($attempt = 0; $attempt -lt 120; $attempt++) {
    try {
        Copy-Item -LiteralPath $Staged -Destination $pending -Force
        if (Test-Path -LiteralPath $backup) { Remove-Item -LiteralPath $backup -Force }
        Move-Item -LiteralPath $Target -Destination $backup
        Move-Item -LiteralPath $pending -Destination $Target
        $env:PYINSTALLER_RESET_ENVIRONMENT = '1'
        Start-Process -FilePath $Target
        Remove-Item -LiteralPath $Staged -Force -ErrorAction SilentlyContinue
        exit 0
    } catch {
        if (Test-Path -LiteralPath $backup) {
            if (Test-Path -LiteralPath $Target) { Remove-Item -LiteralPath $Target -Force -ErrorAction SilentlyContinue }
            Move-Item -LiteralPath $backup -Destination $Target -Force -ErrorAction SilentlyContinue
        }
        Remove-Item -LiteralPath $pending -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 500
    }
}
exit 1
"""


def launch_installer(staging_dir: Path, current_executable: Path, system: str | None = None) -> None:
    if not getattr(sys, "frozen", False):
        raise UpdateError("La actualización automática solo está disponible en el ejecutable instalado.")
    system = system or platform.system()
    target = current_executable.resolve()
    if not target.is_file() or not os.access(target.parent, os.W_OK):
        raise UpdateError("La carpeta de la aplicación no permite sustituir el ejecutable.")
    if system == "Linux":
        installed = target == (Path.home() / ".local/bin/SpiderToMP3-linux-x86_64").resolve()
        helper = staging_dir / "apply-update.sh"
        helper.write_text(LINUX_HELPER, encoding="utf-8")
        helper_env = os.environ.copy()
        original_library_path = helper_env.pop("LD_LIBRARY_PATH_ORIG", None)
        if original_library_path is None:
            helper_env.pop("LD_LIBRARY_PATH", None)
        else:
            helper_env["LD_LIBRARY_PATH"] = original_library_path
        subprocess.Popen(
            ["/bin/sh", str(helper), str(os.getpid()), str(staging_dir), str(target), "yes" if installed else "no"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True, env=helper_env,
        )
    elif system == "Windows":
        helper = staging_dir / "apply-update.ps1"
        helper.write_text(WINDOWS_HELPER, encoding="utf-8-sig")
        subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-WindowStyle", "Hidden", "-File", str(helper), "-OldPid", str(os.getpid()),
             "-Staged", str(staging_dir / "SpiderToMP3.exe"), "-Target", str(target)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    else:
        raise UpdateError("La actualización automática no está disponible en este sistema.")
