import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from yt_dlp.postprocessor.ffmpeg import FFmpegExtractAudioPP

from models import DownloadSettings
from services.download_service import DownloadCancelled, DownloadService


class Events:
    def __init__(self):
        self.logs = []
        self.progress = []
        self.titles = []
        self.done = []
        self.cancelled = False

    def emit_log(self, message):
        self.logs.append(message)

    def emit_progress(self, value):
        self.progress.append(value)

    def emit_current_title(self, title):
        self.titles.append(title)

    def emit_item_done(self, title):
        self.done.append(title)

    def should_cancel(self):
        return self.cancelled


class FakeYoutubeDL:
    def __init__(self, options):
        self.options = options
        self.downloaded = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def download(self, urls):
        self.downloaded.extend(urls)
        previously_done = list(self.events.done)
        title = urls[0]
        info = {"title": title}
        self.options["progress_hooks"][0](
            {"status": "downloading", "info_dict": info, "downloaded_bytes": 50,
             "total_bytes": 100}
        )
        self.options["progress_hooks"][0]({"status": "finished", "info_dict": info})
        if self.events.done != previously_done:
            raise AssertionError("El elemento sigue en conversión")
        self.options["postprocessor_hooks"][0](
            {"status": "finished", "postprocessor": FFmpegExtractAudioPP.pp_key(),
             "info_dict": info}
        )


class DownloadServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.events = Events()
        self.settings = DownloadSettings(
            urls=["https://a.test/1", "https://b.test/2"],
            output_dir=Path(self.temp.name) / "audio",
            audio_format="mp3",
            audio_quality=5,
            filename_template="%(title)s.%(ext)s",
            include_playlist=False,
            open_output_dir_when_done=False,
        )

    def test_download_uses_settings_and_marks_items_after_conversion(self):
        instances = []

        def create_ydl(options):
            ydl = FakeYoutubeDL(options)
            ydl.events = self.events
            instances.append(ydl)
            return ydl

        with patch("services.download_service.YoutubeDL", side_effect=create_ydl):
            DownloadService(self.events).download(self.settings)

        self.assertTrue(self.settings.output_dir.is_dir())
        self.assertEqual([ydl.downloaded for ydl in instances],
                         [["https://a.test/1"], ["https://b.test/2"]])
        self.assertEqual(instances[0].options["noplaylist"], True)
        self.assertEqual(instances[0].options["outtmpl"],
                         str(self.settings.output_dir / self.settings.filename_template))
        self.assertEqual(instances[0].options["postprocessors"][0]["preferredcodec"], "mp3")
        self.assertEqual(self.events.done, self.settings.urls)
        self.assertEqual(self.events.progress, [0, 25, 50, 75, 100])

    def test_cancel_before_first_url_skips_youtube_dl(self):
        self.events.cancelled = True
        with patch("services.download_service.YoutubeDL") as youtube_dl:
            with self.assertRaises(DownloadCancelled):
                DownloadService(self.events).download(self.settings)
        youtube_dl.assert_not_called()

    def test_cancel_during_download_stops_remaining_urls(self):
        def create_ydl(options):
            class CancellingYoutubeDL(FakeYoutubeDL):
                def download(inner_self, urls):
                    self.events.cancelled = True
                    options["progress_hooks"][0]({"status": "downloading"})

            return CancellingYoutubeDL(options)

        with patch("services.download_service.YoutubeDL", side_effect=create_ydl) as youtube_dl:
            with self.assertRaises(DownloadCancelled):
                DownloadService(self.events).download(self.settings)
        self.assertEqual(youtube_dl.call_count, 1)

    def test_postprocessor_only_marks_finished_audio_conversion(self):
        hook = DownloadService(self.events)._postprocessor_hook()
        info = {"title": "Canción"}
        hook({"status": "started", "postprocessor": FFmpegExtractAudioPP.pp_key(), "info_dict": info})
        hook({"status": "finished", "postprocessor": "Otro", "info_dict": info})
        self.assertEqual(self.events.done, [])
        hook({"status": "finished", "postprocessor": FFmpegExtractAudioPP.pp_key(), "info_dict": info})
        self.assertEqual(self.events.done, ["Canción"])


if __name__ == "__main__":
    unittest.main()
