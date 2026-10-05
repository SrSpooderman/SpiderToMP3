import hashlib
import io
import json
import os
import subprocess
import tarfile
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from config import APP_VERSION
from services.updater import (
    LINUX_HELPER, LINUX_PACKAGE_FILES, UpdateError,
    expected_checksum, is_newer_version, prepare_linux_package,
    release_from_json, verify_download,
)


class UpdaterTests(unittest.TestCase):
    def _release(self, system="Linux", version="0.2.1", content=b"new"):
        suffix = "windows-x86_64.exe" if system == "Windows" else "linux-x86_64.tar.gz"
        name = f"SpiderToMP3-v{version}-{suffix}"
        base = f"https://github.com/SrSpooderman/SpiderToMP3/releases/download/v{version}/"
        payload = {
            "tag_name": f"v{version}", "draft": False, "prerelease": False,
            "body": "Cambios de prueba", "assets": [
                {"name": name, "size": len(content), "browser_download_url": base + name},
                {"name": "SHA256SUMS", "size": 100, "browser_download_url": base + "SHA256SUMS"},
            ],
        }
        return payload, name

    def test_compara_versiones_estables_y_no_baja_de_version(self):
        self.assertTrue(is_newer_version("0.2.1", "0.2.0"))
        self.assertTrue(is_newer_version("0.2.0", "0.2.0-rc.1"))
        self.assertFalse(is_newer_version("0.1.9", "0.2.0"))
        self.assertFalse(is_newer_version("0.2.0", "0.2.0"))

    def test_selecciona_el_asset_correcto_y_rechaza_release_insegura(self):
        for system in ("Linux", "Windows"):
            payload, name = self._release(system)
            with patch("services.updater.platform.machine", return_value="x86_64"):
                release = release_from_json(json.dumps(payload).encode(), system, "0.2.0")
            self.assertEqual(release.asset_name, name)
            self.assertEqual(release.version, "0.2.1")
            payload["assets"][0]["browser_download_url"] = "https://evil.example/file"
            with self.assertRaises(UpdateError):
                release_from_json(json.dumps(payload).encode(), system, "0.2.0")
        payload, _ = self._release(version="0.2.1-rc.1")
        with self.assertRaises(UpdateError):
            release_from_json(json.dumps(payload).encode(), "Linux", "0.2.0")

    def test_verifica_hash_y_tamano(self):
        content = b"ejecutable"
        payload, name = self._release(content=content)
        with patch("services.updater.platform.machine", return_value="x86_64"):
            release = release_from_json(json.dumps(payload).encode(), "Linux", "0.2.0")
        digest = hashlib.sha256(content).hexdigest()
        checksum = expected_checksum(f"{digest}  {name}\n".encode(), name)
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / name
            file.write_bytes(content)
            verify_download(file, release, checksum)
            file.write_bytes(b"ejecutable corrupto")
            with self.assertRaises(UpdateError):
                verify_download(file, release, checksum)
            file.write_bytes(b"abcdefghij")
            with self.assertRaisesRegex(UpdateError, "SHA-256"):
                verify_download(file, release, checksum)

    def test_extrae_paquete_valido_y_rechaza_rutas_extra(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / "release.tar.gz"
            for names in (LINUX_PACKAGE_FILES, LINUX_PACKAGE_FILES | {"../escape"}):
                with tarfile.open(archive, "w:gz") as output:
                    for name in names:
                        data = b"file"
                        info = tarfile.TarInfo(name)
                        info.size = len(data)
                        output.addfile(info, io.BytesIO(data))
                if "../escape" in names:
                    with self.assertRaises(UpdateError):
                        prepare_linux_package(archive, root)
                    self.assertFalse((root.parent / "escape").exists())
                else:
                    prepare_linux_package(archive, root)
                    self.assertTrue((root / "SpiderToMP3-linux-x86_64").is_file())

    @unittest.skipUnless(os.name == "posix", "Requiere Linux/POSIX")
    def test_auxiliar_linux_reemplaza_y_conserva_copia(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            stage = root / "stage"
            stage.mkdir()
            target = root / "SpiderToMP3-linux-x86_64"
            target.write_text("old")
            (stage / target.name).write_text("#!/bin/sh\nexit 0\n")
            helper = root / "apply-update.sh"
            helper.write_text(LINUX_HELPER)
            subprocess.run(["/bin/sh", str(helper), "999999999", str(stage), str(target), "no"],
                           check=True, capture_output=True, timeout=10)
            self.assertEqual(target.read_text(), "#!/bin/sh\nexit 0\n")
            self.assertEqual((root / (target.name + ".previous")).read_text(), "old")

    @unittest.skipUnless(os.name == "posix", "Requiere Linux/POSIX")
    def test_auxiliar_linux_restaura_si_nueva_version_no_arranca(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            stage = root / "stage"
            stage.mkdir()
            target = root / "SpiderToMP3-linux-x86_64"
            target.write_text("old")
            (stage / target.name).write_text("#!/bin/sh\nexit 1\n")
            helper = root / "apply-update.sh"
            helper.write_text(LINUX_HELPER)
            result = subprocess.run(
                ["/bin/sh", str(helper), "999999999", str(stage), str(target), "no"],
                capture_output=True, timeout=10,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(target.read_text(), "old")
            self.assertIn("restauró", (root / (target.name + ".update-error")).read_text())

    @unittest.skipUnless(os.name == "posix", "Requiere Linux/POSIX")
    def test_auxiliar_linux_regenera_icono_del_menu(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            stage = root / "stage"
            stage.mkdir()
            target = root / ".local/bin/SpiderToMP3-linux-x86_64"
            target.parent.mkdir(parents=True)
            target.write_text("old")
            (stage / target.name).write_text(
                '#!/bin/sh\nif [ "$1" = --write-menu-icon ]; then printf png > "$2"; fi\n'
            )
            project = Path(__file__).resolve().parents[1]
            (stage / "spidertomp3.svg").write_bytes(
                (project / "assets/spidertomp3-icon.svg").read_bytes()
            )
            (stage / "spidertomp3.desktop").write_bytes(
                (project / "packaging/spidertomp3.desktop").read_bytes()
            )
            helper = root / "apply-update.sh"
            helper.write_text(LINUX_HELPER)
            subprocess.run(["/bin/sh", str(helper), "999999999", str(stage), str(target), "yes"],
                           check=True, capture_output=True, timeout=10,
                           env={**os.environ, "HOME": str(root)})
            icon = root / ".local/share/icons/hicolor/256x256/apps/spidertomp3.png"
            launcher = root / ".local/share/applications/spidertomp3.desktop"
            self.assertEqual(icon.read_bytes(), b"png")
            self.assertIn(f"Icon={icon}", launcher.read_text())
            self.assertIn(f'Exec="{target}"', launcher.read_text())

    def test_consulta_asincrona_informa_si_esta_actualizado(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from controllers.update_controller import UpdateController
        from qt import QApplication, QSettings
        from views.main_window import MainWindow

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                body = json.dumps({"tag_name": f"v{APP_VERSION}", "draft": False, "prerelease": False}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            app = QApplication.instance() or QApplication([])
            with tempfile.TemporaryDirectory() as temp:
                settings = QSettings(str(Path(temp) / "settings.ini"), QSettings.IniFormat)
                with patch("views.main_window.QSettings", return_value=settings), \
                        patch("controllers.update_controller.QSettings", return_value=settings), \
                        patch("controllers.update_controller.LATEST_RELEASE_URL",
                              f"http://127.0.0.1:{server.server_port}/latest"), \
                        patch("controllers.update_controller.QMessageBox.information") as info:
                    window = MainWindow()
                    controller = UpdateController(window, SimpleNamespace(is_running=False))
                    window.check_updates_requested.emit()
                    deadline = time.monotonic() + 5
                    while controller.reply is not None and time.monotonic() < deadline:
                        app.processEvents()
                        time.sleep(0.01)
                    self.assertIsNone(controller.reply)
                    info.assert_called_once()
                    window.close()
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
