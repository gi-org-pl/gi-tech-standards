"""Tests of review/evaluate.py: the authoritative outcome, and the single set
of outcome states in contracts.py."""

import json
import os
import tempfile
import unittest

import fakes
import contracts
import evaluate

RESULT_SCHEMA = contracts.load(os.path.join(fakes.ROOT, "review", "schema.json"))
SCOPE_SCHEMA = contracts.load(os.path.join(fakes.ROOT, "context", "scope.schema.json"))
CATEGORIES = ["data_structures", "state", "api_contracts", "ux_behaviours", "new_dependencies", "architecture"]


def result(findings=(), **extra):
    data = {"result": "passed", "summary": "s", "decisions": {k: [] for k in CATEGORIES}, "findings": list(findings),
            "checked": [], "not_checked": [], "qa": []}
    data.update(extra)
    return data


def finding(severity="non-blocking", title="t", body="b", **extra):
    data = {"severity": severity, "path": "src/a.ts", "title": title, "body": body, "inline": False}
    data.update(extra)
    return data


def scope(**extra):
    data = {"head": "a" * 40, "base": "b" * 40, "standards": "c" * 40, "max_diff_lines": 3000, "diff_lines": 10,
            "file_count": 1, "unlisted": 0, "truncated": False, "reviewed": ["src/a.ts"], "not_reviewed": [],
            "excluded": [], "excluded_lines": 0, "safe_assets": [], "unreviewable": [], "human_paths": [],
            "workflow_changes": [], "renamed": [], "hunks": {"src/a.ts": [{"LEFT": [1, 5], "RIGHT": [1, 9]}]},
            "issues": [], "figma": [], "docs": [], "repo_docs": [], "cut_sources": [], "notes": []}
    data.update(extra)
    return data


def outcome(res, sc=None, coverage="full"):
    return evaluate.evaluate(res, sc or scope(), coverage, RESULT_SCHEMA, SCOPE_SCHEMA)


class OutcomeStatesTest(unittest.TestCase):
    def test_single_set_of_states(self):
        self.assertEqual(set(contracts.OUTCOMES), {"clean", "advisory", "queued", "changes", "human", "invalid", "skipped"})
        passing = {name for name, (passes, _) in contracts.OUTCOMES.items() if passes}
        self.assertEqual(passing, {"clean", "advisory", "queued"})

    def test_exit_codes(self):
        for name, (passes, _) in contracts.OUTCOMES.items():
            self.assertEqual(contracts.main(["contracts.py", "passes", name]), 0 if passes else 1, name)
        self.assertEqual(contracts.main(["contracts.py", "passes", "unknown"]), 1)


class VerdictTest(unittest.TestCase):
    def test_clean_and_advisory(self):
        self.assertEqual(outcome(result())["outcome"], "clean")
        evaluation = outcome(result([finding()]))
        self.assertEqual((evaluation["outcome"], evaluation["advisory"]), ("advisory", 1))

    def test_blocker_after_thirty_advisory_findings(self):
        findings = [finding(title=str(i)) for i in range(30)] + [finding("blocking", title="the blocker")]
        evaluation = outcome(result(findings))
        self.assertEqual((evaluation["outcome"], evaluation["blocking"], evaluation["total"]), ("changes", 1, 31))

    def test_more_findings_than_allowed_needs_a_person(self):
        self.assertEqual(outcome(result([finding(title=str(i)) for i in range(31)]))["outcome"], "human")

    def test_reviewer_result_field_is_ignored(self):
        self.assertEqual(outcome(result([finding("blocking")], result="passed"))["outcome"], "changes")
        self.assertEqual(outcome(result([], result="changes"))["outcome"], "clean")

    def test_coverage_rules(self):
        cases = [
            {"reviewed": [], "file_count": 3, "hunks": {}},
            {"truncated": True, "not_reviewed": ["src/b.ts"]},
            {"unreviewable": [{"path": "bin/x", "reason": "binary"}]},
            {"workflow_changes": [".github/workflows/x.yml"], "human_paths": [{"path": ".github/workflows/x.yml", "reason": "CI workflow"}]},
            {"human_paths": [{"path": "package.json", "reason": "dependency manifest"}]},
            {"cut_sources": ["issue x"]},
        ]
        for extra in cases:
            self.assertEqual(outcome(result(), scope(**extra))["outcome"], "human", extra)

    def test_excluded_only_pull_request_needs_a_person(self):
        sc = scope(reviewed=[], file_count=2, excluded=["src/a.test.ts", "src/b.test.ts"], excluded_lines=40, hunks={})
        self.assertEqual(outcome(result(), sc)["outcome"], "human")

    def test_incomplete_reading_needs_a_person(self):
        self.assertEqual(outcome(result(), coverage="partial")["outcome"], "human")
        self.assertEqual(outcome(result(), coverage="none")["outcome"], "human")
        self.assertEqual(outcome(result(), scope(reviewed=[], file_count=0, hunks={}), coverage="none")["outcome"], "clean")

    def test_blocking_wins_over_human(self):
        evaluation = outcome(result([finding("blocking")]), scope(truncated=True))
        self.assertEqual(evaluation["outcome"], "changes")
        self.assertTrue(evaluation["reasons"])

    def test_invalid_results_and_scopes(self):
        for bad in [None, "nope", {"result": "passed\n::stop-commands::x"}, result(findings=[{"severity": "x"}]),
                    result(findings=[finding(line=True)]), result(findings=[finding(line=0)]),
                    result(extra_field=1)]:
            self.assertEqual(outcome(bad)["outcome"], "invalid", bad)
        broken = scope()
        del broken["hunks"]
        self.assertEqual(outcome(result(), broken)["outcome"], "invalid")

    def test_credential_like_text_is_withheld(self):
        for leak in ["password = hunter2hunter2x", "postgres://user:pa55word@db.example/x", "Authorization: Bearer abcdefghijkl123"]:
            evaluation = outcome(result([finding(body=leak)]))
            self.assertEqual((evaluation["outcome"], evaluation["withheld"]), ("human", True), leak)
        self.assertEqual(outcome(result([finding(body="`const token = getToken()` and process.env.SECRET")]))["outcome"], "advisory")

    def test_check_output_can_only_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            ev, comment, inline = (os.path.join(tmp, n) for n in ("e.json", "c.md", "i.json"))
            with open(ev, "w", encoding="utf-8") as fh:
                json.dump({"outcome": "clean", "reasons": [], "blocking": 0, "advisory": 0, "total": 0, "withheld": False}, fh)
            with open(comment, "w", encoding="utf-8") as fh:
                fh.write("client_secret: abcdef1234567890")
            with open(inline, "w", encoding="utf-8") as fh:
                fh.write("[]")
            evaluate.main(["evaluate.py", "check-output", ev, comment, inline])
            self.assertEqual(contracts.load(ev)["outcome"], "human")


if __name__ == "__main__":
    unittest.main()
