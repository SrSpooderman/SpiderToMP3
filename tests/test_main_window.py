import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from config import APP_VERSION
from models import DownloadRequest
from qt import QApplication, QLabel, QSettings
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


if __name__ == "__main__":
    unittest.main()
