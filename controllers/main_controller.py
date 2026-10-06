from __future__ import annotations

from pathlib import Path

from config import APP_NAME
from controllers.download_worker import DownloadWorker
from models import DownloadRequest, DownloadSettings
from qt import QDesktopServices, QFileDialog, QMessageBox, QThread, QUrl, Slot
from services import parse_urls
from services.validation import validate_settings
from services.privacy import redact_text


class MainController:
    def __init__(self, window) -> None:
        self.window = window
        self.thread: QThread | None = None
        self.worker: DownloadWorker | None = None
        self._close_when_finished = False
        self._selected_preview_requests: list[DownloadRequest] = []
        self._connect_view()

    def _connect_view(self) -> None:
        self.window.download_requested.connect(self.start_download)
        self.window.retry_requested.connect(self.retry_failed)
        self.window.retry_selected_requested.connect(self.retry_selected)
        self.window.resume_requested.connect(self.resume_pending)
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
        self._begin_download(parse_urls(self.window.urls_text()))

    @Slot()
    def retry_failed(self) -> None:
        requests = self.window.failed_requests()
        self._begin_download([request.url for request in requests], requests, preserve_queue=True)

    @Slot()
    def retry_selected(self) -> None:
        request = self.window.selected_request()
        if request is not None:
            self._begin_download([request.url], [request], preserve_queue=True)

    @Slot()
    def resume_pending(self) -> None:
        requests = self.window.pending_requests()
        if requests:
            self._begin_download([request.url for request in requests], requests, preserve_queue=True)

    @Slot(str)
    def ask_duplicate(self, path: str) -> None:
        if self.worker is None:
            return
        box = QMessageBox(self.window)
        box.setWindowTitle("Archivo existente")
        box.setText(f"Ya existe {path}. ¿Qué hacemos con este audio?")
        rename = box.addButton("Renombrar", QMessageBox.AcceptRole)
        skip = box.addButton("Omitir", QMessageBox.RejectRole)
        box.addButton("Cancelar descarga", QMessageBox.DestructiveRole)
        box.exec()
        decision = "rename" if box.clickedButton() is rename else "skip" if box.clickedButton() is skip else "cancel"
        self.worker.answer_duplicate(decision)

    def _begin_download(
        self,
        urls: list[str],
        retry_requests: list[DownloadRequest] | None = None,
        preserve_queue: bool = False,
    ) -> None:
        if self.is_running:
            return
        if not urls:
            self.window.set_validation_errors({"urls": "Pega al menos un enlace para empezar."})
            return
        if not self.window.output_dir_text().strip():
            self.window.set_validation_errors({"output": "Elige una carpeta de salida."})
            return

        settings = DownloadSettings(
            urls=urls,
            output_dir=Path(self.window.output_dir_text()).expanduser(),
            audio_format=self.window.audio_format(),
            audio_quality=self.window.audio_quality(),
            filename_template=self.window.filename_template(),
            include_playlist=self.window.include_playlist(),
            open_output_dir_when_done=self.window.open_output_dir_when_done(),
            retry_requests=retry_requests or [],
            preview_only=retry_requests is None,
            playlist_limit=self.window.playlist_limit(),
            network_attempts=self.window.network_attempts(),
            duplicate_policy=self.window.duplicate_policy(),
            archive_enabled=self.window.archive_enabled(),
            embed_metadata=self.window.embed_metadata(),
            embed_cover=self.window.embed_cover(),
            metadata_overrides=self.window.metadata_overrides(),
        )
        errors = validate_settings(settings)
        self.window.set_validation_errors(errors)
        if errors:
            return

        self.window.save_preferences(urls)
        self.window.prepare_download(urls, preserve=preserve_queue, retry_requests=retry_requests)
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
        if self.worker is not None and self.worker.settings.preview_only is True:
            self.window.set_current_message(message)
            self.window.set_status(message)
            if not self._close_when_finished:
                self._selected_preview_requests = self.window.choose_preview_items()
            return
        if message == "Descarga cancelada.":
            self.window.mark_active_cancelled()
        self.window.set_current_message(message)
        self.window.set_status(message)
        if message.startswith("Finalizado:") and not self._close_when_finished:
            self.window.notify_summary(message)

        if (
            success
            and not self._close_when_finished
            and self.worker is not None
            and self.worker.settings.open_output_dir_when_done
        ):
            path = self.worker.settings.output_dir.resolve()
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        elif not success and message != "Descarga cancelada." and not self._close_when_finished:
            QMessageBox.warning(self.window, APP_NAME, redact_text(message))

    @Slot()
    def thread_finished(self) -> None:
        self.thread = None
        self.worker = None
        if self._close_when_finished:
            self.window.close()
        else:
            self.window.set_running(False)
            selected = self._selected_preview_requests
            self._selected_preview_requests = []
            if selected:
                self._begin_download([request.url for request in selected], selected)

    def handle_close_request(self, event) -> None:
        if not self.is_running:
            event.accept()
            return
        if self._close_when_finished:
            event.ignore()
            return

        response = QMessageBox.question(
            self.window,
            APP_NAME,
            "Hay una descarga en marcha. ¿Quieres cancelar y cerrar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if response != QMessageBox.Yes:
            event.ignore()
            return

        self.cancel_download()
        self._close_when_finished = True
        event.ignore()

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
        self.worker.item_state.connect(self.window.update_item)
        self.worker.duplicate_question.connect(self.ask_duplicate)
        self.worker.finished.connect(self.download_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.thread_finished)
        self.thread.start()
