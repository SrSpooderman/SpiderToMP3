import unittest
from pathlib import Path

from models import DownloadRequest, DownloadSettings
from services.worker_process import settings_from_payload, settings_to_payload


class WorkerProtocolTests(unittest.TestCase):
    def test_retry_identity_survives_the_process_boundary(self):
        request = DownloadRequest("https://example.test/list", (2, 4), "audio-id")
        settings = DownloadSettings(
            urls=[request.url], output_dir=Path("/tmp/spider-audio"),
            audio_format="mp3", audio_quality=2, filename_template="%(id)s.%(ext)s",
            include_playlist=True, open_output_dir_when_done=False,
            retry_requests=[request],
        )
        restored = settings_from_payload(settings_to_payload(settings))
        self.assertEqual(restored.retry_requests, [request])


if __name__ == "__main__":
    unittest.main()
