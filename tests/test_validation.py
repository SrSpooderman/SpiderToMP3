import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from models import DownloadSettings
from services.validation import validate_settings


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = DownloadSettings(
            urls=["https://example.test/audio"],
            output_dir=Path(self.temp.name) / "audio",
            audio_format="mp3",
            audio_quality=2,
            filename_template="%(title)s.%(ext)s",
            include_playlist=False,
            open_output_dir_when_done=False,
        )

    def test_accepts_writable_directory_and_valid_template(self):
        with patch("services.validation.shutil.which", return_value="/usr/bin/ffmpeg"):
            self.assertEqual(validate_settings(self.settings), {})

    def test_rejects_template_outside_output_directory(self):
        settings = DownloadSettings(**{**self.settings.__dict__, "filename_template": "../fuera.%(ext)s"})
        with patch("services.validation.shutil.which", return_value="/usr/bin/ffmpeg"):
            self.assertIn("template", validate_settings(settings))

    def test_rejects_malformed_template(self):
        settings = DownloadSettings(**{**self.settings.__dict__, "filename_template": "%(title"})
        with patch("services.validation.shutil.which", return_value="/usr/bin/ffmpeg"):
            self.assertIn("template", validate_settings(settings))

    def test_reports_missing_ffmpeg(self):
        with patch("services.validation.shutil.which", return_value=None):
            self.assertIn("ffmpeg", validate_settings(self.settings))

    def test_reports_unwritable_output_target(self):
        target = Path(self.temp.name) / "file"
        target.write_text("ocupado")
        settings = DownloadSettings(**{**self.settings.__dict__, "output_dir": target})
        with patch("services.validation.shutil.which", return_value="/usr/bin/ffmpeg"):
            self.assertIn("output", validate_settings(settings))

    def test_rejects_invalid_urls_before_starting(self):
        for url in ("archivo.mp3", "file:///tmp/audio", "https://", "https://ejemplo.test:abc/audio"):
            settings = DownloadSettings(**{**self.settings.__dict__, "urls": [url]})
            with patch("services.validation.shutil.which", return_value="/usr/bin/ffmpeg"):
                self.assertIn("urls", validate_settings(settings), url)

    def test_rejects_quality_from_another_format(self):
        settings = DownloadSettings(**{**self.settings.__dict__, "audio_quality": 256})
        with patch("services.validation.shutil.which", return_value="/usr/bin/ffmpeg"):
            self.assertIn("format", validate_settings(settings))


if __name__ == "__main__":
    unittest.main()
