from __future__ import annotations

import sys

from spidertomp3.config import APP_NAME
from spidertomp3.controllers import MainController
from spidertomp3.qt import QApplication
from spidertomp3.views.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = MainWindow()
    window.controller = MainController(window)
    window.show()
    return app.exec()
