import subprocess
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

import psutil

from controllers.download_worker import DownloadWorker
from models import DownloadSettings


class DownloadWorkerCancellationTests(unittest.TestCase):
    def test_cancel_kills_the_process_and_its_child(self):
        with tempfile.TemporaryDirectory() as temp:
            settings = DownloadSettings([], Path(temp), "mp3", 2, "%(title)s.%(ext)s", False, False)
            worker = DownloadWorker(settings)
            code = (
                "import subprocess,sys,time; "
                "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); "
                "time.sleep(60)"
            )
            parent = subprocess.Popen([sys.executable, "-c", code])
            worker._process = parent
            try:
                deadline = time.monotonic() + 5
                children = []
                while not children and time.monotonic() < deadline:
                    children = psutil.Process(parent.pid).children(recursive=True)
                    time.sleep(0.02)
                self.assertTrue(children, "El proceso de prueba no creó su hijo")
                child_pids = [child.pid for child in children]
                worker.cancel()
                parent.wait(timeout=5)
                psutil.wait_procs(children, timeout=5)
                self.assertTrue(
                    all(
                        not psutil.pid_exists(pid) or psutil.Process(pid).status() == psutil.STATUS_ZOMBIE
                        for pid in child_pids
                    )
                )
            finally:
                if parent.poll() is None:
                    parent.kill()
                    parent.wait()

    @unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg no disponible")
    def test_cancel_kills_ffmpeg_conversion(self):
        with tempfile.TemporaryDirectory() as temp:
            settings = DownloadSettings([], Path(temp), "mp3", 2, "%(title)s.%(ext)s", False, False)
            worker = DownloadWorker(settings)
            code = (
                "import subprocess,sys,time; "
                "subprocess.Popen([sys.argv[1], '-loglevel', 'error', '-re', "
                "'-f', 'lavfi', '-i', 'sine=duration=60', '-f', 'null', '-'], "
                "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); "
                "time.sleep(60)"
            )
            parent = subprocess.Popen([sys.executable, "-c", code, shutil.which("ffmpeg")])
            worker._process = parent
            try:
                deadline = time.monotonic() + 5
                children = []
                while not children and time.monotonic() < deadline:
                    children = psutil.Process(parent.pid).children(recursive=True)
                    time.sleep(0.02)
                self.assertTrue(children)
                worker.cancel()
                parent.wait(timeout=5)
                _, alive = psutil.wait_procs(children, timeout=5)
                self.assertFalse(alive)
            finally:
                if parent.poll() is None:
                    parent.kill()
                    parent.wait()


if __name__ == "__main__":
    unittest.main()
