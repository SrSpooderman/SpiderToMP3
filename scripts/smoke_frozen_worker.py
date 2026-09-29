from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from controllers.download_worker import DownloadWorker
from models import DownloadSettings


def main(binary: Path) -> None:
    with tempfile.TemporaryDirectory() as temp:
        settings = DownloadSettings(
            urls=["invalid:"],
            output_dir=Path(temp),
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
        if len(finished) != 1 or finished[0][0] or "1 fallidos" not in finished[0][1]:
            raise RuntimeError(f"El ejecutable no respondió por la conexión local: {finished}")
        print("Comunicación con el ejecutable verificada.")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
