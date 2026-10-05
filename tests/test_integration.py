import math
import os
import shutil
import struct
import tempfile
import time
import unittest
import wave
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Event, Thread
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from controllers.main_controller import MainController
from models import DownloadRequest, DownloadSettings
from qt import QApplication, QSettings
from services.download_service import DownloadService
from views.main_window import MainWindow


class Events:
    def __init__(self):
        self.states = []
        self.progress = []

    def emit_log(self, message):
        pass

    def emit_progress(self, value):
        self.progress.append(value)

    def emit_current_title(self, title):
        pass

    def emit_item_state(self, key, title, state, url):
        self.states.append(state)

    def should_cancel(self):
        return False

    def ask_duplicate(self, path):
        return "skip"


@contextmanager
def local_audio():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        sample = root / "tone.wav"
        with wave.open(str(sample), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(22050)
            audio.writeframes(b"".join(
                struct.pack("<h", int(4000 * math.sin(2 * math.pi * 440 * i / 22050)))
                for i in range(22050)
            ))

        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(root), **kwargs)

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        Thread(target=server.serve_forever, daemon=True).start()
        try:
            yield root, f"http://127.0.0.1:{server.server_port}/tone.wav"
        finally:
            server.shutdown()
            server.server_close()


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg no disponible")
class IntegrationTests(unittest.TestCase):
    def test_conversion_uses_local_audio_without_internet(self):
        with local_audio() as (root, url):
            settings = DownloadSettings([url], root / "out", "mp3", 2,
                                        "%(title)s.%(ext)s", False, False)
            events = Events()
            summary = DownloadService(events).download(settings)
            self.assertEqual((summary.completed, summary.failed), (1, 0))
            self.assertTrue((root / "out" / "tone.mp3").is_file())
            self.assertEqual(events.progress[-1], 100)
            self.assertIn("convirtiendo", events.states)
            self.assertEqual(events.states[-1], "completado")

    def test_existing_audio_is_reported_and_never_overwritten(self):
        with local_audio() as (root, url):
            output = root / "out"
            output.mkdir()
            existing = output / "tone.mp3"
            existing.write_bytes(b"archivo anterior")
            settings = DownloadSettings([url], output, "mp3", 2,
                                        "%(title)s.%(ext)s", False, False, duplicate_policy="ask")
            events = Events()
            summary = DownloadService(events).download(settings)
            self.assertEqual((summary.completed, summary.failed, summary.skipped), (0, 0, 1))
            self.assertEqual(existing.read_bytes(), b"archivo anterior")
            self.assertIn("omitido", events.states)

    def test_duplicate_can_be_skipped_or_renamed_without_overwrite(self):
        with local_audio() as (root, url):
            output = root / "out"
            output.mkdir()
            existing = output / "tone.mp3"
            existing.write_bytes(b"archivo anterior")
            base = DownloadSettings([url], output, "mp3", 2, "%(title)s.%(ext)s", False, False)
            skipped = DownloadService(Events()).download(base)
            self.assertEqual((skipped.completed, skipped.failed, skipped.skipped), (0, 0, 1))
            renamed = DownloadService(Events()).download(DownloadSettings(
                **{**base.__dict__, "duplicate_policy": "rename"}
            ))
            self.assertEqual((renamed.completed, renamed.failed), (1, 0))
            self.assertEqual(existing.read_bytes(), b"archivo anterior")
            self.assertTrue((output / "tone (2).mp3").is_file())

    def test_archive_skips_same_source_id_after_name_pattern_changes(self):
        with local_audio() as (root, url):
            base = DownloadSettings([url], root / "out", "mp3", 2,
                                    "%(title)s.%(ext)s", False, False, archive_enabled=True)
            first = DownloadService(Events()).download(base)
            second = DownloadService(Events()).download(DownloadSettings(
                **{**base.__dict__, "filename_template": "%(title)s [%(id)s].%(ext)s"}
            ))
            self.assertEqual((first.completed, second.skipped, second.failed), (1, 1, 0))
            self.assertFalse((root / "out" / "tone [tone].mp3").exists())

    def test_qt_window_and_worker_finish_cleanly(self):
        app = QApplication.instance() or QApplication([])
        with local_audio() as (root, url):
            with patch("views.main_window.QSettings", return_value=QSettings(
                str(root / "settings.ini"), QSettings.IniFormat
            )):
                window = MainWindow()
            controller = MainController(window)
            window.url_edit.setPlainText(url)
            window.set_output_dir(str(root / "out"))
            window.open_when_done_check.setChecked(False)
            window.choose_preview_items = lambda: [DownloadRequest(url)]
            with patch("controllers.main_controller.QMessageBox.warning"):
                controller.start_download()
                deadline = time.monotonic() + 30
                while controller.is_running and time.monotonic() < deadline:
                    app.processEvents()
                    time.sleep(0.02)
            self.assertFalse(controller.is_running)
            self.assertTrue((root / "out" / "tone [tone].mp3").is_file())
            self.assertEqual(window.queue_list.count(), 1)
            self.assertIn("Completado", window.queue_list.item(0).text())
            window.close()

    def test_duplicate_question_from_worker_can_be_answered_in_gui(self):
        app = QApplication.instance() or QApplication([])
        with local_audio() as (root, url):
            output = root / "out"
            output.mkdir()
            existing = output / "tone [tone].mp3"
            existing.write_bytes(b"anterior")
            with patch("views.main_window.QSettings", return_value=QSettings(
                str(root / "settings.ini"), QSettings.IniFormat
            )):
                window = MainWindow()
            controller = MainController(window)
            window.url_edit.setPlainText(url)
            window.set_output_dir(str(output))
            window.open_when_done_check.setChecked(False)
            window.duplicate_combo.setCurrentIndex(window.duplicate_combo.findData("ask"))
            window.choose_preview_items = lambda: [DownloadRequest(url)]
            answered = []
            def answer(path):
                answered.append(path)
                controller.worker.answer_duplicate("rename")
            with patch.object(controller, "ask_duplicate", side_effect=answer), \
                    patch("controllers.main_controller.QMessageBox.warning"):
                controller.start_download()
                deadline = time.monotonic() + 30
                while controller.is_running and time.monotonic() < deadline:
                    app.processEvents()
                    time.sleep(0.02)
            self.assertTrue(answered)
            self.assertEqual(existing.read_bytes(), b"anterior")
            self.assertTrue((output / "tone [tone] (2).mp3").is_file())
            window.close()

    def test_cancel_interrupts_a_stalled_request(self):
        app = QApplication.instance() or QApplication([])
        received = Event()

        class SlowHandler(SimpleHTTPRequestHandler):
            def do_GET(self):
                received.set()
                Event().wait(20)

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), SlowHandler)
        server.daemon_threads = True
        Thread(target=server.serve_forever, daemon=True).start()
        try:
            with tempfile.TemporaryDirectory() as temp:
                with patch("views.main_window.QSettings", return_value=QSettings(
                    str(Path(temp) / "settings.ini"), QSettings.IniFormat
                )):
                    window = MainWindow()
                controller = MainController(window)
                window.url_edit.setPlainText(f"http://127.0.0.1:{server.server_port}/slow")
                window.set_output_dir(str(Path(temp) / "out"))
                window.open_when_done_check.setChecked(False)
                with patch("controllers.main_controller.QMessageBox.warning"):
                    controller.start_download()
                    deadline = time.monotonic() + 10
                    while not received.is_set() and time.monotonic() < deadline:
                        app.processEvents()
                        time.sleep(0.02)
                    self.assertTrue(received.is_set())
                    start = time.monotonic()
                    controller.cancel_download()
                    while controller.is_running and time.monotonic() - start < 5:
                        app.processEvents()
                        time.sleep(0.02)
                self.assertFalse(controller.is_running)
                self.assertLess(time.monotonic() - start, 5)
                window.close()
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
