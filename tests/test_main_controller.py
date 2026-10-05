import unittest
from unittest.mock import Mock, patch

from controllers.main_controller import MainController
from models import DownloadRequest
from qt import QMessageBox


class MainControllerCloseTests(unittest.TestCase):
    def setUp(self):
        self.controller = MainController.__new__(MainController)
        self.controller.window = Mock()
        self.controller.thread = Mock()
        self.controller.worker = Mock()
        self.controller._close_when_finished = False
        self.controller._selected_preview_requests = []

    def test_close_during_download_waits_for_worker_to_finish(self):
        event = Mock()
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            self.controller.handle_close_request(event)

        event.ignore.assert_called_once()
        event.accept.assert_not_called()
        self.controller.worker.cancel.assert_called_once()
        self.controller.thread.wait.assert_not_called()
        self.controller.thread_finished()
        self.controller.window.close.assert_called_once()

    def test_declining_close_keeps_download_running(self):
        event = Mock()
        with patch.object(QMessageBox, "question", return_value=QMessageBox.No):
            self.controller.handle_close_request(event)

        event.ignore.assert_called_once()
        self.controller.worker.cancel.assert_not_called()
        self.assertFalse(self.controller._close_when_finished)

    def test_thread_completion_enables_controls(self):
        self.controller.thread_finished()

        self.assertIsNone(self.controller.thread)
        self.assertIsNone(self.controller.worker)
        self.controller.window.set_running.assert_called_once_with(False)

    def test_close_when_idle_is_accepted(self):
        self.controller.thread = None
        event = Mock()

        self.controller.handle_close_request(event)

        event.accept.assert_called_once()
        event.ignore.assert_not_called()

    def test_retry_uses_only_failed_urls(self):
        self.controller.thread = None
        request = DownloadRequest("https://example.test/list", (2,))
        self.controller.window.failed_requests.return_value = [request]
        with patch.object(self.controller, "_begin_download") as begin:
            self.controller.retry_failed()
        begin.assert_called_once_with(["https://example.test/list"], [request], preserve_queue=True)

    def test_cancelled_download_updates_queue_state(self):
        with patch.object(QMessageBox, "warning"):
            self.controller.download_finished(False, "Descarga cancelada.")
        self.controller.window.mark_active_cancelled.assert_called_once()


if __name__ == "__main__":
    unittest.main()
