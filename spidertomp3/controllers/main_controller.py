from __future__ import annotations

from pathlib import Path

from spidertomp3.config import APP_NAME
from spidertomp3.controllers.download_worker import DownloadWorker
from spidertomp3.models import DownloadSettings
from spidertomp3.qt import QDesktopServices, QFileDialog, QMessageBox, QThread, QUrl, Slot
from spidertomp3.services import parse_urls


class MainController:
    def __init__(self, window) -> None:
        self.window = window
        self.thread: QThread | None = None
        self.worker: DownloadWorker | None = None
        self._connect_view()

    def _connect_view(self) -> None:
        self.window.download_requested.connect(self.start_download)
        self.window.cancel_requested.connect(self.cancel_download)
        self.window.clear_requested.connect(self.clear_all)
        self.window.output_dir_requested.connect(self.choose_output_dir)
        self.window.close_requested.connect(self.handle_close_request)

    @Slot()
    def choose_output_dir(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self.window,
            "Elige carpeta de salida",
            self.window.output_dir_text(),
        )
        if selected:
            self.window.set_output_dir(selected)

    @Slot()
    def clear_all(self) -> None:
        if self.is_running:
            return
        self.window.clear_form()
        self.window.set_progress(0)
        self.window.set_current_message("Limpio. Como si nada hubiera pasado.")
        self.window.set_status("Preparado")

    @Slot()
    def start_download(self) -> None:
        urls = parse_urls(self.window.urls_text())
        if not urls:
            QMessageBox.information(self.window, APP_NAME, "Pega al menos un enlace para empezar.")
            return

        template = self.window.filename_template()
        if not template:
            QMessageBox.warning(self.window, APP_NAME, "El patron de nombre no puede estar vacio.")
            return

        settings = DownloadSettings(
            urls=urls,
            output_dir=Path(self.window.output_dir_text()).expanduser(),
            audio_format=self.window.audio_format(),
            audio_quality=self.window.audio_quality(),
            filename_template=template,
            include_playlist=self.window.include_playlist(),
            open_output_dir_when_done=self.window.open_output_dir_when_done(),
        )

        self.window.prepare_download(urls)
        self.window.set_running(True)
        self._start_worker(settings)

    @Slot()
    def cancel_download(self) -> None:
        if self.worker is not None:
            self.worker.cancel()
            self.window.set_status("Cancelando...")
            self.window.set_cancel_enabled(False)

    @Slot(bool, str)
    def download_finished(self, success: bool, message: str) -> None:
        self.window.set_running(False)
        self.window.set_current_message(message)
        self.window.set_status(message)

        if success and self.window.open_output_dir_when_done():
            path = Path(self.window.output_dir_text()).expanduser().resolve()
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        elif not success:
            QMessageBox.warning(self.window, APP_NAME, message)

    @Slot()
    def thread_finished(self) -> None:
        self.thread = None
        self.worker = None

    def handle_close_request(self, event) -> None:
        if not self.is_running:
            event.accept()
            return

        response = QMessageBox.question(
            self.window,
            APP_NAME,
            "Hay una descarga en marcha. Quieres cancelar y cerrar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if response != QMessageBox.Yes:
            event.ignore()
            return

        self.cancel_download()
        if self.thread is not None:
            self.thread.quit()
            self.thread.wait(3000)
        event.accept()

    @property
    def is_running(self) -> bool:
        return self.thread is not None

    def _start_worker(self, settings: DownloadSettings) -> None:
        self.thread = QThread(self.window)
        self.worker = DownloadWorker(settings)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.log.connect(self.window.append_log)
        self.worker.progress.connect(self.window.set_progress)
        self.worker.current_title.connect(self.window.set_current_title)
        self.worker.item_done.connect(self.window.mark_item_done)
        self.worker.finished.connect(self.download_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.thread_finished)
        self.thread.start()
