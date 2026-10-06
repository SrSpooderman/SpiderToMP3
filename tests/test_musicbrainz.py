import json
import unittest
from unittest.mock import patch

import services.musicbrainz as musicbrainz
from services.musicbrainz import parse_recordings


class MusicBrainzTests(unittest.TestCase):
    def test_parse_recordings_returns_explicit_choices_with_album_and_credit(self):
        payload = {
            "recordings": [
                {
                    "id": "recording-id",
                    "title": "Canción",
                    "score": 92,
                    "artist-credit": [{"name": "Artista"}, " feat. ", {"name": "Invitado"}],
                    "releases": [{"title": "Álbum"}],
                }
            ]
        }
        match = parse_recordings(json.dumps(payload).encode("utf-8"))[0]
        self.assertEqual(
            (match.title, match.artist, match.album, match.score), ("Canción", "Artista feat. Invitado", "Álbum", 92)
        )

    def test_rejects_invalid_response(self):
        with self.assertRaisesRegex(ValueError, "inválida"):
            parse_recordings(b"{}")

    def test_lookup_identifies_client_and_limits_repeated_requests(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _limit):
                return b'{"recordings": []}'

        musicbrainz._last_request = 0.0
        with (
            patch("services.musicbrainz.urlopen", return_value=Response()) as request,
            patch("services.musicbrainz.time.monotonic", side_effect=[100.0, 100.0, 100.2, 101.2]),
            patch("services.musicbrainz.time.sleep") as sleep,
        ):
            self.assertEqual(musicbrainz.search_recordings("Canción"), [])
            self.assertEqual(musicbrainz.search_recordings("Canción"), [])
        self.assertEqual(request.call_count, 2)
        self.assertIn("SpiderToMP3", request.call_args.args[0].get_header("User-agent"))
        sleep.assert_called_once()
        self.assertGreaterEqual(sleep.call_args.args[0], 0.8)


if __name__ == "__main__":
    unittest.main()
