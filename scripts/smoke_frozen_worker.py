from __future__ import annotations

import math
import shutil
import struct
import sys
import tempfile
import wave
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from unittest.mock import patch

from controllers.download_worker import DownloadWorker
from models import DownloadSettings


def main(binary: Path) -> None:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("La prueba del ejecutable necesita FFmpeg y ffprobe")
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        with wave.open(str(root / "tone.wav"), "wb") as audio:
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
            settings = DownloadSettings(
                urls=[f"http://127.0.0.1:{server.server_port}/tone.wav"],
                output_dir=root / "out",
                audio_format="mp3",
                audio_quality=2,
                filename_template="%(title)s.%(ext)s",
                include_playlist=False,
                open_output_dir_when_done=False,
            )
            worker = DownloadWorker(settings)
            finished: list[tuple[bool, str]] = []
            worker.finished.connect(lambda success, message: finished.append((success, message)))
            with patch.object(sys, "executable", str(binary.resolve())), patch.object(
                sys, "frozen", True, create=True
            ):
                worker.run()
            result = root / "out" / "tone.mp3"
            if len(finished) != 1 or not finished[0][0] or not result.is_file() or result.stat().st_size == 0:
                raise RuntimeError(f"El ejecutable no convirtió el WAV local: {finished}")
            print("Conversión real con el ejecutable verificada.")
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    main(Path(sys.argv[1]))
