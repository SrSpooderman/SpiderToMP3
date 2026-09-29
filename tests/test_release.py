import ast
import os
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

from config import APP_VERSION
from scripts.release_assets import asset_names, prepare, verify
from scripts.versioning import check_tag, check_version, release_notes, windows_version_resource


class VersioningTests(unittest.TestCase):
    def test_tag_and_changelog_must_match_the_application(self):
        check_tag(f"v{APP_VERSION}")
        with self.assertRaises(ValueError):
            check_tag("v9.9.9")
        with self.assertRaises(ValueError):
            check_version("01.0.0")
        with self.assertRaises(ValueError):
            check_version("0.1.0-rc.01")
        check_version("0.1.0-rc.1")
        notes = release_notes(Path("CHANGELOG.md").read_text(encoding="utf-8"))
        self.assertIn("Primera versión", notes)

    def test_windows_version_resource_uses_same_version(self):
        resource = windows_version_resource()
        ast.parse(resource, mode="eval")
        self.assertIn(f"ProductVersion', '{APP_VERSION}'", resource)
        self.assertIn("filevers=(0, 1, 0, 0)", resource)


class ReleaseAssetsTests(unittest.TestCase):
    def test_separate_assets_and_checksums(self):
        with tempfile.TemporaryDirectory() as temp:
            inputs = Path(temp) / "inputs"
            output = Path(temp) / "release"
            inputs.mkdir()
            (inputs / "SpiderToMP3.exe").write_bytes(b"windows")
            (inputs / "SpiderToMP3-linux-x86_64").write_bytes(b"linux")
            prepare(inputs, output)
            verify(output)
            windows_name, linux_name = asset_names()
            self.assertEqual({item.name for item in output.iterdir()},
                             {windows_name, linux_name, "SHA256SUMS"})
            (output / windows_name).write_bytes(b"corrupto")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                verify(output)

    @unittest.skipUnless(os.name == "posix" and shutil.which("install"), "Requiere POSIX")
    def test_linux_release_archive_installs_in_user_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inputs = root / "inputs"
            inputs.mkdir()
            (inputs / "SpiderToMP3.exe").write_bytes(b"windows")
            (inputs / "SpiderToMP3-linux-x86_64").write_bytes(b"linux")
            output = root / "release"
            prepare(inputs, output)
            package = root / "package"
            package.mkdir()
            with tarfile.open(output / asset_names()[1], "r:gz") as archive:
                for member in archive:
                    target = package / member.name
                    target.write_bytes(archive.extractfile(member).read())
                    target.chmod(member.mode)
            install_home = root / "user"
            subprocess.run(["sh", str(package / "install-bazzite.sh")], check=True,
                           env={**os.environ, "SPIDER_INSTALL_HOME": str(install_home)},
                           capture_output=True)
            self.assertEqual((install_home / ".local/bin/SpiderToMP3-linux-x86_64").read_bytes(),
                             b"linux")


if __name__ == "__main__":
    unittest.main()
