from __future__ import annotations

from config import (
    APP_NAME,
    AUDIO_FORMATS,
    DEFAULT_FILENAME_TEMPLATE,
    DEFAULT_OUTPUT_DIR,
    WINDOW_TITLE,
)
from qt import (
    QApplication,
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSlider,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    Qt,
    Signal,
    Slot,
)
from views.styles import APP_STYLESHEET


class MainWindow(QMainWindow):
    download_requested = Signal()
    cancel_requested = Signal()
    clear_requested = Signal()
    output_dir_requested = Signal()
    close_requested = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(980, 680)
        self.setMinimumSize(760, 540)

        self._create_widgets()
        self._build_layout()
        self._connect_signals()
        self._apply_style()

    def _create_widgets(self) -> None:
        self.url_edit = QTextEdit()
        self.url_edit.setPlaceholderText(
            "Pega aqui uno o varios enlaces, uno por linea.\n"
            "YouTube, playlists, podcasts publicos... lo que yt-dlp entienda."
        )

        self.queue_list = QListWidget()
        self.queue_list.setAlternatingRowColors(True)

        self.output_edit = QLineEdit(str(DEFAULT_OUTPUT_DIR))
        self.browse_button = QPushButton("Elegir carpeta")

        self.format_combo = QComboBox()
        self.format_combo.addItems(AUDIO_FORMATS)

        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(0, 9)
        self.quality_slider.setValue(5)
        self.quality_slider.setTickPosition(QSlider.TicksBelow)
        self.quality_slider.setTickInterval(1)
        self.quality_label = QLabel("5")

        self.template_edit = QLineEdit(DEFAULT_FILENAME_TEMPLATE)
        self.playlist_check = QCheckBox("Permitir playlists")
        self.open_when_done_check = QCheckBox("Abrir carpeta al terminar")
        self.open_when_done_check.setChecked(True)

        self.start_button = QPushButton("Descargar")
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setEnabled(False)
        self.clear_button = QPushButton("Limpiar")

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        self.current_label = QLabel("Esperando enlaces. La arana aun esta tomando cafe.")
        self.current_label.setWordWrap(True)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Aqui apareceran los logs de descarga.")

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

        layout.addWidget(QLabel("Enlaces"))
        layout.addWidget(self.url_edit, 3)
        layout.addWidget(QLabel("Carpeta de salida"))
        layout.addLayout(self._build_output_row())
        layout.addLayout(self._build_options_grid())
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
        options.addWidget(QLabel("Formato"), 0, 0)
        options.addWidget(self.format_combo, 0, 1)
        options.addWidget(QLabel("Calidad"), 0, 2)
        options.addWidget(self.quality_slider, 0, 3)
        options.addWidget(self.quality_label, 0, 4)
        options.addWidget(QLabel("Nombre"), 1, 0)
        options.addWidget(self.template_edit, 1, 1, 1, 4)
        options.addWidget(self.playlist_check, 2, 1)
        options.addWidget(self.open_when_done_check, 2, 2, 1, 3)
        return options

    def _build_ffmpeg_hint(self) -> QLabel:
        hint = QLabel("Nota: para convertir a mp3/wav/flac hace falta FFmpeg instalado y en PATH.")
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        return hint

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Cola"))
        layout.addWidget(self.queue_list, 1)
        layout.addWidget(QLabel("Actividad"))
        layout.addWidget(self.log_view, 2)
        return panel

    def _build_download_controls(self) -> QHBoxLayout:
        controls = QHBoxLayout()
        controls.addWidget(self.start_button)
        controls.addWidget(self.cancel_button)
        controls.addWidget(self.clear_button)
        controls.addStretch(1)
        controls.addWidget(self.progress, 2)
        return controls

    def _connect_signals(self) -> None:
        self.start_button.clicked.connect(self.download_requested.emit)
        self.cancel_button.clicked.connect(self.cancel_requested.emit)
        self.clear_button.clicked.connect(self.clear_requested.emit)
        self.browse_button.clicked.connect(self.output_dir_requested.emit)
        self.quality_slider.valueChanged.connect(
            lambda value: self.quality_label.setText(str(value))
        )

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

    def audio_quality(self) -> int:
        return self.quality_slider.value()

    def filename_template(self) -> str:
        return self.template_edit.text().strip()

    def include_playlist(self) -> bool:
        return self.playlist_check.isChecked()

    def open_output_dir_when_done(self) -> bool:
        return self.open_when_done_check.isChecked()

    def prepare_download(self, urls: list[str]) -> None:
        self.queue_list.clear()
        self.queue_list.addItems(urls)
        self.log_view.clear()
        self.progress.setValue(0)

    def clear_form(self) -> None:
        self.url_edit.clear()
        self.queue_list.clear()
        self.log_view.clear()

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

    def set_status(self, message: str) -> None:
        self.statusBar().showMessage(message)

    def set_cancel_enabled(self, enabled: bool) -> None:
        self.cancel_button.setEnabled(enabled)

    def set_running(self, running: bool) -> None:
        self.start_button.setEnabled(not running)
        self.cancel_button.setEnabled(running)
        self.clear_button.setEnabled(not running)
        self.browse_button.setEnabled(not running)
        self.url_edit.setReadOnly(running)
        self.output_edit.setReadOnly(running)
        self.template_edit.setReadOnly(running)
        self.format_combo.setEnabled(not running)
        self.quality_slider.setEnabled(not running)
        self.playlist_check.setEnabled(not running)
        self.open_when_done_check.setEnabled(not running)
        self.statusBar().showMessage("Descargando..." if running else "Preparado")

    def closeEvent(self, event) -> None:
        self.close_requested.emit(event)
