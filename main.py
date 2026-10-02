from __future__ import annotations

import os
import sys

from config import APP_NAME, APP_VERSION


def main(smoke_test: bool = False) -> int:
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
    if smoke_test:
        QTimer.singleShot(0, app.quit)
    else:
        window.update_controller.start_auto_check()
    return app.exec()


if __name__ == "__main__":
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
