from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from config import APP_NAME, APP_VERSION


def write_menu_icon(destination: Path) -> int:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    asset_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    renderer = QSvgRenderer(str(asset_root / "assets" / "spidertomp3-icon.svg"))
    if not renderer.isValid():
        return 1
    image = QImage(256, 256, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    return 0 if image.save(str(destination), "PNG") else 1


def repair_installed_menu_icon(home: Path, executable: Path) -> bool:
    expected = home / ".local/bin/SpiderToMP3-linux-x86_64"
    launcher = home / ".local/share/applications/spidertomp3.desktop"
    if executable.resolve() != expected.resolve() or not launcher.is_file():
        return False
    entry = launcher.read_text(encoding="utf-8")
    old_icon = "Icon=spidertomp3\n"
    if old_icon not in entry:
        return False
    icon = home / ".local/share/icons/hicolor/256x256/apps/spidertomp3.png"
    icon.parent.mkdir(parents=True, exist_ok=True)
    if write_menu_icon(icon) != 0:
        return False
    icon.chmod(0o644)
    launcher.write_text(entry.replace(old_icon, f"Icon={icon}\n", 1), encoding="utf-8")
    return True


def main(smoke_test: bool = False) -> int:
    if sys.platform.startswith("linux") and getattr(sys, "frozen", False):
        try:
            repaired = repair_installed_menu_icon(Path.home(), Path(sys.executable))
            if repaired and shutil.which("kbuildsycoca6"):
                locale_env = os.environ.copy()
                locale_env.pop("LC_ALL", None)
                subprocess.run(
                    ["kbuildsycoca6", "--noincremental"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=10,
                    check=False,
                    env=locale_env,
                )
        except (OSError, subprocess.TimeoutExpired):
            pass
    from controllers import MainController
    from controllers.update_controller import UpdateController
    from qt import QApplication, QTimer
    from views.main_window import MainWindow

    app = QApplication([sys.argv[0]] if smoke_test else sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    window = MainWindow()
    window.controller = MainController(window)
    window.update_controller = UpdateController(window, window.controller)
    window.show()
    if getattr(sys, "frozen", False) and not smoke_test:
        error_file = Path(str(sys.executable) + ".update-error")
        if error_file.is_file():
            from qt import QMessageBox

            try:
                message = error_file.read_text(encoding="utf-8-sig")
                error_file.unlink()
                QTimer.singleShot(0, lambda: QMessageBox.warning(window, "Actualización", message))
            except OSError:
                pass
    if smoke_test:
        QTimer.singleShot(0, app.quit)
    else:
        window.update_controller.start_auto_check()
    return app.exec()


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--write-menu-icon":
        raise SystemExit(write_menu_icon(Path(sys.argv[2])))
    if "--version" in sys.argv:
        if sys.stdout is not None:
            print(f"{APP_NAME} {APP_VERSION}")
        raise SystemExit(0)
    if "--download-worker" in sys.argv:
        if sys.stdout is None:
            sys.stdout = open(os.devnull, "w")
        if sys.stderr is None:
            sys.stderr = open(os.devnull, "w")
        from services.worker_process import main as worker_main

        raise SystemExit(worker_main())
    raise SystemExit(main(smoke_test="--smoke-test" in sys.argv))
