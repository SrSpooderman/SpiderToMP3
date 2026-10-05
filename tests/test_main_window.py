import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtTest import QTest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from config import APP_VERSION
from models import DownloadRequest
from qt import QApplication, QLabel, QListWidget, QMessageBox, QSettings, QTimer, Qt
from views.main_window import MainWindow


class MainWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_preferences_history_quality_and_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            settings = QSettings(str(Path(temp) / "settings.ini"), QSettings.IniFormat)
            with patch("views.main_window.QSettings", return_value=settings):
                window = MainWindow()
                window.set_output_dir(str(Path(temp) / "audio"))
                window.format_combo.setCurrentText("flac")
                self.assertIsNone(window.audio_quality())
                window.save_preferences(["https://example.test/one", "https://example.test/two"])
                window.update_item("0", "Prueba", "fallido", "https://example.test/one")
                self.assertEqual(window.failed_urls(), ["https://example.test/one"])
                window.update_item("1", "Otra", "fallido", {
                    "url": "https://example.test/list", "playlist_path": [3],
                    "error": "No se pudo convertir",
                })
                self.assertIn(DownloadRequest("https://example.test/list", (3,)),
                              window.failed_requests())
                self.assertIn("No se pudo convertir", window.queue_list.item(1).text())
                window.set_running(False)
                self.assertTrue(window.retry_button.isEnabled())
                window.close()

                restored = MainWindow()
                self.assertEqual(restored.output_dir_text(), str(Path(temp) / "audio"))
                self.assertEqual(restored.audio_format(), "flac")
                self.assertEqual(restored.recent_combo.count(), 2)
                restored.clear_history()
                self.assertEqual(restored.recent_combo.count(), 0)
                restored.close()

    def test_accessible_labels_and_field_errors(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch("views.main_window.QSettings", return_value=QSettings(
                str(Path(temp) / "settings.ini"), QSettings.IniFormat
            )):
                window = MainWindow()
            window.show()
            self.app.processEvents()
            window.set_validation_errors({"urls": "Falta un enlace", "output": "Carpeta inválida"})
            self.app.processEvents()
            self.assertEqual(window.url_error.text(), "Falta un enlace")
            self.assertEqual(window.output_error.text(), "Carpeta inválida")
            self.assertTrue(window.url_edit.hasFocus())
            self.assertEqual(window.queue_list.accessibleName(), "Cola de audios")
            self.assertFalse(window.windowIcon().isNull())
            buddies = {label.buddy() for label in window.findChildren(QLabel)}
            self.assertTrue({window.url_edit, window.output_edit, window.format_combo,
                             window.quality_combo, window.template_edit}.issubset(buddies))
            window.close()

    def test_log_is_bounded_can_be_copied_and_about_shows_version(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch("views.main_window.QSettings", return_value=QSettings(
                str(Path(temp) / "settings.ini"), QSettings.IniFormat
            )):
                window = MainWindow()
            for index in range(1005):
                window.append_log(f"Línea {index}")
            self.assertLessEqual(window.log_view.document().blockCount(), 1000)
            window.copy_log_button.click()
            self.assertIn("Línea 1004", self.app.clipboard().text())
            with patch("views.main_window.QMessageBox.about") as about:
                window.menuBar().actions()[0].menu().actions()[1].trigger()
            self.assertIn(APP_VERSION, about.call_args.args[2])
            requested = []
            window.check_updates_requested.connect(lambda: requested.append(True))
            window.menuBar().actions()[0].menu().actions()[0].trigger()
            self.assertEqual(requested, [True])
            window.close()

    def test_queue_restores_pending_without_repeating_completed_and_can_clear_history(self):
        with tempfile.TemporaryDirectory() as temp:
            settings = QSettings(str(Path(temp) / "settings.ini"), QSettings.IniFormat)
            with patch("views.main_window.QSettings", return_value=settings):
                window = MainWindow()
                window.update_item("0", "Hecho", "completado", {"url": "https://example.test/a", "path": str(Path(temp) / "a.mp3")})
                window.update_item("1", "En curso", "descargando", {"url": "https://example.test/b"})
                window.close()
                restored = MainWindow()
                self.assertEqual(restored.queue_list.count(), 2)
                self.assertEqual(restored.pending_requests(), [DownloadRequest("https://example.test/b")])
                restored.clear_history()
                restored.close()
                empty = MainWindow()
                self.assertEqual(empty.queue_list.count(), 0)
                empty.close()

    def test_copy_log_and_queue_hide_url_secrets(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch("views.main_window.QSettings", return_value=QSettings(
                str(Path(temp) / "settings.ini"), QSettings.IniFormat
            )):
                window = MainWindow()
            secret_url = "https://example.test/audio?token=secret123"
            window.append_log(f"Error con {secret_url}")
            window.update_item("0", secret_url, "fallido", {"url": secret_url, "error": secret_url})
            window.copy_log()
            self.assertNotIn("secret123", self.app.clipboard().text())
            self.assertNotIn("secret123", window.queue_list.item(0).text())
            window.close()

    def test_preview_can_deselect_items_and_queue_can_reorder(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch("views.main_window.QSettings", return_value=QSettings(
                str(Path(temp) / "settings.ini"), QSettings.IniFormat
            )):
                window = MainWindow()
            first = {"url": "https://example.test/a", "source": "Origen", "duration": 70}
            second = {"url": "https://example.test/b", "source": "Origen", "duration": 90}
            window.update_item("0", "Uno", "pendiente", first)
            window.update_item("1", "Dos", "pendiente", second)
            def choose_second():
                dialog = self.app.activeModalWidget()
                choices = dialog.findChild(QListWidget)
                choices.item(0).setCheckState(Qt.Unchecked)
                dialog.accept()
            QTimer.singleShot(0, choose_second)
            self.assertEqual(window.choose_preview_items(), [DownloadRequest("https://example.test/b")])
            window.queue_list.setCurrentRow(1)
            window.move_selected(-1)
            self.assertIn("Dos", window.queue_list.item(0).text())
            window.close()

    def test_cleanup_only_removes_recorded_new_partial_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch("views.main_window.QSettings", return_value=QSettings(
                str(root / "settings.ini"), QSettings.IniFormat
            )):
                window = MainWindow()
            window.set_output_dir(temp)
            partial = root / "new.wav.part"
            partial.write_bytes(b"partial")
            existing = root / "old.wav.part"
            existing.write_bytes(b"previous")
            window.update_item("0", "Uno", "fallido", {
                "url": "https://example.test/a", "partial_paths": [str(partial)]
            })
            with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
                window.clean_partials()
            self.assertFalse(partial.exists())
            self.assertEqual(existing.read_bytes(), b"previous")
            window.close()

    def test_keyboard_shortcuts_paste_remove_and_high_contrast(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch("views.main_window.QSettings", return_value=QSettings(
                str(Path(temp) / "settings.ini"), QSettings.IniFormat
            )):
                window = MainWindow()
            window.show()
            window.activateWindow()
            window.url_edit.setFocus()
            self.app.processEvents()
            self.app.clipboard().setText("https://example.test/a\nhttps://example.test/a")
            QTest.keyClick(window.url_edit, Qt.Key_V, Qt.ControlModifier | Qt.ShiftModifier)
            self.app.processEvents()
            self.assertEqual(window.urls_text().strip(), "https://example.test/a")
            window.update_item("0", "Uno", "fallido", {"url": "https://example.test/a"})
            window.queue_list.setFocus()
            window.queue_list.setCurrentRow(0)
            QTest.keyClick(window.queue_list, Qt.Key_Delete)
            self.assertEqual(window.queue_list.count(), 0)
            window.theme_combo.setCurrentText("Alto contraste")
            self.assertIn("#ffff00", self.app.styleSheet())
            window.close()


if __name__ == "__main__":
    unittest.main()
