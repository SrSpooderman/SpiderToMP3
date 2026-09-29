from __future__ import annotations

import sys
from pathlib import Path

from config import (
    APP_NAME,
    APP_VERSION,
    AUDIO_FORMATS,
    DEFAULT_FILENAME_TEMPLATE,
    DEFAULT_OUTPUT_DIR,
    QUALITY_OPTIONS,
    WINDOW_TITLE,
)
from qt import (
    QApplication,
    QAction,
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    Qt,
    Signal,
    Slot,
    QIcon,
    QSettings,
)
from views.styles import APP_STYLESHEET
from models import DownloadRequest


class MainWindow(QMainWindow):
    download_requested = Signal()
    cancel_requested = Signal()
    clear_requested = Signal()
    output_dir_requested = Signal()
    retry_requested = Signal()
    close_requested = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._settings = QSettings(APP_NAME, APP_NAME)
        self._queue_items: dict[str, QListWidgetItem] = {}
        self.setWindowTitle(WINDOW_TITLE)
        asset_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
        self.setWindowIcon(QIcon(str(asset_root / "assets" / "spidertomp3.svg")))
        self.resize(980, 680)
        self.setMinimumSize(760, 540)

        self._create_widgets()
        self._build_layout()
        self._connect_signals()
        self._build_menu()
        self._restore_preferences()
        self._apply_style()

    def _create_widgets(self) -> None:
        self.url_edit = QTextEdit()
        self.url_edit.setPlaceholderText(
            "Pega aquí uno o varios enlaces, uno por línea.\n"
            "YouTube, listas, podcasts públicos... lo que yt-dlp entienda."
        )

        self.queue_list = QListWidget()
        self.queue_list.setAlternatingRowColors(True)
        self.queue_list.setAccessibleName("Cola de audios")

        self.output_edit = QLineEdit(str(DEFAULT_OUTPUT_DIR))
        self.browse_button = QPushButton("Elegir carpeta")

        self.format_combo = QComboBox()
        self.format_combo.addItems(AUDIO_FORMATS)

        self.quality_combo = QComboBox()
        self._update_quality_options()

        self.template_edit = QLineEdit(DEFAULT_FILENAME_TEMPLATE)
        self.playlist_check = QCheckBox("Permitir playlists")
        self.open_when_done_check = QCheckBox("Abrir carpeta al terminar")
        self.open_when_done_check.setChecked(True)

        self.start_button = QPushButton("Descargar")
        self.retry_button = QPushButton("Reintentar fallidos")
        self.retry_button.setEnabled(False)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setEnabled(False)
        self.clear_button = QPushButton("Limpiar")
        self.recent_combo = QComboBox()
        self.recent_combo.setAccessibleName("Enlaces recientes")
        self.use_recent_button = QPushButton("Añadir reciente")
        self.clear_history_button = QPushButton("Borrar historial")
        self.output_error = QLabel()
        self.url_error = QLabel()
        self.format_error = QLabel()
        self.template_error = QLabel()
        for label in (self.url_error, self.output_error, self.format_error, self.template_error):
            label.setObjectName("Error")
            label.setWordWrap(True)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setAccessibleName("Progreso total")

        self.current_label = QLabel("Esperando enlaces.")
        self.current_label.setWordWrap(True)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(1000)
        self.log_view.setPlaceholderText("Aquí aparecerá la actividad de descarga.")
        self.log_view.setAccessibleName("Actividad de descarga")
        self.copy_log_button = QPushButton("Copiar registro")

        self.statusBar().showMessage("Preparado")

    def _build_layout(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 18, 18, 14)
        root.setSpacing(12)

        root.addLayout(self._build_header())
        root.addWidget(self._build_splitter(), 1)
        root.addLayout(self._build_download_controls())
        root.addWidget(self.current_label)
        self.setCentralWidget(central)

    def _build_header(self) -> QVBoxLayout:
        title = QLabel(APP_NAME)
        title.setObjectName("Title")
        subtitle = QLabel("Convierte enlaces a audio con una interfaz simple y cero rituales raros.")
        subtitle.setObjectName("Subtitle")

        header = QVBoxLayout()
        header.addWidget(title)
        header.addWidget(subtitle)
        return header

    def _build_splitter(self) -> QSplitter:
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([560, 360])
        return splitter

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 10, 0)
        layout.setSpacing(10)

        url_label = QLabel("Enlaces")
        url_label.setBuddy(self.url_edit)
        layout.addWidget(url_label)
        layout.addWidget(self.url_edit, 3)
        layout.addWidget(self.url_error)
        history = QHBoxLayout()
        history.addWidget(self.recent_combo, 1)
        history.addWidget(self.use_recent_button)
        history.addWidget(self.clear_history_button)
        layout.addLayout(history)
        output_label = QLabel("Carpeta de salida")
        output_label.setBuddy(self.output_edit)
        layout.addWidget(output_label)
        layout.addLayout(self._build_output_row())
        layout.addWidget(self.output_error)
        layout.addLayout(self._build_options_grid())
        layout.addWidget(self.format_error)
        layout.addWidget(self.template_error)
        layout.addWidget(self._build_ffmpeg_hint())
        return panel

    def _build_output_row(self) -> QHBoxLayout:
        output_row = QHBoxLayout()
        output_row.addWidget(self.output_edit, 1)
        output_row.addWidget(self.browse_button)
        return output_row

    def _build_options_grid(self) -> QGridLayout:
        options = QGridLayout()
        options.setHorizontalSpacing(12)
        options.setVerticalSpacing(8)
        format_label = QLabel("Formato")
        format_label.setBuddy(self.format_combo)
        options.addWidget(format_label, 0, 0)
        options.addWidget(self.format_combo, 0, 1)
        quality_label = QLabel("Calidad")
        quality_label.setBuddy(self.quality_combo)
        options.addWidget(quality_label, 0, 2)
        options.addWidget(self.quality_combo, 0, 3, 1, 2)
        name_label = QLabel("Nombre")
        name_label.setBuddy(self.template_edit)
        options.addWidget(name_label, 1, 0)
        options.addWidget(self.template_edit, 1, 1, 1, 4)
        options.addWidget(self.playlist_check, 2, 1)
        options.addWidget(self.open_when_done_check, 2, 2, 1, 3)
        return options

    def _build_ffmpeg_hint(self) -> QLabel:
        hint = QLabel("Para convertir audio hacen falta FFmpeg y ffprobe en el PATH.")
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        self.ffmpeg_hint = hint
        return hint

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Cola"))
        layout.addWidget(self.queue_list, 1)
        activity_header = QHBoxLayout()
        activity_header.addWidget(QLabel("Actividad"))
        activity_header.addStretch(1)
        activity_header.addWidget(self.copy_log_button)
        layout.addLayout(activity_header)
        layout.addWidget(self.log_view, 2)
        return panel

    def _build_download_controls(self) -> QHBoxLayout:
        controls = QHBoxLayout()
        controls.addWidget(self.start_button)
        controls.addWidget(self.retry_button)
        controls.addWidget(self.cancel_button)
        controls.addWidget(self.clear_button)
        controls.addStretch(1)
        controls.addWidget(self.progress, 2)
        return controls

    def _connect_signals(self) -> None:
        self.start_button.clicked.connect(self.download_requested.emit)
        self.retry_button.clicked.connect(self.retry_requested.emit)
        self.cancel_button.clicked.connect(self.cancel_requested.emit)
        self.clear_button.clicked.connect(self.clear_requested.emit)
        self.browse_button.clicked.connect(self.output_dir_requested.emit)
        self.format_combo.currentTextChanged.connect(self._update_quality_options)
        self.use_recent_button.clicked.connect(self._use_recent)
        self.clear_history_button.clicked.connect(self.clear_history)
        self.copy_log_button.clicked.connect(self.copy_log)

    def _build_menu(self) -> None:
        about = QAction("Acerca de SpiderToMP3", self)
        about.triggered.connect(self._show_about)
        self.menuBar().addMenu("Ayuda").addAction(about)

    def _show_about(self) -> None:
        QMessageBox.about(
            self, f"Acerca de {APP_NAME}",
            f"{APP_NAME} {APP_VERSION}\nDescarga y convierte audio con yt-dlp y FFmpeg.",
        )

    def copy_log(self) -> None:
        QApplication.clipboard().setText(self.log_view.toPlainText())
        self.statusBar().showMessage("Registro copiado al portapapeles.", 4000)

    def _apply_style(self) -> None:
        QApplication.instance().setStyleSheet(APP_STYLESHEET)

    def urls_text(self) -> str:
        return self.url_edit.toPlainText()

    def output_dir_text(self) -> str:
        return self.output_edit.text()

    def set_output_dir(self, path: str) -> None:
        self.output_edit.setText(path)

    def audio_format(self) -> str:
        return self.format_combo.currentText()

    def audio_quality(self) -> int | None:
        return self.quality_combo.currentData()

    def filename_template(self) -> str:
        return self.template_edit.text().strip()

    def include_playlist(self) -> bool:
        return self.playlist_check.isChecked()

    def open_output_dir_when_done(self) -> bool:
        return self.open_when_done_check.isChecked()

    def prepare_download(self, urls: list[str]) -> None:
        self.queue_list.clear()
        self._queue_items.clear()
        self.log_view.clear()
        self.progress.setValue(0)
        self.current_label.setText("Analizando enlaces...")
        self.retry_button.setEnabled(False)

    def clear_form(self) -> None:
        self.url_edit.clear()
        self.queue_list.clear()
        self._queue_items.clear()
        self.log_view.clear()
        self.retry_button.setEnabled(False)

    @Slot(str)
    def append_log(self, text: str) -> None:
        self.log_view.appendPlainText(text)
        bar = self.log_view.verticalScrollBar()
        bar.setValue(bar.maximum())

    @Slot(int)
    def set_progress(self, value: int) -> None:
        self.progress.setValue(value)

    @Slot(str)
    def set_current_title(self, title: str) -> None:
        self.current_label.setText(f"Ahora: {title}")

    @Slot(str)
    def set_current_message(self, message: str) -> None:
        self.current_label.setText(message)

    @Slot(str)
    def mark_item_done(self, title: str) -> None:
        self.statusBar().showMessage(f"Convertido: {title}", 4500)

    @Slot(str, str, str, object)
    def update_item(self, key: str, title: str, state: str, target: object) -> None:
        labels = {
            "pendiente": "Pendiente", "descargando": "Descargando",
            "convirtiendo": "Convirtiendo", "completado": "Completado",
            "fallido": "Fallido", "cancelado": "Cancelado",
        }
        item = self._queue_items.get(key)
        if item is None:
            item = QListWidgetItem()
            self._queue_items[key] = item
            self.queue_list.addItem(item)
        if isinstance(target, str):
            target = {"url": target, "playlist_path": []}
        if not isinstance(target, dict):
            return
        error = str(target.get("error", ""))
        item.setText(f"{labels.get(state, state)} · {title}" + (f" — {error}" if error else ""))
        item.setToolTip(error)
        item.setData(Qt.UserRole, target)
        item.setData(Qt.UserRole + 1, state)
        item.setData(Qt.UserRole + 2, title)
        if state == "fallido":
            self.retry_button.setEnabled(True)

    def failed_requests(self) -> list[DownloadRequest]:
        requests: list[DownloadRequest] = []
        for item in self._queue_items.values():
            if item.data(Qt.UserRole + 1) != "fallido":
                continue
            target = item.data(Qt.UserRole)
            requests.append(DownloadRequest(
                target["url"], tuple(target.get("playlist_path", ())), target.get("expected_id")
            ))
        return list(dict.fromkeys(requests))

    def failed_urls(self) -> list[str]:
        return list(dict.fromkeys(request.url for request in self.failed_requests()))

    def mark_active_cancelled(self) -> None:
        for key, item in self._queue_items.items():
            state = item.data(Qt.UserRole + 1)
            if state in {"pendiente", "descargando", "convirtiendo"}:
                self.update_item(key, item.data(Qt.UserRole + 2), "cancelado", item.data(Qt.UserRole))

    def set_validation_errors(self, errors: dict[str, str]) -> None:
        self.url_error.setText(errors.get("urls", ""))
        self.output_error.setText(errors.get("output", ""))
        self.format_error.setText(errors.get("format", ""))
        self.template_error.setText(errors.get("template", ""))
        self.ffmpeg_hint.setText(errors.get("ffmpeg", "Para convertir audio hacen falta FFmpeg y ffprobe en el PATH."))
        self.ffmpeg_hint.setObjectName("Error" if "ffmpeg" in errors else "Hint")
        self.ffmpeg_hint.style().unpolish(self.ffmpeg_hint)
        self.ffmpeg_hint.style().polish(self.ffmpeg_hint)
        if "urls" in errors:
            self.url_edit.setFocus()
        elif "output" in errors:
            self.output_edit.setFocus()
        elif "template" in errors:
            self.template_edit.setFocus()
        elif "format" in errors:
            self.format_combo.setFocus()
        if errors:
            self.statusBar().showMessage(next(iter(errors.values())))

    def _update_quality_options(self, *_args) -> None:
        selected = self.quality_combo.currentData() if hasattr(self, "quality_combo") else None
        self.quality_combo.clear()
        for label, value in QUALITY_OPTIONS[self.audio_format()]:
            self.quality_combo.addItem(label, value)
        for index in range(self.quality_combo.count()):
            if self.quality_combo.itemData(index) == selected:
                self.quality_combo.setCurrentIndex(index)
                break

    def _restore_preferences(self) -> None:
        self.output_edit.setText(str(self._settings.value("output_dir", str(DEFAULT_OUTPUT_DIR))))
        self.template_edit.setText(str(self._settings.value("template", DEFAULT_FILENAME_TEMPLATE)))
        index = self.format_combo.findText(str(self._settings.value("format", AUDIO_FORMATS[0])))
        if index >= 0:
            self.format_combo.setCurrentIndex(index)
        quality = self._settings.value("quality", None)
        for index in range(self.quality_combo.count()):
            if str(self.quality_combo.itemData(index)) == str(quality):
                self.quality_combo.setCurrentIndex(index)
                break
        self.playlist_check.setChecked(self._settings.value("playlist", False, type=bool))
        self.open_when_done_check.setChecked(self._settings.value("open_when_done", True, type=bool))
        self.recent_combo.addItems(self._settings.value("recent_urls", [], type=list))

    def save_preferences(self, urls: list[str]) -> None:
        self._settings.setValue("output_dir", self.output_dir_text())
        self._settings.setValue("template", self.filename_template())
        self._settings.setValue("format", self.audio_format())
        self._settings.setValue("quality", self.audio_quality())
        self._settings.setValue("playlist", self.include_playlist())
        self._settings.setValue("open_when_done", self.open_output_dir_when_done())
        recent = list(dict.fromkeys(urls + [self.recent_combo.itemText(i) for i in range(self.recent_combo.count())]))[:20]
        self._settings.setValue("recent_urls", recent)
        self.recent_combo.clear()
        self.recent_combo.addItems(recent)

    def clear_history(self) -> None:
        self._settings.remove("recent_urls")
        self.recent_combo.clear()

    def _use_recent(self) -> None:
        url = self.recent_combo.currentText()
        if url and url not in self.urls_text().splitlines():
            self.url_edit.append(url)

    def set_status(self, message: str) -> None:
        self.statusBar().showMessage(message)

    def set_cancel_enabled(self, enabled: bool) -> None:
        self.cancel_button.setEnabled(enabled)

    def set_running(self, running: bool) -> None:
        self.start_button.setEnabled(not running)
        self.retry_button.setEnabled(not running and bool(self.failed_urls()))
        self.cancel_button.setEnabled(running)
        self.clear_button.setEnabled(not running)
        self.browse_button.setEnabled(not running)
        self.url_edit.setReadOnly(running)
        self.output_edit.setReadOnly(running)
        self.template_edit.setReadOnly(running)
        self.format_combo.setEnabled(not running)
        self.quality_combo.setEnabled(not running)
        self.playlist_check.setEnabled(not running)
        self.open_when_done_check.setEnabled(not running)
        self.recent_combo.setEnabled(not running)
        self.use_recent_button.setEnabled(not running)
        self.clear_history_button.setEnabled(not running)
        self.statusBar().showMessage("Descargando..." if running else "Preparado")

    def closeEvent(self, event) -> None:
        self.close_requested.emit(event)
