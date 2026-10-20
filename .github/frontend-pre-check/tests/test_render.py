"""Tests of review/render.py: presentation only - every finding with its body,
plain-text escaping, allowlisted links, and that display limits do not touch
the outcome."""

import unittest

import fakes  # noqa: F401  (import paths)
import render
from test_evaluate import finding, outcome, result, scope


def rendered(res, sc=None):
    sc = sc or scope()
    return render.render(res, sc, outcome(res, sc), "full")


class PublicationTest(unittest.TestCase):
    def test_every_body_is_in_the_main_comment(self):
        findings = [finding("blocking", title="no line", body="evidence one"),
                    finding("blocking", title="outside hunk", body="evidence two", inline=True, line=99),
                    finding(title="inline ok", body="evidence three", inline=True, line=3)]
        comment, inline = rendered(result(findings))
        for text in ["evidence one", "evidence two", "evidence three"]:
            self.assertIn(text, comment)
        self.assertEqual(len(inline), 1)

    def test_more_than_fifteen_inline_findings_keep_their_bodies(self):
        findings = [finding(title="t{}".format(i), body="body{}".format(i), inline=True, line=2) for i in range(20)]
        comment, inline = rendered(result(findings))
        self.assertEqual(len(inline), 15)
        for i in range(20):
            self.assertIn("body{}".format(i), comment)

    def test_display_cap_shows_blockers_and_keeps_the_outcome(self):
        findings = [finding(title="a{}".format(i)) for i in range(30)] + [finding("blocking", title="the blocker")]
        comment, _ = rendered(result(findings))
        self.assertIn("the blocker", comment)
        self.assertIn("changes needed - 1 blocking", comment)
        self.assertIn("31 findings were returned", comment)

    def test_identical_titles_at_two_lines_stay_distinct(self):
        findings = [finding(title="same", inline=True, line=2), finding(title="same", inline=True, line=4)]
        _, inline = rendered(result(findings))
        self.assertEqual(len({i["fingerprint"] for i in inline}), 2)

    def test_advisory_is_not_called_no_findings(self):
        comment, _ = rendered(result([finding()]))
        self.assertIn("1 advisory finding", comment)
        self.assertNotIn("no findings", comment)


class AllowedLinkTest(unittest.TestCase):
    def test_legit_links_pass(self):
        for url in ["https://github.com/gi-org-pl/repo/blob/main/x.md#L10",
                    "https://github.com/gi-org-pl/mypolitics-app/actions/runs/123",
                    "https://www.figma.com/design/KEY/name?node-id=1-2",
                    "https://figma.com/design/KEY/name?node-id=1-2",
                    "https://gi.org.pl/path"]:
            self.assertTrue(render.allowed_link(url), url)

    def test_traversal_and_tricks_are_rejected(self):
        for url in ["https://github.com/gi-org-pl/../other-org/repo",
                    "https://github.com/gi-org-pl/%2e%2e/other-org/repo",
                    "https://github.com/gi-org-pl/.%2e/other-org/repo",
                    "https://github.com/gi-org-pl/%2e./other-org/repo",
                    "https://github.com/gi-org-pl/..%2fother-org/repo",
                    "https://github.com/gi-org-pl/%252e%252e/other-org/repo",
                    "https://github.com/gi-org-pl/%2E%2E/other-org/repo",
                    "https://github.com/gi-org-pl/x%5c..%5cevil",
                    "https://github.com/gi-org-pl//evil",
                    "https://github.com/evil-org/repo",
                    "https://github.com.evil.example/gi-org-pl/",
                    "http://github.com/gi-org-pl/repo",
                    "https://figma.com.evil.example/x"]:
            self.assertFalse(render.allowed_link(url), url)


class EscapeTest(unittest.TestCase):
    def assert_no_link(self, text):
        out = render.multi_line(text, 3000)
        self.assertNotRegex(out, r"(?<!\\)\[[^\]]*(?<!\\)\]\(", out)
        self.assertNotRegex(out, r"(?m)^\s*(?<!\\)\[[^\]]+(?<!\\)\]:", out)
        self.assertNotRegex(out, r"(?i)https?://", out)
        self.assertNotRegex(out, r"(?i)\bwww\.", out)
        self.assertNotIn("<", out)

    def test_no_model_link_survives(self):
        for text in ["[x](https://evil.example)", "[Review][evidence]\n\n[evidence]: //attacker.example/collect",
                     "[shortcut]\n\n[shortcut]: https://evil.example", "<https://evil.example>",
                     "https://evil.example/raw", "www.evil.example", "see //attacker.example/x",
                     "[x](https://github.com/gi-org-pl/../evil)", "%68ttps://evil.example"]:
            self.assert_no_link(text)

    def test_mentions_html_images(self):
        out = render.one_line("@team <b>x</b> ![i](https://evil.example/p.png) a@b.example", 400)
        for bad in ["@team", "<b>", "![", "a@b"]:
            self.assertNotIn(bad, out)

    def test_no_markdown_structure_from_the_model(self):
        out = render.multi_line("# heading\n- item\n> quote\n| a | b |\n**Result:** passed", 3000)
        for line in out.split("\n"):
            self.assertFalse(line.startswith(("#", "- ", ">", "|", "**")), line)

    def test_suggestion_fence_becomes_plain_code(self):
        out = render.multi_line("x\n```suggestion\ncode\n```", 3000)
        self.assertNotIn("suggestion", out)
        self.assertIn("```\ncode\n```", out)

    def test_code_stays_literal(self):
        self.assertIn("`a < b`", render.one_line("see `a < b` here", 400))

    def test_tokens_are_redacted(self):
        self.assertNotIn("sk-ant-oat01", render.one_line("sk-ant-oat01-" + "A" * 40, 400))


if __name__ == "__main__":
    unittest.main()
