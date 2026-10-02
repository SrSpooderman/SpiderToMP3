#!/bin/sh
set -eu

bundle_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
install_root=${SPIDER_INSTALL_HOME:-$HOME}
binary="$install_root/.local/bin/SpiderToMP3-linux-x86_64"
icon="$install_root/.local/share/icons/hicolor/256x256/apps/spidertomp3.png"
launcher="$install_root/.local/share/applications/spidertomp3.desktop"
install -Dm755 "$bundle_dir/SpiderToMP3-linux-x86_64" "$binary"
install -Dm644 "$bundle_dir/spidertomp3.svg" "$install_root/.local/share/icons/hicolor/scalable/apps/spidertomp3.svg"
mkdir -p "$(dirname -- "$icon")"
QT_QPA_PLATFORM=offscreen "$binary" --write-menu-icon "$icon"
chmod 644 "$icon"
install -Dm644 "$bundle_dir/spidertomp3.desktop" "$launcher"
sed -i "s|^Exec=.*|Exec=\"$binary\"|" "$launcher"
sed -i "s|^Icon=.*|Icon=$icon|" "$launcher"
if command -v kbuildsycoca6 >/dev/null 2>&1 && [ -z "${SPIDER_INSTALL_HOME:-}" ]; then
    env -u LC_ALL kbuildsycoca6 --noincremental >/dev/null 2>&1 || true
fi
echo "SpiderToMP3 instalado en tu usuario. Abre la app desde el menú o ejecuta $binary."
