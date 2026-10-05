#!/bin/sh
set -eu

install_root=${SPIDER_INSTALL_HOME:-$HOME}
binary="$install_root/.local/bin/SpiderToMP3-linux-x86_64"
rm -f -- \
    "$binary" \
    "$install_root/.local/share/icons/hicolor/256x256/apps/spidertomp3.png" \
    "$install_root/.local/share/icons/hicolor/scalable/apps/spidertomp3.svg" \
    "$install_root/.local/share/applications/spidertomp3.desktop"
for old_binary in "$binary".previous* "$binary".update-error; do
    if [ -f "$old_binary" ]; then
        rm -f -- "$old_binary"
    fi
done
if command -v kbuildsycoca6 >/dev/null 2>&1 && [ -z "${SPIDER_INSTALL_HOME:-}" ]; then
    env -u LC_ALL kbuildsycoca6 --noincremental >/dev/null 2>&1 || true
fi
echo "SpiderToMP3 desinstalado. Las preferencias y archivos descargados se han conservado."
