from __future__ import annotations

import json
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
    QAbstractItemView,
    QApplication,
    QAction,
    QDesktopServices,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSystemTrayIcon,
    QTabWidget,
    QThread,
    QTimer,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    Qt,
    Signal,
    Slot,
    QIcon,
    QSettings,
    QUrl,
)
from views.styles import APP_STYLESHEET, DARK_STYLESHEET, HIGH_CONTRAST_STYLESHEET
from models import DownloadRequest
from services.playlist_io import PlaylistRecord, read_playlist, write_playlist
from services.musicbrainz import search_recordings
from services.podcast_rss import PodcastEpisode, fetch_rss
from services.privacy import redact_text
from services.url_parser import parse_urls


class FeedWorker(QThread):
    loaded = Signal(str, object)
    failed = Signal(str)

    def __init__(self, feed_url: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.feed_url = feed_url

    def run(self) -> None:
        try:
            episodes = fetch_rss(self.feed_url)
        except Exception as exc:
            self.failed.emit(redact_text(str(exc)))
        else:
            self.loaded.emit(self.feed_url, episodes)


class MainWindow(QMainWindow):
    download_requested = Signal()
    cancel_requested = Signal()
    clear_requested = Signal()
    output_dir_requested = Signal()
    retry_requested = Signal()
    retry_selected_requested = Signal()
    resume_requested = Signal()
    close_requested = Signal(object)
    check_updates_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._settings = QSettings(APP_NAME, APP_NAME)
        self._queue_items: dict[str, QListWidgetItem] = {}
        self._active_key_prefix = ""
        self._run_number = 0
        self._import_number = 0
        self._podcast_pending: dict[str, dict[str, str]] = {}
        self._podcast_processed: dict[str, list[str]] = {}
        self._metadata_overrides: dict[str, dict[str, str]] = {}
        self._feed_worker: FeedWorker | None = None
        self._history_suspended = False
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(250)
        self._save_timer.timeout.connect(self._write_queue)
        self.setWindowTitle(WINDOW_TITLE)
        asset_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
        self.setWindowIcon(QIcon(str(asset_root / "assets" / "spidertomp3-icon.svg")))
        self.resize(1180, 780)
        self.setMinimumSize(860, 600)
        self.setAcceptDrops(True)

        self._create_widgets()
        self._build_layout()
        self._connect_signals()
        self._build_menu()
        self._restore_preferences()
        self._apply_style()

    def _create_widgets(self) -> None:
        self.url_edit = QTextEdit()
        self.url_edit.setAcceptDrops(False)
        self.url_edit.setPlaceholderText(
            "Pega uno o varios enlaces, uno por línea…\nPuedes incluir vídeos, listas y audios públicos compatibles."
        )
        self.url_edit.setFixedHeight(96)

        self.queue_list = QListWidget()
        self.queue_list.setAlternatingRowColors(False)
        self.queue_list.setAccessibleName("Cola de audios")

        self.output_edit = QLineEdit(str(DEFAULT_OUTPUT_DIR))
        self.browse_button = QPushButton("Examinar")

        self.format_combo = QComboBox()
        self.format_combo.addItems(AUDIO_FORMATS)

        self.quality_combo = QComboBox()
        self._update_quality_options()

        self.template_edit = QLineEdit(DEFAULT_FILENAME_TEMPLATE)
        self.preset_combo = QComboBox()
        for label, value in (
            ("Personalizado", ""),
            ("Título e ID", "%(title).120s [%(id)s].%(ext)s"),
            ("Solo título", "%(title).120s.%(ext)s"),
            ("Autor y título", "%(uploader).60s - %(title).120s.%(ext)s"),
            ("Lista y número", "%(playlist).60s/%(playlist_index)03d - %(title).120s.%(ext)s"),
        ):
            self.preset_combo.addItem(label, value)
        self.template_preview_label = QLabel()
        self.template_preview_label.setWordWrap(True)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(("Sistema", "Claro", "Oscuro", "Alto contraste"))
        self.playlist_check = QCheckBox("Permitir playlists")
        self.playlist_limit_spin = QSpinBox()
        self.playlist_limit_spin.setRange(1, 5000)
        self.playlist_limit_spin.setValue(200)
        self.attempts_spin = QSpinBox()
        self.attempts_spin.setRange(1, 5)
        self.attempts_spin.setValue(2)
        self.duplicate_combo = QComboBox()
        for label, value in (("Omitir", "skip"), ("Renombrar", "rename"), ("Preguntar", "ask")):
            self.duplicate_combo.addItem(label, value)
        self.archive_check = QCheckBox("Omitir ID ya descargados")
        self.metadata_check = QCheckBox("Añadir metadatos del origen")
        self.cover_check = QCheckBox("Incluir portada si está disponible")
        self.cover_check.setToolTip("Disponible para MP3, M4A, Opus y FLAC.")
        self.remember_check = QCheckBox("Guardar historial y sesión")
        self.remember_check.setChecked(True)
        self.open_when_done_check = QCheckBox("Abrir carpeta al terminar")
        self.open_when_done_check.setChecked(True)

        self.start_button = QPushButton("Descargar audio")
        self.start_button.setObjectName("PrimaryButton")
        self.retry_button = QPushButton("Reintentar fallidos")
        self.retry_button.setEnabled(False)
        self.retry_selected_button = QPushButton("Reintentar selección")
        self.retry_selected_button.setEnabled(False)
        self.resume_button = QPushButton("Reanudar")
        self.resume_button.setEnabled(False)
        self.paste_button = QPushButton("Pegar del portapapeles")
        self.import_list_button = QPushButton("Importar lista")
        self.import_rss_button = QPushButton("Podcast RSS")
        self.export_list_button = QPushButton("Exportar lista")
        self.remove_button = QPushButton("Quitar")
        self.move_up_button = QPushButton("↑")
        self.move_down_button = QPushButton("↓")
        self.move_up_button.setToolTip("Subir en la cola")
        self.move_down_button.setToolTip("Bajar en la cola")
        self.open_file_button = QPushButton("Abrir archivo")
        self.open_folder_button = QPushButton("Abrir carpeta")
        self.export_log_button = QPushButton("Exportar informe")
        self.clean_partials_button = QPushButton("Limpiar restos")
        self._last_total_progress = 0
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setObjectName("DangerButton")
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
        self.progress.setTextVisible(True)

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
        central.setObjectName("Central")
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(16)

        root.addLayout(self._build_header())
        root.addWidget(self._build_splitter(), 1)
        root.addWidget(self._build_download_controls())
        self.setCentralWidget(central)

    def _build_header(self) -> QHBoxLayout:
        icon = QLabel()
        icon.setObjectName("BrandIcon")
        icon.setPixmap(self.windowIcon().pixmap(42, 42))
        icon.setFixedSize(48, 48)
        title = QLabel("SpiderToMP3")
        title.setObjectName("Title")
        subtitle = QLabel("Tu audio, organizado y listo para escuchar.")
        subtitle.setObjectName("Subtitle")
        titles = QVBoxLayout()
        titles.setSpacing(2)
        titles.addWidget(title)
        titles.addWidget(subtitle)
        version = QLabel(f"VERSIÓN {APP_VERSION}")
        version.setObjectName("VersionBadge")
        header = QHBoxLayout()
        header.setSpacing(12)
        header.addWidget(icon)
        header.addLayout(titles)
        header.addStretch()
        header.addWidget(version)
        return header

    def _build_splitter(self) -> QSplitter:
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setChildrenCollapsible(False)
        splitter.setSizes([610, 510])
        return splitter

    def _build_left_panel(self) -> QWidget:
        content = QWidget()
        content.setObjectName("ScrollContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 10, 0)
        layout.setSpacing(12)

        source, source_layout = self._make_card("01  ·  ENLACES", "Añade lo que quieres convertir")
        url_label = QLabel("Direcciones de origen")
        url_label.setBuddy(self.url_edit)
        source_layout.addWidget(url_label)
        source_layout.addWidget(self.url_edit)
        source_layout.addWidget(self.url_error)
        source_actions = QHBoxLayout()
        source_actions.addWidget(self.paste_button)
        source_actions.addWidget(self.import_list_button)
        source_layout.addLayout(source_actions)
        source_layout.addWidget(self.import_rss_button)
        layout.addWidget(source)

        output, output_layout = self._make_card("02  ·  SALIDA", "Elige cómo guardar tus audios")
        output_label = QLabel("Carpeta de salida")
        output_label.setBuddy(self.output_edit)
        output_layout.addWidget(output_label)
        output_layout.addLayout(self._build_output_row())
        output_layout.addWidget(self.output_error)
        output_layout.addLayout(self._build_options_grid())
        output_layout.addWidget(self.format_error)
        output_layout.addWidget(self.template_error)
        layout.addWidget(output)

        advanced, advanced_layout = self._make_card("03  ·  PREFERENCIAS", "Controla listas, duplicados y sesión")
        advanced_layout.addLayout(self._build_advanced_grid())
        recent_label = QLabel("Enlaces recientes")
        recent_label.setObjectName("FieldLabel")
        advanced_layout.addWidget(recent_label)
        advanced_layout.addWidget(self.recent_combo)
        history_actions = QHBoxLayout()
        history_actions.addWidget(self.use_recent_button)
        history_actions.addWidget(self.clear_history_button)
        advanced_layout.addLayout(history_actions)
        advanced_layout.addWidget(self._build_ffmpeg_hint())
        layout.addWidget(advanced)
        layout.addStretch()

        panel = QScrollArea()
        panel.setObjectName("PanelScroll")
        panel.setWidgetResizable(True)
        panel.setFrameShape(QScrollArea.NoFrame)
        panel.setWidget(content)
        panel.setMinimumWidth(390)
        return panel

    def _make_card(self, eyebrow: str, heading: str) -> tuple[QWidget, QVBoxLayout]:
        card = QWidget()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(9)
        eyebrow_label = QLabel(eyebrow)
        eyebrow_label.setObjectName("Eyebrow")
        heading_label = QLabel(heading)
        heading_label.setObjectName("SectionTitle")
        layout.addWidget(eyebrow_label)
        layout.addWidget(heading_label)
        layout.addSpacing(3)
        return card, layout

    def _build_output_row(self) -> QHBoxLayout:
        output_row = QHBoxLayout()
        output_row.addWidget(self.output_edit, 1)
        output_row.addWidget(self.browse_button)
        return output_row

    def _build_options_grid(self) -> QGridLayout:
        options = QGridLayout()
        options.setHorizontalSpacing(12)
        options.setVerticalSpacing(9)
        format_label = QLabel("Formato")
        format_label.setBuddy(self.format_combo)
        options.addWidget(format_label, 0, 0)
        options.addWidget(self.format_combo, 0, 1)
        quality_label = QLabel("Calidad")
        quality_label.setBuddy(self.quality_combo)
        options.addWidget(quality_label, 1, 0)
        options.addWidget(self.quality_combo, 1, 1)
        name_label = QLabel("Nombre de archivo")
        name_label.setBuddy(self.template_edit)
        options.addWidget(name_label, 2, 0, 1, 2)
        options.addWidget(self.template_edit, 3, 0)
        options.addWidget(self.preset_combo, 3, 1)
        self.template_preview_label.setObjectName("Preview")
        options.addWidget(self.template_preview_label, 4, 0, 1, 2)
        return options

    def _build_advanced_grid(self) -> QGridLayout:
        options = QGridLayout()
        options.setHorizontalSpacing(12)
        options.setVerticalSpacing(10)
        options.addWidget(self.playlist_check, 0, 0, 1, 2)
        options.addWidget(self.open_when_done_check, 1, 0, 1, 2)
        limit_label = QLabel("Máx. lista")
        limit_label.setBuddy(self.playlist_limit_spin)
        options.addWidget(limit_label, 2, 0)
        options.addWidget(self.playlist_limit_spin, 2, 1)
        attempts_label = QLabel("Intentos")
        attempts_label.setBuddy(self.attempts_spin)
        options.addWidget(attempts_label, 3, 0)
        options.addWidget(self.attempts_spin, 3, 1)
        duplicate_label = QLabel("Duplicados")
        duplicate_label.setBuddy(self.duplicate_combo)
        options.addWidget(duplicate_label, 4, 0)
        options.addWidget(self.duplicate_combo, 4, 1)
        options.addWidget(self.archive_check, 5, 0, 1, 2)
        options.addWidget(self.metadata_check, 6, 0, 1, 2)
        options.addWidget(self.cover_check, 7, 0, 1, 2)
        options.addWidget(self.remember_check, 8, 0, 1, 2)
        theme_label = QLabel("Tema")
        theme_label.setBuddy(self.theme_combo)
        options.addWidget(theme_label, 9, 0)
        options.addWidget(self.theme_combo, 9, 1)
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
        layout.setContentsMargins(4, 0, 0, 0)
        tabs = QTabWidget()
        tabs.setObjectName("WorkspaceTabs")

        queue, queue_layout = self._make_card("COLA DE DESCARGA", "Tus audios")
        queue_layout.addWidget(self.queue_list, 1)
        queue_actions = QHBoxLayout()
        for button in (self.remove_button, self.move_up_button, self.move_down_button):
            queue_actions.addWidget(button)
        queue_actions.addStretch()
        queue_actions.addWidget(self.export_list_button)
        queue_layout.addLayout(queue_actions)
        open_actions = QHBoxLayout()
        open_actions.addWidget(self.open_file_button)
        open_actions.addWidget(self.open_folder_button)
        queue_layout.addLayout(open_actions)
        tabs.addTab(queue, "Cola")

        activity, activity_layout = self._make_card("REGISTRO", "Actividad")
        activity_header = QHBoxLayout()
        activity_header.addWidget(self.copy_log_button)
        activity_header.addWidget(self.export_log_button)
        activity_layout.addWidget(self.log_view, 1)
        activity_layout.addLayout(activity_header)
        activity_layout.addWidget(self.clean_partials_button)
        tabs.addTab(activity, "Actividad")
        layout.addWidget(tabs)
        panel.setMinimumWidth(330)
        return panel

    def _build_download_controls(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("ActionBar")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)
        top = QHBoxLayout()
        top.addWidget(self.current_label, 1)
        top.addWidget(self.progress, 1)
        layout.addLayout(top)
        controls = QHBoxLayout()
        controls.addWidget(self.start_button)
        controls.addWidget(self.cancel_button)
        controls.addWidget(self.resume_button)
        controls.addWidget(self.retry_button)
        controls.addWidget(self.retry_selected_button)
        controls.addStretch(1)
        controls.addWidget(self.clear_button)
        layout.addLayout(controls)
        return panel

    def _connect_signals(self) -> None:
        self.start_button.clicked.connect(self.download_requested.emit)
        self.retry_button.clicked.connect(self.retry_requested.emit)
        self.retry_selected_button.clicked.connect(self.retry_selected_requested.emit)
        self.resume_button.clicked.connect(self.resume_requested.emit)
        self.cancel_button.clicked.connect(self.cancel_requested.emit)
        self.clear_button.clicked.connect(self.clear_requested.emit)
        self.browse_button.clicked.connect(self.output_dir_requested.emit)
        self.format_combo.currentTextChanged.connect(self._update_quality_options)
        self.format_combo.currentTextChanged.connect(self._update_template_preview)
        self.format_combo.currentTextChanged.connect(self._update_cover_availability)
        self.template_edit.textChanged.connect(self._update_template_preview)
        self.preset_combo.currentIndexChanged.connect(self._use_preset)
        self.theme_combo.currentTextChanged.connect(self._apply_style)
        self.use_recent_button.clicked.connect(self._use_recent)
        self.clear_history_button.clicked.connect(self.clear_history)
        self.copy_log_button.clicked.connect(self.copy_log)
        self.export_log_button.clicked.connect(self.export_report)
        self.clean_partials_button.clicked.connect(self.clean_partials)
        self.paste_button.clicked.connect(self.paste_links)
        self.import_list_button.clicked.connect(self.import_list)
        self.import_rss_button.clicked.connect(self.import_rss)
        self.export_list_button.clicked.connect(self.export_list)
        self.remove_button.clicked.connect(self.remove_selected)
        self.move_up_button.clicked.connect(lambda: self.move_selected(-1))
        self.move_down_button.clicked.connect(lambda: self.move_selected(1))
        self.open_file_button.clicked.connect(self.open_selected_file)
        self.open_folder_button.clicked.connect(self.open_selected_folder)
        self.remember_check.toggled.connect(self._remember_changed)
        self.queue_list.currentItemChanged.connect(lambda *_: self._refresh_queue_buttons())
        QApplication.styleHints().colorSchemeChanged.connect(self._system_theme_changed)
        for shortcut, callback in (
            ("Ctrl+Shift+V", self.paste_links),
            ("Delete", self.remove_selected),
            ("Ctrl+R", self.retry_selected_requested.emit),
        ):
            action = QAction(self)
            action.setShortcut(shortcut)
            action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
            action.triggered.connect(callback)
            self.addAction(action)

    def _build_menu(self) -> None:
        check_updates = QAction("Buscar actualizaciones", self)
        check_updates.triggered.connect(self.check_updates_requested.emit)
        about = QAction("Acerca de SpiderToMP3", self)
        about.triggered.connect(self._show_about)
        help_menu = self.menuBar().addMenu("Ayuda")
        help_menu.addAction(check_updates)
        help_menu.addAction(about)

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            f"Acerca de {APP_NAME}",
            f"{APP_NAME} {APP_VERSION}\nDescarga y convierte audio con yt-dlp y FFmpeg.",
        )

    def copy_log(self) -> None:
        QApplication.clipboard().setText(self.log_view.toPlainText())
        self.statusBar().showMessage("Registro copiado al portapapeles.", 4000)

    def export_report(self) -> None:
        destination, _ = QFileDialog.getSaveFileName(
            self, "Guardar informe", "spidertomp3-informe.txt", "Texto (*.txt)"
        )
        if destination:
            lines = [self.queue_list.item(i).text() for i in range(self.queue_list.count())]
            try:
                Path(destination).write_text(
                    redact_text("\n".join(lines) + "\n\n" + self.log_view.toPlainText()), encoding="utf-8"
                )
            except OSError as exc:
                QMessageBox.warning(self, "Informe", redact_text(str(exc)))
            else:
                self.set_status("Informe guardado.")

    def paste_links(self) -> None:
        current = parse_urls(self.urls_text())
        added = [url for url in parse_urls(QApplication.clipboard().text()) if url not in current]
        if added:
            self.url_edit.setPlainText("\n".join(current + added))

    def import_list(self) -> None:
        source, _ = QFileDialog.getOpenFileName(self, "Importar lista", "", "Listas de audio (*.csv *.m3u *.m3u8)")
        if not source:
            return
        try:
            records = read_playlist(Path(source))
        except (OSError, UnicodeError, ValueError) as exc:
            QMessageBox.warning(self, "Importar lista", redact_text(str(exc)))
            return
        urls = parse_urls(self.urls_text())
        seen = set(urls)
        for record in records:
            if record.url and record.url not in seen:
                urls.append(record.url)
                seen.add(record.url)
            self._import_number += 1
            target = {"url": record.url, "playlist_path": []}
            if record.path:
                target["path"] = record.path
            self.update_item(f"import-{self._import_number}", record.title, record.status, target)
        self.url_edit.setPlainText("\n".join(urls))
        self.set_status(f"Importados {len(records)} elementos.")

    def import_rss(self) -> None:
        feed_url, accepted = QInputDialog.getText(self, "Podcast RSS", "Dirección del feed RSS público:")
        if not accepted or not feed_url.strip() or self._feed_worker is not None:
            return
        self.import_rss_button.setEnabled(False)
        self.set_status("Buscando episodios del podcast...")
        self._feed_worker = FeedWorker(feed_url.strip(), self)
        self._feed_worker.loaded.connect(self._rss_loaded)
        self._feed_worker.failed.connect(self._rss_failed)
        self._feed_worker.finished.connect(self._rss_finished)
        self._feed_worker.start()

    @Slot(str, object)
    def _rss_loaded(self, feed_url: str, episodes: list[PodcastEpisode]) -> None:
        if not self.start_button.isEnabled():
            self.set_status("El podcast se puede importar al terminar la descarga actual.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Episodios del podcast")
        dialog.resize(680, 480)
        layout = QVBoxLayout(dialog)
        caption = QLabel("Elige los episodios nuevos. Solo se usarán los archivos de audio publicados en el RSS.")
        caption.setWordWrap(True)
        layout.addWidget(caption)
        choices = QListWidget(dialog)
        processed = set(self._podcast_processed.get(feed_url, []))
        for episode in episodes:
            item = QListWidgetItem(f"{episode.title}  ·  {episode.published or 'Sin fecha'}")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked if episode.guid in processed else Qt.Checked)
            if episode.guid in processed:
                item.setToolTip("Ya procesado; puedes volver a seleccionarlo.")
            choices.addItem(item)
        layout.addWidget(choices)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.Accepted:
            self.set_status("Importación de podcast cancelada.")
            return
        urls = parse_urls(self.urls_text())
        seen = set(urls)
        chosen = 0
        for index, episode in enumerate(episodes):
            if choices.item(index).checkState() != Qt.Checked:
                continue
            chosen += 1
            if episode.url not in seen:
                urls.append(episode.url)
                seen.add(episode.url)
            self._import_number += 1
            self._podcast_pending[episode.url] = {"feed": feed_url, "guid": episode.guid}
            self.update_item(
                f"rss-{self._import_number}",
                episode.title,
                "pendiente",
                {
                    "url": episode.url,
                    "source": "Podcast RSS",
                    "playlist_path": [],
                },
            )
        self.url_edit.setPlainText("\n".join(urls))
        self._save_podcast_state()
        self.set_status(f"Añadidos {chosen} episodios del podcast.")

    @Slot(str)
    def _rss_failed(self, message: str) -> None:
        QMessageBox.warning(self, "Podcast RSS", message)
        self.set_status("No se pudo leer el podcast.")

    @Slot()
    def _rss_finished(self) -> None:
        self._feed_worker = None
        self.import_rss_button.setEnabled(self.start_button.isEnabled())

    def export_list(self) -> None:
        records = []
        for index in range(self.queue_list.count()):
            item = self.queue_list.item(index)
            target = item.data(Qt.UserRole)
            if isinstance(target, dict):
                records.append(
                    PlaylistRecord(
                        str(item.data(Qt.UserRole + 2) or ""),
                        str(target.get("url") or ""),
                        str(item.data(Qt.UserRole + 1) or "pendiente"),
                        str(target.get("path") or ""),
                    )
                )
        if not records:
            records = [PlaylistRecord(url, url) for url in parse_urls(self.urls_text())]
        if not records:
            self.set_status("No hay enlaces ni elementos de cola para exportar.")
            return
        destination, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Exportar lista",
            "spidertomp3-lista.csv",
            "CSV (*.csv);;Lista M3U (*.m3u *.m3u8)",
        )
        if not destination:
            return
        path = Path(destination)
        if not path.suffix:
            path = path.with_suffix(".m3u" if "M3U" in selected_filter else ".csv")
        try:
            write_playlist(path, records)
        except (OSError, UnicodeError, ValueError) as exc:
            QMessageBox.warning(self, "Exportar lista", redact_text(str(exc)))
        else:
            self.set_status(f"Lista exportada: {len(records)} elementos.")

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        parts = []
        for url in event.mimeData().urls():
            if url.isLocalFile() and url.toLocalFile().lower().endswith(".txt"):
                path = Path(url.toLocalFile())
                try:
                    if path.stat().st_size <= 1024 * 1024:
                        parts.append(path.read_text(encoding="utf-8-sig"))
                except (OSError, UnicodeError):
                    self.set_status("No se pudo leer el archivo de enlaces.")
            elif url.scheme() in {"http", "https"}:
                parts.append(url.toString())
        if not parts and not event.mimeData().hasUrls() and event.mimeData().hasText():
            parts.append(event.mimeData().text())
        existing = parse_urls(self.urls_text())
        self.url_edit.setPlainText("\n".join(dict.fromkeys(existing + parse_urls("\n".join(parts)))))
        event.acceptProposedAction()

    def remove_selected(self) -> None:
        item = self.queue_list.currentItem()
        if item is None or self.start_button.isEnabled() is False:
            return
        for key, value in list(self._queue_items.items()):
            if value is item:
                del self._queue_items[key]
                break
        self.queue_list.takeItem(self.queue_list.row(item))
        self._save_queue()
        self._refresh_queue_buttons()

    def move_selected(self, offset: int) -> None:
        row = self.queue_list.currentRow()
        new_row = row + offset
        if row < 0 or not self.start_button.isEnabled() or not 0 <= new_row < self.queue_list.count():
            return
        item = self.queue_list.takeItem(row)
        self.queue_list.insertItem(new_row, item)
        self.queue_list.setCurrentRow(new_row)
        self._save_queue()

    def selected_request(self) -> DownloadRequest | None:
        item = self.queue_list.currentItem()
        if item is None or item.data(Qt.UserRole + 1) not in {"fallido", "cancelado"}:
            return None
        target = item.data(Qt.UserRole)
        return DownloadRequest(target["url"], tuple(target.get("playlist_path", ())), target.get("expected_id"))

    def pending_requests(self) -> list[DownloadRequest]:
        requests = []
        for index in range(self.queue_list.count()):
            item = self.queue_list.item(index)
            if item.data(Qt.UserRole + 1) not in {"pendiente", "cancelado", "descargando", "convirtiendo"}:
                continue
            target = item.data(Qt.UserRole)
            requests.append(
                DownloadRequest(target["url"], tuple(target.get("playlist_path", ())), target.get("expected_id"))
            )
        return list(dict.fromkeys(requests))

    def _refresh_queue_buttons(self) -> None:
        idle = self.start_button.isEnabled()
        self.retry_selected_button.setEnabled(idle and self.selected_request() is not None)
        self.resume_button.setEnabled(idle and bool(self.pending_requests()))

    def open_selected_file(self) -> None:
        item = self.queue_list.currentItem()
        target = item.data(Qt.UserRole) if item else None
        if isinstance(target, dict) and target.get("path") and Path(target["path"]).is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(target["path"]))

    def open_selected_folder(self) -> None:
        item = self.queue_list.currentItem()
        target = item.data(Qt.UserRole) if item else None
        path = (
            Path(target["path"]).parent
            if isinstance(target, dict) and target.get("path")
            else Path(self.output_dir_text())
        )
        if path.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def notify_summary(self, message: str) -> None:
        if QSystemTrayIcon.isSystemTrayAvailable() and QSystemTrayIcon.supportsMessages():
            if not hasattr(self, "_tray_icon"):
                self._tray_icon = QSystemTrayIcon(self.windowIcon(), self)
            self._tray_icon.show()
            self._tray_icon.showMessage(APP_NAME, redact_text(message), QSystemTrayIcon.Information, 8000)

    def clean_partials(self) -> None:
        root = Path(self.output_dir_text()).expanduser().resolve()
        candidates: set[Path] = set()
        for item in self._queue_items.values():
            if item.data(Qt.UserRole + 1) not in {"fallido", "cancelado"}:
                continue
            target = item.data(Qt.UserRole)
            for raw in target.get("partial_paths", []):
                path = Path(raw).resolve()
                candidate_output = (
                    Path(target["candidate_output"]).resolve() if target.get("candidate_output") else None
                )
                is_partial = path == candidate_output or path.name.endswith(
                    (".part", ".ytdl", ".temp.mp3", ".temp.m4a", ".temp.opus", ".temp.wav", ".temp.flac")
                )
                if path.is_relative_to(root) and is_partial and path.is_file():
                    candidates.add(path)
        if not candidates:
            self.set_status("No hay restos identificados de esta sesión.")
            return
        answer = QMessageBox.question(
            self,
            "Limpiar restos",
            f"¿Borrar {len(candidates)} archivos parciales creados en esta sesión?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            removed = 0
            for path in candidates:
                try:
                    path.unlink(missing_ok=True)
                    removed += 1
                except OSError as exc:
                    self.append_log(f"No se pudo borrar un archivo parcial: {exc}")
            self.set_status(f"Se borraron {removed} archivos parciales.")

    def _apply_style(self) -> None:
        theme = self.theme_combo.currentText()
        if theme == "Sistema":
            theme = "Oscuro" if QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark else "Claro"
        stylesheet = {"Claro": APP_STYLESHEET, "Oscuro": DARK_STYLESHEET, "Alto contraste": HIGH_CONTRAST_STYLESHEET}[
            theme
        ]
        QApplication.instance().setStyleSheet(stylesheet)

    def _system_theme_changed(self, *_args) -> None:
        if self.theme_combo.currentText() == "Sistema":
            self._apply_style()

    def _use_preset(self) -> None:
        template = self.preset_combo.currentData()
        if template:
            self.template_edit.setText(template)

    def _update_template_preview(self) -> None:
        from yt_dlp import YoutubeDL

        try:
            with YoutubeDL({"quiet": True, "outtmpl": self.filename_template()}) as ydl:
                filename = ydl.prepare_filename(
                    {
                        "title": "Canción de prueba",
                        "id": "abc123",
                        "uploader": "Artista",
                        "playlist": "Lista",
                        "playlist_index": 1,
                        "ext": self.audio_format(),
                    }
                )
            self.template_preview_label.setText(f"Ejemplo: {filename}")
        except Exception:
            self.template_preview_label.setText("Ejemplo: patrón inválido")

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

    def playlist_limit(self) -> int:
        return self.playlist_limit_spin.value()

    def network_attempts(self) -> int:
        return self.attempts_spin.value()

    def duplicate_policy(self) -> str:
        return self.duplicate_combo.currentData()

    def archive_enabled(self) -> bool:
        return self.archive_check.isChecked()

    def embed_metadata(self) -> bool:
        return self.metadata_check.isChecked()

    def embed_cover(self) -> bool:
        return self.cover_check.isChecked() and self.audio_format() != "wav"

    def metadata_overrides(self) -> dict[str, dict[str, str]]:
        return dict(self._metadata_overrides)

    def prepare_download(
        self, urls: list[str], preserve: bool = False, retry_requests: list[DownloadRequest] | None = None
    ) -> None:
        self._history_suspended = False
        if retry_requests is None and not preserve:
            self._metadata_overrides.clear()
        self._run_number += 1
        self._active_key_prefix = f"{self._run_number}:"
        if preserve:
            for key, item in list(self._queue_items.items()):
                target = item.data(Qt.UserRole)
                request = DownloadRequest(
                    target["url"], tuple(target.get("playlist_path", ())), target.get("expected_id")
                )
                if item.data(Qt.UserRole + 1) in {"fallido", "cancelado", "pendiente"} and request in (
                    retry_requests or []
                ):
                    self.queue_list.takeItem(self.queue_list.row(item))
                    del self._queue_items[key]
        else:
            self.queue_list.clear()
            self._queue_items.clear()
        self.log_view.clear()
        self.progress.setValue(0)
        self._last_total_progress = 0
        self.current_label.setText("Analizando enlaces...")
        self.retry_button.setEnabled(False)
        self._save_queue()

    def choose_preview_items(self) -> list[DownloadRequest]:
        candidates = [
            self.queue_list.item(index)
            for index in range(self.queue_list.count())
            if self.queue_list.item(index).data(Qt.UserRole + 1) == "pendiente"
        ]
        if not candidates:
            return []
        dialog = QDialog(self)
        dialog.setWindowTitle("Vista previa de la descarga")
        dialog.resize(680, 450)
        layout = QVBoxLayout(dialog)
        limited = any((item.data(Qt.UserRole) or {}).get("truncated") for item in candidates)
        message = f"Se encontraron {len(candidates)} audios. Desmarca los que no quieras descargar."
        if limited:
            message += " La lista supera el límite configurado: solo se descargarán los primeros."
        layout.addWidget(QLabel(message))
        choices = QListWidget(dialog)
        choices.setDragDropMode(QAbstractItemView.InternalMove)
        for original in candidates:
            target = original.data(Qt.UserRole)
            duration = target.get("duration") if isinstance(target, dict) else None
            duration_text = (
                f" · {int(duration) // 60}:{int(duration) % 60:02d}" if isinstance(duration, (int, float)) else ""
            )
            source = target.get("source", "Enlace") if isinstance(target, dict) else "Enlace"
            item = QListWidgetItem(
                f"{redact_text(str(original.data(Qt.UserRole + 2)))} · {redact_text(str(source))}{duration_text}"
            )
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            item.setData(Qt.UserRole, target)
            item.setData(Qt.UserRole + 1, original.data(Qt.UserRole + 2))
            choices.addItem(item)
        choices.setCurrentRow(0)
        layout.addWidget(choices)
        order_actions = QHBoxLayout()
        up = QPushButton("Subir")
        down = QPushButton("Bajar")

        def move_choice(offset: int) -> None:
            row = choices.currentRow()
            if row < 0 or not 0 <= row + offset < choices.count():
                return
            moved = choices.takeItem(row)
            choices.insertItem(row + offset, moved)
            choices.setCurrentRow(row + offset)

        up.clicked.connect(lambda: move_choice(-1))
        down.clicked.connect(lambda: move_choice(1))
        order_actions.addWidget(up)
        order_actions.addWidget(down)
        order_actions.addStretch()
        musicbrainz_button = QPushButton("Buscar en MusicBrainz")
        musicbrainz_button.clicked.connect(lambda: self._choose_musicbrainz_for_item(choices))
        order_actions.addWidget(musicbrainz_button)
        layout.addLayout(order_actions)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.Accepted:
            return []
        requests = []
        selected_metadata_keys = set()
        conflicts = 0
        for index in range(choices.count()):
            item = choices.item(index)
            if item.checkState() == Qt.Checked:
                target = item.data(Qt.UserRole)
                selected_metadata_keys.add(f"{target.get('url') or ''}|{target.get('id') or ''}")
                requests.append(
                    DownloadRequest(target["url"], tuple(target.get("playlist_path", ())), target.get("expected_id"))
                )
                if self.duplicate_policy() == "ask":
                    from yt_dlp import YoutubeDL

                    try:
                        with YoutubeDL(
                            {"quiet": True, "outtmpl": str(Path(self.output_dir_text()) / self.filename_template())}
                        ) as ydl:
                            candidate = Path(
                                ydl.prepare_filename(
                                    {
                                        "title": item.data(Qt.UserRole + 1),
                                        "id": target.get("id"),
                                        "ext": self.audio_format(),
                                    }
                                )
                            )
                        conflicts += candidate.is_file()
                    except Exception:
                        pass
        if conflicts:
            choice = QMessageBox.question(
                self,
                "Archivos existentes",
                f"Hay {conflicts} archivos con el nombre previsto. ¿Renombrar los nuevos?\n"
                "Sí: renombrar; No: omitir; Cancelar: volver a la cola.",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Cancel,
            )
            if choice == QMessageBox.Cancel:
                return []
            self.duplicate_combo.setCurrentIndex(
                self.duplicate_combo.findData("rename" if choice == QMessageBox.Yes else "skip")
            )
        self._metadata_overrides = {
            key: tags for key, tags in self._metadata_overrides.items() if key in selected_metadata_keys
        }
        return requests

    def _choose_musicbrainz_for_item(self, choices: QListWidget) -> None:
        item = choices.currentItem()
        if item is None:
            self.set_status("Selecciona un audio para buscar metadatos.")
            return
        target = item.data(Qt.UserRole)
        if not isinstance(target, dict):
            return
        title = str(item.data(Qt.UserRole + 1) or "")
        preview_dialog = choices.window()
        artist, accepted = QInputDialog.getText(
            preview_dialog,
            "MusicBrainz",
            "Artista (opcional para afinar la búsqueda):",
            text=str(target.get("artist") or ""),
        )
        if not accepted:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()
        error = None
        try:
            matches = search_recordings(title, artist)
        except (OSError, UnicodeError, ValueError) as exc:
            error = exc
        finally:
            QApplication.restoreOverrideCursor()
        if error is not None:
            QMessageBox.warning(preview_dialog, "MusicBrainz", redact_text(str(error)))
            return
        if not matches:
            self.set_status("MusicBrainz no encontró coincidencias.")
            return
        labels = ["Conservar metadatos del origen"] + [
            f"{match.title} — {match.artist or 'Sin artista'} · {match.album or 'Sin álbum'} ({match.score})"
            for match in matches
        ]
        selected, accepted = QInputDialog.getItem(
            preview_dialog, "MusicBrainz", "Elige la grabación antes de escribir etiquetas:", labels, 0, False
        )
        if not accepted:
            return
        identity = f"{target.get('url') or ''}|{target.get('id') or ''}"
        if selected == labels[0]:
            self._metadata_overrides.pop(identity, None)
            item.setToolTip("")
            return
        chosen = matches[labels.index(selected) - 1]
        self._metadata_overrides[identity] = {
            "title": chosen.title,
            "artist": chosen.artist,
            "album": chosen.album,
        }
        self.metadata_check.setChecked(True)
        item.setToolTip(f"MusicBrainz: {chosen.title} — {chosen.artist} · {chosen.album}")
        self.set_status("Metadatos de MusicBrainz elegidos para este audio.")

    def clear_form(self) -> None:
        self.url_edit.clear()
        self.queue_list.clear()
        self._queue_items.clear()
        self.log_view.clear()
        self.retry_button.setEnabled(False)
        self._save_queue()

    @Slot(str)
    def append_log(self, text: str) -> None:
        self.log_view.appendPlainText(redact_text(text))
        bar = self.log_view.verticalScrollBar()
        bar.setValue(bar.maximum())

    @Slot(int)
    def set_progress(self, value: int) -> None:
        self._last_total_progress = value
        if self.progress.maximum() != 0:
            self.progress.setValue(value)

    @Slot(str)
    def set_current_title(self, title: str) -> None:
        self.current_label.setText(f"Ahora: {redact_text(title)}")

    @Slot(str)
    def set_current_message(self, message: str) -> None:
        self.current_label.setText(redact_text(message))

    @Slot(str)
    def mark_item_done(self, title: str) -> None:
        self.statusBar().showMessage(f"Convertido: {title}", 4500)

    @Slot(str, str, str, object)
    def update_item(self, key: str, title: str, state: str, target: object) -> None:
        if key not in self._queue_items:
            key = self._active_key_prefix + key
        labels = {
            "pendiente": "Pendiente",
            "descargando": "Descargando",
            "convirtiendo": "Convirtiendo",
            "completado": "Completado",
            "fallido": "Fallido",
            "cancelado": "Cancelado",
            "omitido": "Omitido",
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
        previous = item.data(Qt.UserRole)
        previous_state = item.data(Qt.UserRole + 1)
        if isinstance(previous, dict):
            for key in ("partial_paths", "candidate_output"):
                if key in previous and key not in target:
                    target = {**target, key: previous[key]}
        error = redact_text(str(target.get("error", "")))
        shown = f"{labels.get(state, state)} · {redact_text(title)}"
        progress = target.get("progress")
        if state == "descargando" and isinstance(progress, dict):
            if progress.get("percent") is not None:
                shown += f" · {progress['percent']} %"
            if progress.get("speed"):
                shown += f" · {progress['speed'] / 1024 / 1024:.1f} MiB/s"
            if progress.get("eta") is not None:
                shown += f" · {int(progress['eta'])} s"
        if error:
            shown += f" — {error}"
        item.setText(shown)
        item.setToolTip(redact_text(str(target.get("path") or target.get("help") or error)))
        item.setData(Qt.AccessibleDescriptionRole, shown)
        item.setData(Qt.UserRole, target)
        item.setData(Qt.UserRole + 1, state)
        item.setData(Qt.UserRole + 2, title)
        if state == "completado":
            self._mark_podcast_processed(str(target.get("url") or ""))
        if state == "fallido":
            self.retry_button.setEnabled(True)
        if state == "convirtiendo":
            self.progress.setRange(0, 0)
            self.progress.setFormat("Convirtiendo…")
        elif state in {"descargando", "completado", "fallido", "omitido"}:
            if self.progress.maximum() == 0:
                self.progress.setRange(0, 100)
                self.progress.setValue(self._last_total_progress)
            self.progress.setFormat("%p %")
        if state != "descargando" or previous_state != "descargando":
            self._save_queue()
        self._refresh_queue_buttons()

    def failed_requests(self) -> list[DownloadRequest]:
        requests: list[DownloadRequest] = []
        for index in range(self.queue_list.count()):
            item = self.queue_list.item(index)
            if item.data(Qt.UserRole + 1) != "fallido":
                continue
            target = item.data(Qt.UserRole)
            requests.append(
                DownloadRequest(target["url"], tuple(target.get("playlist_path", ())), target.get("expected_id"))
            )
        return list(dict.fromkeys(requests))

    def failed_urls(self) -> list[str]:
        return list(dict.fromkeys(request.url for request in self.failed_requests()))

    def mark_active_cancelled(self) -> None:
        for key, item in self._queue_items.items():
            state = item.data(Qt.UserRole + 1)
            if state in {"pendiente", "descargando", "convirtiendo"}:
                self.update_item(key, item.data(Qt.UserRole + 2), "cancelado", item.data(Qt.UserRole))

    def set_validation_errors(self, errors: dict[str, str]) -> None:
        self.url_error.setText(redact_text(errors.get("urls", "")))
        self.output_error.setText(redact_text(errors.get("output", "")))
        self.format_error.setText(redact_text(errors.get("format", "")))
        self.template_error.setText(redact_text(errors.get("template", "")))
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
            self.statusBar().showMessage(redact_text(next(iter(errors.values()))))

    def _update_quality_options(self, *_args) -> None:
        selected = self.quality_combo.currentData() if hasattr(self, "quality_combo") else None
        self.quality_combo.clear()
        for label, value in QUALITY_OPTIONS[self.audio_format()]:
            self.quality_combo.addItem(label, value)
        for index in range(self.quality_combo.count()):
            if self.quality_combo.itemData(index) == selected:
                self.quality_combo.setCurrentIndex(index)
                break

    def _update_cover_availability(self, *_args) -> None:
        self.cover_check.setEnabled(self.audio_format() != "wav" and self.start_button.isEnabled())

    def _restore_preferences(self) -> None:
        self.output_edit.setText(str(self._settings.value("output_dir", str(DEFAULT_OUTPUT_DIR))))
        self.template_edit.setText(str(self._settings.value("template", DEFAULT_FILENAME_TEMPLATE)))
        self._update_template_preview()
        index = self.format_combo.findText(str(self._settings.value("format", AUDIO_FORMATS[0])))
        if index >= 0:
            self.format_combo.setCurrentIndex(index)
        quality = self._settings.value("quality", None)
        for index in range(self.quality_combo.count()):
            if str(self.quality_combo.itemData(index)) == str(quality):
                self.quality_combo.setCurrentIndex(index)
                break
        self.playlist_check.setChecked(self._settings.value("playlist", False, type=bool))
        self.playlist_limit_spin.setValue(self._settings.value("playlist_limit", 200, type=int))
        self.attempts_spin.setValue(self._settings.value("network_attempts", 2, type=int))
        duplicate_index = self.duplicate_combo.findData(self._settings.value("duplicate_policy", "skip"))
        if duplicate_index >= 0:
            self.duplicate_combo.setCurrentIndex(duplicate_index)
        self.archive_check.setChecked(self._settings.value("archive_enabled", False, type=bool))
        self.metadata_check.setChecked(self._settings.value("embed_metadata", False, type=bool))
        self.cover_check.setChecked(self._settings.value("embed_cover", False, type=bool))
        self._update_cover_availability()
        self.remember_check.setChecked(self._settings.value("remember_recent", True, type=bool))
        self.theme_combo.setCurrentText(str(self._settings.value("theme", "Sistema")))
        self.open_when_done_check.setChecked(self._settings.value("open_when_done", True, type=bool))
        self.recent_combo.addItems(self._settings.value("recent_urls", [], type=list))
        self._restore_podcast_state()
        self._restore_queue()

    def save_preferences(self, urls: list[str]) -> None:
        self._settings.setValue("output_dir", self.output_dir_text())
        self._settings.setValue("template", self.filename_template())
        self._settings.setValue("format", self.audio_format())
        self._settings.setValue("quality", self.audio_quality())
        self._settings.setValue("playlist", self.include_playlist())
        self._settings.setValue("playlist_limit", self.playlist_limit())
        self._settings.setValue("network_attempts", self.network_attempts())
        self._settings.setValue("duplicate_policy", self.duplicate_policy())
        self._settings.setValue("archive_enabled", self.archive_enabled())
        self._settings.setValue("embed_metadata", self.embed_metadata())
        self._settings.setValue("embed_cover", self.cover_check.isChecked())
        self._settings.setValue("remember_recent", self.remember_check.isChecked())
        self._settings.setValue("theme", self.theme_combo.currentText())
        self._settings.setValue("open_when_done", self.open_output_dir_when_done())
        if not self.remember_check.isChecked():
            self.clear_history()
            return
        recent = list(dict.fromkeys(urls + [self.recent_combo.itemText(i) for i in range(self.recent_combo.count())]))[
            :20
        ]
        self._settings.setValue("recent_urls", recent)
        self.recent_combo.clear()
        self.recent_combo.addItems(recent)
        self._save_podcast_state()

    def clear_history(self) -> None:
        self._history_suspended = True
        self._save_timer.stop()
        self._settings.remove("recent_urls")
        self._settings.remove("queue_session")
        self._settings.remove("podcast_processed")
        self._settings.remove("podcast_pending")
        self._podcast_processed.clear()
        self._podcast_pending.clear()
        self.recent_combo.clear()

    def _remember_changed(self, enabled: bool) -> None:
        if not enabled:
            self.clear_history()
        else:
            self._history_suspended = False
            self._save_queue()
            self._save_podcast_state()

    def _restore_podcast_state(self) -> None:
        if not self.remember_check.isChecked():
            return
        try:
            processed = json.loads(self._settings.value("podcast_processed", "{}"))
            pending = json.loads(self._settings.value("podcast_pending", "{}"))
            if isinstance(processed, dict):
                self._podcast_processed = {
                    str(feed): [str(guid) for guid in guids][-500:]
                    for feed, guids in processed.items()
                    if isinstance(guids, list)
                }
            if isinstance(pending, dict):
                self._podcast_pending = {
                    str(url): {"feed": str(item["feed"]), "guid": str(item["guid"])}
                    for url, item in pending.items()
                    if isinstance(item, dict) and "feed" in item and "guid" in item
                }
        except (ValueError, TypeError):
            self._settings.remove("podcast_processed")
            self._settings.remove("podcast_pending")

    def _save_podcast_state(self) -> None:
        if not self.remember_check.isChecked() or self._history_suspended:
            return
        self._settings.setValue("podcast_processed", json.dumps(self._podcast_processed, ensure_ascii=False))
        self._settings.setValue("podcast_pending", json.dumps(self._podcast_pending, ensure_ascii=False))

    def _mark_podcast_processed(self, url: str) -> None:
        episode = self._podcast_pending.pop(url, None)
        if episode is None:
            return
        processed = self._podcast_processed.setdefault(episode["feed"], [])
        if episode["guid"] not in processed:
            processed.append(episode["guid"])
            del processed[:-500]
        self._save_podcast_state()

    def _save_queue(self) -> None:
        if not self.remember_check.isChecked() or self._history_suspended:
            return
        self._save_timer.start()

    def _write_queue(self) -> None:
        if not self.remember_check.isChecked() or self._history_suspended:
            return
        entries = []
        for index in range(self.queue_list.count()):
            item = self.queue_list.item(index)
            target = item.data(Qt.UserRole)
            if isinstance(target, dict):
                entries.append(
                    {
                        "title": item.data(Qt.UserRole + 2),
                        "state": item.data(Qt.UserRole + 1),
                        "target": {key: value for key, value in target.items() if key != "progress"},
                    }
                )
        self._settings.setValue("queue_session", json.dumps(entries, ensure_ascii=False))

    def _restore_queue(self) -> None:
        if not self.remember_check.isChecked():
            return
        try:
            entries = json.loads(self._settings.value("queue_session", "[]"))
            if not isinstance(entries, list):
                return
            for index, entry in enumerate(entries):
                state = entry["state"]
                if state in {"descargando", "convirtiendo"}:
                    state = "pendiente"
                self.update_item(str(index), entry["title"], state, entry["target"])
        except (ValueError, KeyError, TypeError):
            self._settings.remove("queue_session")

    def _use_recent(self) -> None:
        url = self.recent_combo.currentText()
        if url and url not in self.urls_text().splitlines():
            self.url_edit.append(url)

    def set_status(self, message: str) -> None:
        self.statusBar().showMessage(redact_text(message))

    def set_cancel_enabled(self, enabled: bool) -> None:
        self.cancel_button.setEnabled(enabled)

    def set_running(self, running: bool) -> None:
        self.start_button.setEnabled(not running)
        self.retry_button.setEnabled(not running and bool(self.failed_urls()))
        self._refresh_queue_buttons()
        self.cancel_button.setEnabled(running)
        self.clear_button.setEnabled(not running)
        self.browse_button.setEnabled(not running)
        self.url_edit.setReadOnly(running)
        self.output_edit.setReadOnly(running)
        self.template_edit.setReadOnly(running)
        self.format_combo.setEnabled(not running)
        self.quality_combo.setEnabled(not running)
        self.playlist_check.setEnabled(not running)
        self.playlist_limit_spin.setEnabled(not running)
        self.attempts_spin.setEnabled(not running)
        self.duplicate_combo.setEnabled(not running)
        self.archive_check.setEnabled(not running)
        self.metadata_check.setEnabled(not running)
        self.cover_check.setEnabled(not running and self.audio_format() != "wav")
        self.remember_check.setEnabled(not running)
        self.preset_combo.setEnabled(not running)
        self.theme_combo.setEnabled(not running)
        self.open_when_done_check.setEnabled(not running)
        self.recent_combo.setEnabled(not running)
        self.use_recent_button.setEnabled(not running)
        self.clear_history_button.setEnabled(not running)
        self.clean_partials_button.setEnabled(not running)
        for button in (
            self.paste_button,
            self.import_list_button,
            self.remove_button,
            self.move_up_button,
            self.move_down_button,
            self.open_file_button,
            self.open_folder_button,
        ):
            button.setEnabled(not running)
        self.import_rss_button.setEnabled(not running and self._feed_worker is None)
        self.statusBar().showMessage("Descargando..." if running else "Preparado")

    def closeEvent(self, event) -> None:
        self.close_requested.emit(event)
        if event.isAccepted():
            if self._feed_worker is not None:
                self._feed_worker.wait(11000)
            self._save_timer.stop()
            self._write_queue()
            self._save_podcast_state()
            self._settings.sync()
