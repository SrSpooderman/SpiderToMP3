import unittest

from services.url_parser import parse_urls


class ParseUrlsTests(unittest.TestCase):
    def test_splits_lines_and_commas_preserving_order(self):
        self.assertEqual(
            parse_urls(" https://a.test/1, https://b.test/2\nhttps://c.test/3 "),
            ["https://a.test/1", "https://b.test/2", "https://c.test/3"],
        )

    def test_ignores_empty_lines_comments_and_duplicates(self):
        self.assertEqual(
            parse_urls("\n# comentario\nhttps://a.test/1\n https://a.test/1 \n"),
            ["https://a.test/1"],
        )

    def test_keeps_commas_inside_a_url(self):
        self.assertEqual(
            parse_urls("https://a.test/audio?ids=1,2,3, https://b.test/song"),
            ["https://a.test/audio?ids=1,2,3", "https://b.test/song"],
        )


if __name__ == "__main__":
    unittest.main()
