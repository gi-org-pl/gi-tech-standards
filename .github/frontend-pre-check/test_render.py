"""Tests of render.py: the verdict, the escaping and the publication rules.
Run: python3 -m unittest discover -s .github/frontend-pre-check"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import render  # noqa: E402

EMPTY_DECISIONS = {k: [] for k, _ in render.CATEGORIES}


def result(findings=(), **extra):
    data = {"result": "passed", "summary": "s", "decisions": dict(EMPTY_DECISIONS), "findings": list(findings),
            "checked": [], "not_checked": [], "qa": []}
    data.update(extra)
    return data


def finding(severity="non-blocking", path="src/a.ts", title="t", body="b", inline=False, line=None):
    f = {"severity": severity, "path": path, "title": title, "body": body, "inline": inline}
    if line is not None:
        f["line"] = line
    return f


def scope(**extra):
    data = {"head": "a" * 40, "base": "b" * 40, "standards": "c" * 40, "reviewed": ["src/a.ts"], "file_count": 1,
            "diff_lines": 10, "max_diff_lines": 3000, "truncated": False, "not_reviewed": [], "excluded": [],
            "excluded_lines": 0, "safe_assets": [], "unreviewable": [], "human_paths": [], "workflow_changes": [],
            "renamed": [], "issues": [], "figma": [], "docs": [], "repo_docs": [], "cut_sources": [], "notes": [],
            "hunks": {"src/a.ts": [{"LEFT": [1, 5], "RIGHT": [1, 9]}]}}
    data.update(extra)
    return data


def render_with(res, sc=None, coverage="full"):
    with tempfile.TemporaryDirectory() as tmp:
        rp, sp = os.path.join(tmp, "r.json"), os.path.join(tmp, "s.json")
        with open(rp, "w", encoding="utf-8") as fh:
            json.dump(res, fh)
        with open(sp, "w", encoding="utf-8") as fh:
            json.dump(sc or scope(), fh)
        os.environ["COVERAGE"] = coverage
        argv = sys.argv
        sys.argv = ["render.py", rp, sp, tmp]
        try:
            render.main()
        finally:
            sys.argv = argv
        with open(os.path.join(tmp, "outcome"), encoding="utf-8") as fh:
            outcome = fh.read()
        with open(os.path.join(tmp, "comment.md"), encoding="utf-8") as fh:
            comment = fh.read()
        with open(os.path.join(tmp, "inline.json"), encoding="utf-8") as fh:
            inline = json.load(fh)
    return outcome, comment, inline


class VerdictTest(unittest.TestCase):
    def test_clean(self):
        self.assertEqual(render_with(result())[0], "clean")

    def test_one_advisory_finding_is_not_clean(self):
        outcome, comment, _ = render_with(result([finding()]))
        self.assertEqual(outcome, "advisory")
        self.assertIn("1 advisory finding", comment)
        self.assertNotIn("no findings", comment)

    def test_blocker_after_thirty_advisory_findings(self):
        findings = [finding(title="a{}".format(i)) for i in range(30)] + [finding("blocking", title="the blocker")]
        outcome, comment, _ = render_with(result(findings))
        self.assertEqual(outcome, "changes")
        self.assertIn("the blocker", comment)

    def test_more_findings_than_allowed_needs_a_person(self):
        outcome, _, _ = render_with(result([finding(title=str(i)) for i in range(31)]))
        self.assertEqual(outcome, "human")

    def test_reviewer_result_is_ignored(self):
        self.assertEqual(render_with(result([finding("blocking")], result="passed"))[0], "changes")
        self.assertEqual(render_with(result([], result="changes"))[0], "clean")

    def test_nothing_reviewed_needs_a_person(self):
        self.assertEqual(render_with(result(), scope(reviewed=[], file_count=3, hunks={}))[0], "human")

    def test_scope_reasons_need_a_person(self):
        for extra in [{"truncated": True}, {"unreviewable": [{"path": "bin/x", "reason": "binary"}]},
                      {"workflow_changes": [".github/workflows/x.yml"],
                       "human_paths": [{"path": ".github/workflows/x.yml", "reason": "CI workflow"}]},
                      {"human_paths": [{"path": "package.json", "reason": "dependency manifest"}]},
                      {"cut_sources": ["issue x"]}]:
            self.assertEqual(render_with(result(), scope(**extra))[0], "human", extra)

    def test_incomplete_reading_needs_a_person(self):
        self.assertEqual(render_with(result(), coverage="partial")[0], "human")
        self.assertEqual(render_with(result(), coverage="none")[0], "human")

    def test_invalid_results(self):
        for bad in [{"result": "passed\n::stop-commands::x"}, result(findings=[{"severity": "x"}]),
                    result(findings=[finding(line=True)]), "nope"]:
            self.assertEqual(render_with(bad)[0], "invalid")


class PublicationTest(unittest.TestCase):
    def test_every_body_is_in_the_main_comment(self):
        findings = [finding("blocking", title="no line", body="evidence one"),
                    finding("blocking", title="outside hunk", body="evidence two", inline=True, line=99),
                    finding("non-blocking", title="inline ok", body="evidence three", inline=True, line=3)]
        outcome, comment, inline = render_with(result(findings))
        for text in ["evidence one", "evidence two", "evidence three"]:
            self.assertIn(text, comment)
        self.assertEqual(len(inline), 1)

    def test_more_than_fifteen_inline_findings_keep_their_bodies(self):
        findings = [finding(title="t{}".format(i), body="body{}".format(i), inline=True, line=2) for i in range(20)]
        _, comment, inline = render_with(result(findings))
        self.assertEqual(len(inline), 15)
        for i in range(20):
            self.assertIn("body{}".format(i), comment)

    def test_identical_titles_at_two_lines_stay_distinct(self):
        findings = [finding(title="same", inline=True, line=2), finding(title="same", inline=True, line=4)]
        _, _, inline = render_with(result(findings))
        self.assertEqual(len({i["fingerprint"] for i in inline}), 2)

    def test_credential_like_output_is_withheld(self):
        for leak in ["password = hunter2hunter2x", "postgres://user:pa55word@db.example/x",
                     "Authorization: Bearer abcdefghijkl123"]:
            outcome, comment, inline = render_with(result([finding(body=leak)]))
            self.assertEqual(outcome, "quarantine", leak)
            self.assertNotIn(leak, comment)
            self.assertEqual(inline, [])

    def test_code_talk_is_not_withheld(self):
        outcome, _, _ = render_with(result([finding(body="`const token = getToken()` and process.env.SECRET")]))
        self.assertEqual(outcome, "advisory")


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
        self.assertNotRegex(out, r"(?<!\\)\[[^\]]*(?<!\\)\]\(", out)   # inline link
        self.assertNotRegex(out, r"(?m)^\s*(?<!\\)\[[^\]]+(?<!\\)\]:", out)  # reference definition
        self.assertNotRegex(out, r"(?i)https?://", out)                    # autolink
        self.assertNotRegex(out, r"(?i)\bwww\.", out)
        self.assertNotIn("<", out)
        return out

    def test_no_model_link_survives(self):
        for text in ["[x](https://evil.example)", "[Review][evidence]\n\n[evidence]: //attacker.example/collect",
                     "[shortcut]\n\n[shortcut]: https://evil.example", "<https://evil.example>",
                     "https://evil.example/raw", "www.evil.example", "see //attacker.example/x",
                     "[x](https://github.com/gi-org-pl/../evil)", "%68ttps://evil.example"]:
            self.assert_no_link(text)

    def test_mentions_html_images(self):
        out = render.one_line("@team <b>x</b> ![i](https://evil.example/p.png) a@b.example", 400)
        self.assertNotIn("@team", out)
        self.assertNotIn("<b>", out)
        self.assertNotIn("![", out)
        self.assertNotIn("a@b", out)

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
