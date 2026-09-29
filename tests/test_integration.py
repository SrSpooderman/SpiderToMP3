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
from models import DownloadSettings
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
                                        "%(title)s.%(ext)s", False, False)
            events = Events()
            summary = DownloadService(events).download(settings)
            self.assertEqual((summary.completed, summary.failed), (0, 1))
            self.assertEqual(existing.read_bytes(), b"archivo anterior")
            self.assertIn("fallido", events.states)

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
