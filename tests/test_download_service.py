import tempfile
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from yt_dlp.utils import DownloadError

from config import QUALITY_OPTIONS
from models import DownloadRequest, DownloadSettings
from services.download_service import DownloadCancelled, DownloadService


class Events:
    def __init__(self):
        self.logs = []
        self.progress = []
        self.states = []
        self.cancelled = False

    def emit_log(self, message):
        self.logs.append(message)

    def emit_progress(self, value):
        self.progress.append(value)

    def emit_current_title(self, title):
        pass

    def emit_item_state(self, key, title, state, url):
        self.states.append((key, title, state, url))

    def ask_duplicate(self, path):
        return "skip"

    def should_cancel(self):
        return self.cancelled


class FakeYoutubeDL:
    plans = {}
    failures = set()

    def __init__(self, options):
        self.options = options

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def extract_info(self, url, download=False, process=False):
        if url not in self.plans:
            raise ValueError("Enlace inválido")
        return self.plans[url]

    def process_ie_result(self, info, download=True, extra_info=None):
        if not download:
            return info
        if info["id"] in self.failures:
            raise ValueError("Fallo de prueba")
        progress = self.options["progress_hooks"][0]
        progress({"status": "downloading", "downloaded_bytes": 80, "total_bytes": 100})
        progress({"status": "downloading", "downloaded_bytes": 20, "total_bytes": 100})
        progress({"status": "downloading", "downloaded_bytes": 50, "total_bytes": 100})
        progress({"status": "finished"})
        if "postprocessor_hooks" in self.options:
            self.options["postprocessor_hooks"][0](
                {"status": "finished", "postprocessor": "ExtractAudio"}
            )
        destination = Path(self.prepare_filename({**info, "ext": self.options["postprocessors"][0]["preferredcodec"]}))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"audio")
        return info

    def prepare_filename(self, info):
        return (self.options["outtmpl"].replace("%(title)s", info["title"])
                .replace("%(ext)s", info["ext"]))


class DownloadServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.events = Events()
        self.settings = DownloadSettings(
            urls=["https://test.local/list", "https://test.local/other"],
            output_dir=Path(self.temp.name) / "audio",
            audio_format="mp3",
            audio_quality=2,
            filename_template="%(title)s.%(ext)s",
            include_playlist=True,
            open_output_dir_when_done=False,
        )
        FakeYoutubeDL.plans = {
            "https://test.local/list": {
                "_type": "playlist", "title": "Lista", "entries": [
                    {"_type": "url", "id": "one", "title": "Uno", "url": "https://test.local/one"},
                    {"_type": "url", "id": "two", "title": "Dos", "url": "https://test.local/two"},
                ],
            },
            "https://test.local/other": {"id": "three", "title": "Tres", "webpage_url": "https://test.local/other"},
        }
        FakeYoutubeDL.failures = set()

    def test_playlist_tracks_are_planned_and_progress_reaches_100_last(self):
        with patch("services.download_service.YoutubeDL", FakeYoutubeDL):
            summary = DownloadService(self.events).download(self.settings)

        self.assertEqual((summary.completed, summary.failed), (3, 0))
        self.assertEqual([state for _, _, state, _ in self.events.states].count("pendiente"), 3)
        self.assertEqual([state for _, _, state, _ in self.events.states].count("completado"), 3)
        self.assertEqual([target["url"] for _, _, state, target in self.events.states if state == "pendiente"],
                         ["https://test.local/one", "https://test.local/two", "https://test.local/other"])
        self.assertEqual(self.events.progress[-1], 100)
        self.assertLess(max(self.events.progress[:-1]), 100)
        self.assertEqual(self.events.progress, sorted(self.events.progress))

    def test_failed_track_does_not_stop_remaining_tracks(self):
        FakeYoutubeDL.failures = {"two"}
        with patch("services.download_service.YoutubeDL", FakeYoutubeDL):
            summary = DownloadService(self.events).download(self.settings)
        self.assertEqual((summary.completed, summary.failed), (2, 1))
        self.assertTrue(any(
            key == "1" and title == "Dos" and state == "fallido"
            and target["url"] == "https://test.local/two" and "Fallo de prueba" in target["error"]
            for key, title, state, target in self.events.states
        ))
        self.assertTrue(any(
            key == "2" and title == "Tres" and state == "completado"
            for key, title, state, _ in self.events.states
        ))

    def test_missing_output_is_failure_and_actual_result_path_is_reported(self):
        class MissingYoutubeDL(FakeYoutubeDL):
            def process_ie_result(self, info, download=True, extra_info=None):
                return info

        with patch("services.download_service.YoutubeDL", MissingYoutubeDL):
            summary = DownloadService(self.events).download(self.settings)
        self.assertEqual(summary.completed, 0)
        self.assertEqual(summary.failed, 3)
        self.assertTrue(all(state != "completado" for _, _, state, _ in self.events.states))

        self.events = Events()
        class ActualPathYoutubeDL(FakeYoutubeDL):
            def process_ie_result(self, info, download=True, extra_info=None):
                if not download:
                    return info
                actual = Path(self.options["outtmpl"]).parent / f"actual-{info['id']}.mp3"
                actual.parent.mkdir(parents=True, exist_ok=True)
                actual.write_bytes(b"audio")
                return {**info, "requested_downloads": [{"filepath": str(actual)}]}

        with patch("services.download_service.YoutubeDL", ActualPathYoutubeDL):
            summary = DownloadService(self.events).download(self.settings)
        self.assertEqual(summary.completed, 3)
        completed = [target for _, _, state, target in self.events.states if state == "completado"]
        self.assertTrue(all(Path(item["path"]).is_file() for item in completed))

    def test_retry_targets_only_the_failed_playlist_entry_without_a_direct_url(self):
        FakeYoutubeDL.plans["https://test.local/list"]["entries"][1]["url"] = "two"
        FakeYoutubeDL.failures = {"two"}
        with patch("services.download_service.YoutubeDL", FakeYoutubeDL):
            DownloadService(self.events).download(self.settings)
        target = next(target for _, title, state, target in self.events.states
                      if title == "Dos" and state == "fallido")
        self.assertEqual(target["url"], "https://test.local/list")
        self.assertEqual(target["playlist_path"], [2])
        self.assertEqual(target["expected_id"], "two")

        FakeYoutubeDL.failures = set()
        retry = DownloadSettings(**{
            **self.settings.__dict__, "urls": [target["url"]],
            "retry_requests": [DownloadRequest(target["url"], tuple(target["playlist_path"]),
                                               target["expected_id"])],
        })
        retry_events = Events()
        with patch("services.download_service.YoutubeDL", FakeYoutubeDL):
            summary = DownloadService(retry_events).download(retry)
        self.assertEqual((summary.completed, summary.failed), (1, 0))
        self.assertEqual([title for _, title, state, _ in retry_events.states
                          if state == "completado"], ["Dos"])

        FakeYoutubeDL.plans["https://test.local/list"]["entries"].reverse()
        changed_events = Events()
        with patch("services.download_service.YoutubeDL", FakeYoutubeDL):
            changed = DownloadService(changed_events).download(retry)
        self.assertEqual((changed.completed, changed.failed), (0, 1))
        self.assertIn("lista cambió", changed_events.states[0][3]["error"])

    def test_failed_extraction_does_not_stop_other_urls(self):
        self.settings.urls.insert(0, "https://test.local/bad")
        with patch("services.download_service.YoutubeDL", FakeYoutubeDL):
            summary = DownloadService(self.events).download(self.settings)
        self.assertEqual((summary.completed, summary.failed), (3, 1))
        self.assertEqual(self.events.states[0][2], "fallido")

    def test_playlist_limit_stops_before_materializing_entire_list(self):
        class CountingEntries:
            count = 0
            def __iter__(self):
                for index in range(10000):
                    self.count += 1
                    yield {"id": str(index), "title": str(index)}
        entries = CountingEntries()
        FakeYoutubeDL.plans["https://test.local/list"]["entries"] = entries
        settings = DownloadSettings(**{**self.settings.__dict__, "playlist_limit": 5, "preview_only": True})
        with patch("services.download_service.YoutubeDL", FakeYoutubeDL):
            summary = DownloadService(self.events).download(settings)
        self.assertEqual(summary.failed, 0)
        self.assertEqual(len([state for _, _, state, _ in self.events.states if state == "pendiente"]), 6)
        self.assertEqual(entries.count, 6)

    def test_single_item_mode_does_not_traverse_playlist(self):
        class CountingEntries:
            count = 0
            def __iter__(self):
                for index in range(10000):
                    self.count += 1
                    yield {"id": str(index), "title": str(index)}
        entries = CountingEntries()
        FakeYoutubeDL.plans["https://test.local/list"]["entries"] = entries
        settings = DownloadSettings(**{**self.settings.__dict__, "include_playlist": False, "preview_only": True})
        with patch("services.download_service.YoutubeDL", FakeYoutubeDL):
            DownloadService(self.events).download(settings)
        self.assertEqual(entries.count, 1)

    def test_temporary_network_failure_retries_but_other_errors_do_not(self):
        class FlakyYoutubeDL(FakeYoutubeDL):
            attempts = 0
            def process_ie_result(self, info, download=True, extra_info=None):
                if download:
                    self.__class__.attempts += 1
                    if self.__class__.attempts == 1:
                        raise DownloadError("HTTP Error 503")
                return super().process_ie_result(info, download, extra_info)
        settings = DownloadSettings(**{**self.settings.__dict__, "urls": ["https://test.local/other"],
                                       "network_attempts": 2})
        with patch("services.download_service.YoutubeDL", FlakyYoutubeDL):
            summary = DownloadService(self.events).download(settings)
        self.assertEqual((summary.completed, summary.failed), (1, 0))
        self.assertEqual(FlakyYoutubeDL.attempts, 2)

        FakeYoutubeDL.failures = {"three"}
        self.events = Events()
        settings = DownloadSettings(**{**settings.__dict__, "output_dir": settings.output_dir / "other"})
        with patch("services.download_service.YoutubeDL", FakeYoutubeDL):
            failed = DownloadService(self.events).download(settings)
        self.assertEqual((failed.completed, failed.failed), (0, 1))

    def test_cancel_during_download_stops_work(self):
        class CancellingYoutubeDL(FakeYoutubeDL):
            def process_ie_result(inner_self, info, download=True, extra_info=None):
                self.events.cancelled = True
                inner_self.options["progress_hooks"][0]({"status": "downloading"})

        with patch("services.download_service.YoutubeDL", CancellingYoutubeDL):
            with self.assertRaises(DownloadCancelled):
                DownloadService(self.events).download(self.settings)
        self.assertNotIn(100, self.events.progress)

    def test_quality_setting_is_only_passed_for_lossy_formats(self):
        service = DownloadService(self.events)
        self.assertEqual(service._options(self.settings)["postprocessors"][0]["preferredquality"], "2")
        if sys.platform.startswith("linux"):
            self.assertIn("no-certifi", service._options(self.settings)["compat_opts"])
        lossless = DownloadSettings(**{**self.settings.__dict__, "audio_format": "flac", "audio_quality": None})
        self.assertNotIn("preferredquality", service._options(lossless)["postprocessors"][0])

    def test_each_format_passes_its_selected_quality(self):
        service = DownloadService(self.events)
        for audio_format, options in QUALITY_OPTIONS.items():
            for _, quality in options:
                settings = DownloadSettings(**{
                    **self.settings.__dict__, "audio_format": audio_format, "audio_quality": quality
                })
                postprocessor = service._options(settings)["postprocessors"][0]
                self.assertEqual(postprocessor["preferredcodec"], audio_format)
                self.assertEqual(postprocessor.get("preferredquality"),
                                 None if quality is None else str(quality))


if __name__ == "__main__":
    unittest.main()
