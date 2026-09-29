import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


@unittest.skipUnless(os.name == "posix" and shutil.which("install"), "Requiere utilidades POSIX")
class BazziteInstallerTests(unittest.TestCase):
    def test_installs_launcher_icon_and_binary_in_user_home(self):
        project = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle = root / "bundle"
            bundle.mkdir()
            (bundle / "SpiderToMP3-linux-x86_64").write_bytes(b"binary")
            for name, source in (
                ("spidertomp3.svg", project / "assets" / "spidertomp3.svg"),
                ("spidertomp3.desktop", project / "packaging" / "spidertomp3.desktop"),
            ):
                shutil.copyfile(source, bundle / name)
            script = bundle / "install-bazzite.sh"
            shutil.copyfile(project / "packaging" / "install-bazzite.sh", script)
            home = root / "home"
            home.mkdir()
            subprocess.run(["sh", str(script)], check=True, cwd=bundle,
                           env={**os.environ, "SPIDER_INSTALL_HOME": str(home)}, capture_output=True)

            binary = home / ".local/bin/SpiderToMP3-linux-x86_64"
            launcher = home / ".local/share/applications/spidertomp3.desktop"
            icon = home / ".local/share/icons/hicolor/scalable/apps/spidertomp3.svg"
            self.assertTrue(binary.is_file())
            self.assertTrue(binary.stat().st_mode & 0o111)
            self.assertTrue(icon.is_file())
            self.assertIn(f"Exec={binary}", launcher.read_text())


if __name__ == "__main__":
    unittest.main()
