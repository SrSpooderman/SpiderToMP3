# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


project = Path(SPECPATH).parent
a = Analysis(
    [str(project / "main.py")],
    pathex=[str(project)],
    binaries=[],
    datas=[(str(project / "assets/spidertomp3-icon.svg"), "assets")],
    hiddenimports=collect_submodules("yt_dlp"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# La biblioteca empaquetada en Ubuntu puede chocar con la pila X11 de Fedora/Bazzite.
# Qt carga la copia del sistema, disponible en los escritorios compatibles.
a.binaries = [entry for entry in a.binaries if Path(entry[0]).name != "libxkbcommon.so.0"]

pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="SpiderToMP3-linux-x86_64",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)
