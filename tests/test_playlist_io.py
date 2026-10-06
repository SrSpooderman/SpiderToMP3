import tempfile
import unittest
from pathlib import Path

from services.playlist_io import PlaylistRecord, read_playlist, write_playlist


class PlaylistIOTests(unittest.TestCase):
    def test_csv_and_m3u_round_trip_title_source_status_and_local_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audio = root / "canción.mp3"
            audio.write_bytes(b"audio")
            records = [
                PlaylistRecord("Tema, uno", "https://example.test/one?part=1,2", "completado", str(audio)),
                PlaylistRecord("Tema dos", "https://example.test/two", "pendiente"),
            ]
            for extension in ("csv", "m3u"):
                path = root / f"lista.{extension}"
                write_playlist(path, records)
                self.assertEqual(read_playlist(path), records)

    def test_plain_m3u_accepts_web_urls_and_relative_local_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audio = root / "local.mp3"
            audio.write_bytes(b"audio")
            path = root / "lista.m3u8"
            path.write_text(
                "#EXTM3U\n#EXTINF:-1,Enlace\nhttps://example.test/track\n#EXTINF:-1,Archivo local\nlocal.mp3\n",
                encoding="utf-8",
            )
            self.assertEqual(
                read_playlist(path),
                [
                    PlaylistRecord("Enlace", "https://example.test/track"),
                    PlaylistRecord("Archivo local", "", "completado", str(audio)),
                ],
            )

    def test_rejects_invalid_url_and_oversized_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "lista.csv"
            path.write_text("title,url,status,path\nMala,ftp://example.test/a,pendiente,\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "HTTP"):
                read_playlist(path)
            path.write_bytes(b"x" * (5 * 1024 * 1024 + 1))
            with self.assertRaisesRegex(ValueError, "5 MiB"):
                read_playlist(path)

    def test_csv_title_cannot_be_interpreted_as_a_formula(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "lista.csv"
            record = PlaylistRecord('=HYPERLINK("https://example.test")', "https://example.test/audio")
            write_playlist(path, [record])
            self.assertIn("'=HYPERLINK", path.read_text(encoding="utf-8-sig"))
            self.assertEqual(read_playlist(path), [record])


if __name__ == "__main__":
    unittest.main()
