from __future__ import annotations

import traceback

from spidertomp3.models import DownloadSettings
from spidertomp3.qt import QObject, Signal, Slot
from spidertomp3.services.download_service import DownloadCancelled, DownloadService


class DownloadWorker(QObject):
    log = Signal(str)
    progress = Signal(int)
    current_title = Signal(str)
    item_done = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, settings: DownloadSettings) -> None:
        super().__init__()
        self.settings = settings
        self._cancelled = False

    @Slot()
    def run(self) -> None:
        try:
            DownloadService(self).download(self.settings)
        except DownloadCancelled:
            self.finished.emit(False, "Descarga cancelada.")
        except Exception as exc:
            self.log.emit(traceback.format_exc())
            message = str(exc) or "Algo fallo durante la descarga."
            self.finished.emit(False, message)
        else:
            self.finished.emit(True, "Todo listo. La telarana musical esta servida.")

    def cancel(self) -> None:
        self._cancelled = True

    def should_cancel(self) -> bool:
        return self._cancelled

    def emit_log(self, message: str) -> None:
        self.log.emit(message)

    def emit_progress(self, value: int) -> None:
        self.progress.emit(value)

    def emit_current_title(self, title: str) -> None:
        self.current_title.emit(title)

    def emit_item_done(self, title: str) -> None:
        self.item_done.emit(title)
