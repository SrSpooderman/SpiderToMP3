#!/bin/sh
set -eu

bundle_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
install_root=${SPIDER_INSTALL_HOME:-$HOME}
install -Dm755 "$bundle_dir/SpiderToMP3-linux-x86_64" "$install_root/.local/bin/SpiderToMP3-linux-x86_64"
install -Dm644 "$bundle_dir/spidertomp3.svg" "$install_root/.local/share/icons/hicolor/scalable/apps/spidertomp3.svg"
install -Dm644 "$bundle_dir/spidertomp3.desktop" "$install_root/.local/share/applications/spidertomp3.desktop"
sed -i "s|^Exec=.*|Exec=$install_root/.local/bin/SpiderToMP3-linux-x86_64|" "$install_root/.local/share/applications/spidertomp3.desktop"
echo "SpiderToMP3 instalado en tu usuario. Abre la app desde el menú o ejecuta ~/.local/bin/SpiderToMP3-linux-x86_64."
