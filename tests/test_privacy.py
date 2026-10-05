import unittest
from pathlib import Path

from services.privacy import redact_text


class PrivacyTests(unittest.TestCase):
    def test_hides_url_credentials_query_tokens_and_home_path(self):
        value = f"falló https://name:password@example.test/audio?token=abc&key=def cookie: xyz {Path.home()}/Music"
        safe = redact_text(value)
        for secret in ("password", "abc", "def", "xyz", str(Path.home())):
            self.assertNotIn(secret, safe)
        self.assertIn("example.test/audio?[oculto]", safe)


if __name__ == "__main__":
    unittest.main()
