import os
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from main import repair_installed_menu_icon


@unittest.skipUnless(os.name == "posix" and shutil.which("install"), "Requiere utilidades POSIX")
class BazziteInstallerTests(unittest.TestCase):
    def test_repairs_launcher_written_by_previous_updater(self):
        project = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            launcher = home / ".local/share/applications/spidertomp3.desktop"
            launcher.parent.mkdir(parents=True)
            shutil.copyfile(project / "packaging/spidertomp3.desktop", launcher)
            binary = home / ".local/bin/SpiderToMP3-linux-x86_64"
            self.assertTrue(repair_installed_menu_icon(home, binary))
            icon = home / ".local/share/icons/hicolor/256x256/apps/spidertomp3.png"
            self.assertEqual(icon.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
            self.assertIn(f"Icon={icon}", launcher.read_text())
            self.assertFalse(repair_installed_menu_icon(home, binary))

    def test_installs_launcher_icon_and_binary_in_user_home(self):
        project = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle = root / "bundle"
            bundle.mkdir()
            binary = bundle / "SpiderToMP3-linux-x86_64"
            binary.write_text(
                f"#!/bin/sh\nexec {shlex.quote(sys.executable)} "
                f"{shlex.quote(str(project / 'main.py'))} \"$@\"\n"
            )
            for name, source in (
                ("spidertomp3.svg", project / "assets" / "spidertomp3-icon.svg"),
                ("spidertomp3.desktop", project / "packaging" / "spidertomp3.desktop"),
            ):
                shutil.copyfile(source, bundle / name)
            script = bundle / "install-bazzite.sh"
            shutil.copyfile(project / "packaging" / "install-bazzite.sh", script)
            home = root / "user home"
            home.mkdir()
            subprocess.run(["sh", str(script)], check=True, cwd=bundle,
                           env={**os.environ, "SPIDER_INSTALL_HOME": str(home)}, capture_output=True)

            binary = home / ".local/bin/SpiderToMP3-linux-x86_64"
            launcher = home / ".local/share/applications/spidertomp3.desktop"
            icon = home / ".local/share/icons/hicolor/256x256/apps/spidertomp3.png"
            self.assertTrue(binary.is_file())
            self.assertTrue(binary.stat().st_mode & 0o111)
            self.assertTrue(icon.is_file())
            self.assertEqual(icon.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(struct.unpack(">II", icon.read_bytes()[16:24]), (256, 256))
            self.assertIn(f'Exec="{home / ".local/bin/SpiderToMP3-linux-x86_64"}"',
                          launcher.read_text())
            self.assertIn(f"Icon={icon}", launcher.read_text())
            if shutil.which("desktop-file-validate"):
                subprocess.run(["desktop-file-validate", str(launcher)], check=True,
                               capture_output=True)


if __name__ == "__main__":
    unittest.main()
