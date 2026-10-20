"""Tests of the escaping in render.py. Run: python3 -m unittest discover -s .github/frontend-pre-check"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import render  # noqa: E402


class AllowedLinkTest(unittest.TestCase):
    def test_legit_links_pass(self):
        for url in [
            "https://github.com/gi-org-pl/repo/blob/main/x.md#L10",
            "https://github.com/gi-org-pl/mypolitics-app/actions/runs/123",
            "https://www.figma.com/design/KEY/name?node-id=1-2",
            "https://figma.com/design/KEY/name?node-id=1-2",
            "https://gi.org.pl/path",
        ]:
            self.assertTrue(render.allowed_link(url), url)

    def test_traversal_is_rejected(self):
        for url in [
            "https://github.com/gi-org-pl/../other-org/repo",
            "https://github.com/gi-org-pl/%2e%2e/other-org/repo",
            "https://github.com/gi-org-pl/.%2e/other-org/repo",
            "https://github.com/gi-org-pl/%2e./other-org/repo",
            "https://github.com/gi-org-pl/..%2fother-org/repo",
            "https://github.com/gi-org-pl/%252e%252e/other-org/repo",
            "https://github.com/gi-org-pl/%2E%2E/other-org/repo",
            "https://github.com/gi-org-pl/repo/./x",
            "https://gi.org.pl/..",
            "https://www.figma.com/design/../../evil",
        ]:
            self.assertFalse(render.allowed_link(url), url)

    def test_other_tricks_are_rejected(self):
        for url in [
            "https://github.com/gi-org-pl/x%5c..%5cevil",  # backslash, encoded
            "https://github.com/gi-org-pl//evil",
            "https://github.com/evil-org/repo",
            "https://github.com.evil.example/gi-org-pl/",
            "https://evil.example/https://github.com/gi-org-pl/",
            "http://github.com/gi-org-pl/repo",
            "https://GITHUB.com/gi-org-pl/../evil",
            "https://figma.com.evil.example/x",
        ]:
            self.assertFalse(render.allowed_link(url), url)


class EscapeTest(unittest.TestCase):
    def test_traversal_link_is_not_rendered_as_link(self):
        out = render.one_line("see [docs](https://github.com/gi-org-pl/../evil/repo)", 400)
        self.assertNotIn("](https://github.com/gi-org-pl/../evil", out)
        self.assertIn("`https://github.com/gi-org-pl/../evil/repo`", out)

    def test_mentions_html_images(self):
        out = render.one_line("@team <b>x</b> ![i](https://evil.example/p.png)", 400)
        self.assertNotIn("@team", out)
        self.assertNotIn("<b>", out)
        self.assertNotIn("![", out)

    def test_suggestion_fence_becomes_plain_code(self):
        out = render.multi_line("x\n```suggestion\ncode\n```", 3000)
        self.assertNotIn("suggestion", out)
        self.assertIn("```\ncode\n```", out)

    def test_tokens_are_redacted(self):
        out = render.one_line("sk-ant-oat01-" + "A" * 40, 400)
        self.assertNotIn("sk-ant-oat01", out)


if __name__ == "__main__":
    unittest.main()
