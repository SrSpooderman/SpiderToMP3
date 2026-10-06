import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from services.podcast_rss import fetch_rss, parse_rss


class PodcastRSSTests(unittest.TestCase):
    def test_only_audio_enclosures_are_imported_with_stable_identity(self):
        feed = b"""<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item><title>Episode one</title><guid>episode-1</guid><pubDate>Mon, 05 Oct 2026 10:00:00 GMT</pubDate>
    <enclosure url="/audio/one.mp3" type="audio/mpeg"/></item>
  <item><title>Trailer</title><enclosure url="/video.mp4" type="video/mp4"/></item>
  <item><title>Episode two</title><enclosure url="https://cdn.example.test/two.opus" type="audio/ogg"/></item>
</channel></rss>"""
        episodes = parse_rss(feed, "https://example.test/feed.xml")
        self.assertEqual(
            [episode.url for episode in episodes],
            ["https://example.test/audio/one.mp3", "https://cdn.example.test/two.opus"],
        )
        self.assertEqual(episodes[0].guid, "episode-1")
        self.assertEqual(episodes[1].guid, episodes[1].url)

    def test_rejects_invalid_or_empty_feed(self):
        with self.assertRaisesRegex(ValueError, "XML"):
            parse_rss(b"<rss", "https://example.test/feed")
        with self.assertRaisesRegex(ValueError, "audio"):
            parse_rss(
                b"<rss><channel><item><title>No audio</title></item></channel></rss>", "https://example.test/feed"
            )

    def test_fetches_feed_from_local_http_without_downloading_episode(self):
        requested = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                requested.append(self.path)
                payload = (
                    b"<rss><channel><item><title>Uno</title>"
                    b'<enclosure url="/episode.mp3" type="audio/mpeg"/>'
                    b"</item></channel></rss>"
                )
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            episodes = fetch_rss(f"http://127.0.0.1:{server.server_port}/feed.xml")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        self.assertEqual(len(episodes), 1)
        self.assertEqual(requested, ["/feed.xml"])
        self.assertTrue(episodes[0].url.endswith("/episode.mp3"))


if __name__ == "__main__":
    unittest.main()
