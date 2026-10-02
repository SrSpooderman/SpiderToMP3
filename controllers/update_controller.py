from __future__ import annotations

import os
import platform
import shutil
import sys
import tempfile
import time
from pathlib import Path

from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from config import APP_NAME, APP_VERSION
from qt import (
    QApplication, QDesktopServices, QMessageBox, QProgressDialog, QSettings,
    QTimer, QUrl, Qt,
)
from services.updater import (
    LATEST_RELEASE_URL, MAX_ASSET_BYTES, ReleaseUpdate, UpdateError,
    expected_checksum, launch_installer, prepare_linux_package,
    release_from_json, verify_download,
)


class UpdateController:
    def __init__(self, window, download_controller) -> None:
        self.window = window
        self.download_controller = download_controller
        self.manager = QNetworkAccessManager(window)
        self.settings = QSettings(APP_NAME, APP_NAME)
        self.reply: QNetworkReply | None = None
        self.state = ""
        self.manual = False
        self.buffer = bytearray()
        self.release: ReleaseUpdate | None = None
        self.checksum = ""
        self.stage: Path | None = None
        self.output = None
        self.progress: QProgressDialog | None = None
        self.cancelled = False
        window.check_updates_requested.connect(lambda: self.check(manual=True))
        window.close_requested.connect(self._on_close)

    def start_auto_check(self) -> None:
        if not getattr(sys, "frozen", False):
            return
        last = float(self.settings.value("updates/last_check", 0) or 0)
        if time.time() - last >= 24 * 60 * 60:
            QTimer.singleShot(2000, lambda: self.check(manual=False))

    def check(self, manual: bool = True) -> None:
        if self.reply is not None:
            if manual:
                self.window.set_status("Ya se está comprobando o descargando una actualización.")
            return
        self.manual = manual
        self.release = None
        self.window.set_status("Buscando actualizaciones...")
        self._request(LATEST_RELEASE_URL, "release")

    def _request(self, url: str, state: str) -> None:
        if state == "asset":
            assert self.stage is not None and self.release is not None
            self.output = (self.stage / self.release.asset_name).open("wb")
        request = QNetworkRequest(QUrl(url))
        request.setRawHeader(b"User-Agent", b"SpiderToMP3-updater")
        request.setRawHeader(b"Accept", b"application/vnd.github+json" if state == "release" else b"application/octet-stream")
        request.setTransferTimeout(30_000)
        self.state = state
        self.buffer.clear()
        self.reply = self.manager.get(request)
        self.reply.readyRead.connect(self._read)
        self.reply.finished.connect(self._finished)
        if state == "asset":
            self.reply.downloadProgress.connect(self._update_progress)

    def _read(self) -> None:
        if self.reply is None:
            return
        chunk = bytes(self.reply.readAll())
        if self.state == "asset":
            try:
                if self.output is None or self.output.tell() + len(chunk) > MAX_ASSET_BYTES:
                    raise UpdateError("La descarga supera el tamaño permitido.")
                self.output.write(chunk)
            except (OSError, UpdateError) as exc:
                self._fail(str(exc))
        else:
            if len(self.buffer) + len(chunk) > 1024 * 1024:
                self._fail("La respuesta de actualización es demasiado grande.")
            else:
                self.buffer.extend(chunk)

    def _finished(self) -> None:
        reply = self.reply
        if reply is None:
            return
        self._read()
        if self.reply is None:
            return
        self.reply = None
        reply.deleteLater()
        if self.cancelled:
            self._cleanup()
            self.window.set_status("Actualización cancelada.")
            return
        status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        if reply.error() != QNetworkReply.NetworkError.NoError or status != 200:
            self._fail(f"No se pudo consultar GitHub (HTTP {status or 'sin respuesta'}).")
            return
        try:
            if self.state == "release":
                self.settings.setValue("updates/last_check", time.time())
                release = release_from_json(bytes(self.buffer))
                if release is None:
                    self.window.set_status(f"{APP_NAME} {APP_VERSION} está actualizado.")
                    if self.manual:
                        QMessageBox.information(self.window, "Actualizaciones", f"Ya tienes la versión más reciente ({APP_VERSION}).")
                    return
                self.release = release
                self._offer_update(release)
            elif self.state == "checksums":
                assert self.release is not None
                self.checksum = expected_checksum(bytes(self.buffer), self.release.asset_name)
                self._request(self.release.asset_url, "asset")
            elif self.state == "asset":
                self._finish_download()
        except (OSError, UpdateError) as exc:
            self._fail(str(exc))

    def _offer_update(self, release: ReleaseUpdate) -> None:
        box = QMessageBox(self.window)
        box.setWindowTitle("Nueva versión disponible")
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.setText(f"SpiderToMP3 {release.version} está disponible.\n\n{release.notes[:3000]}")
        install = box.addButton("Actualizar", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Más tarde", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is not install:
            self.window.set_status("Actualización pospuesta.")
            return
        if not getattr(sys, "frozen", False):
            QDesktopServices.openUrl(QUrl(release.page_url))
            return
        if self.download_controller.is_running:
            QMessageBox.information(self.window, "Actualizaciones", "Termina o cancela la descarga de audio antes de actualizar.")
            return
        if not os.access(Path(sys.executable).resolve().parent, os.W_OK):
            QMessageBox.warning(self.window, "Actualizaciones", "No tienes permiso para sustituir el ejecutable. Descarga la Release e instálala manualmente.")
            QDesktopServices.openUrl(QUrl(release.page_url))
            return
        self.stage = Path(tempfile.mkdtemp(prefix="spidertomp3-update-"))
        self.cancelled = False
        self.progress = QProgressDialog("Descargando actualización...", "Cancelar", 0, 100, self.window)
        self.progress.setWindowTitle("Actualizando SpiderToMP3")
        self.progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress.setMinimumDuration(0)
        self.progress.canceled.connect(self._cancel)
        self.progress.show()
        self._request(release.checksums_url, "checksums")

    def _update_progress(self, received: int, total: int) -> None:
        if self.progress is not None:
            size = self.release.asset_size if self.release else total
            self.progress.setValue(min(99, int(received * 100 / size)) if size else 0)

    def _finish_download(self) -> None:
        assert self.release is not None and self.stage is not None
        if self.output is not None:
            self.output.close()
            self.output = None
        archive = self.stage / self.release.asset_name
        verify_download(archive, self.release, self.checksum)
        if platform.system() == "Linux":
            prepare_linux_package(archive, self.stage)
            archive.unlink()
        else:
            archive.rename(self.stage / "SpiderToMP3.exe")
        if self.download_controller.is_running:
            raise UpdateError("Hay una descarga de audio en curso. Inténtalo de nuevo al terminar.")
        launch_installer(self.stage, Path(sys.executable))
        self.stage = None  # El proceso auxiliar usa esta carpeta tras el cierre.
        if self.progress is not None:
            self.progress.hide()
            self.progress.deleteLater()
            self.progress = None
        self.window.set_status("Instalando actualización...")
        QApplication.instance().quit()

    def _cancel(self) -> None:
        self.cancelled = True
        if self.reply is not None:
            self.reply.abort()
        else:
            self._cleanup()

    def _on_close(self, event) -> None:
        if event.isAccepted() and self.reply is not None:
            self.cancelled = True
            self.reply.abort()

    def _cleanup(self) -> None:
        if self.output is not None:
            self.output.close()
            self.output = None
        if self.progress is not None:
            self.progress.hide()
            self.progress.deleteLater()
            self.progress = None
        if self.stage is not None:
            shutil.rmtree(self.stage, ignore_errors=True)
            self.stage = None

    def _fail(self, message: str) -> None:
        if self.reply is not None:
            self.reply.abort()
            self.reply.deleteLater()
            self.reply = None
        self._cleanup()
        self.window.set_status(message)
        if self.manual or self.release is not None:
            QMessageBox.warning(self.window, "Actualizaciones", message)
