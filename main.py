from __future__ import annotations

import sys

from config import APP_NAME
from controllers import MainController
from qt import QApplication
from views.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = MainWindow()
    window.controller = MainController(window)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
