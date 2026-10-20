"""Tests of gate.py: every branch of the decision table and the input checks."""

import datetime
import os
import sys
import unittest

import fakes
from fakes import FakeGitHub, GitHubError

sys.path.insert(0, fakes.ROOT)
import gate  # noqa: E402

NOW = datetime.datetime(2026, 10, 20, 12, 0, tzinfo=datetime.timezone.utc)
RUNS = "repos/gi-org-pl/app/actions/runs?*"


def env(**extra):
    data = {"EVENT": "pull_request", "ACTION": "synchronize", "DRAFT": "false", "HEAD_REPO": "gi-org-pl/app",
            "REPO": "gi-org-pl/app", "HEAD_REF": "feature/x", "PR_NUMBER": "7", "AUTHOR_TYPE": "User",
            "ACTOR": "someone", "HAS_TOKEN": "true", "MAX_RUNS": "8",
            "CALLER_REF": "gi-org-pl/app/.github/workflows/frontend-pre-check.yml@refs/pull/7/merge",
            "MODEL": "sonnet", "MAX_TURNS": "60", "MAX_DIFF_LINES": "3000", "TIMEOUT": "20",
            "EXCLUDE_PATHS": "*.test.ts", "DOC_REPOS": "gi-org-pl/product",
            "WORKFLOW_SHA": "a" * 40, "WORKFLOW_REPOSITORY": "gi-org-pl/gi-tech-standards"}
    data.update(extra)
    return data


def runs(count, pr=7):
    run = {"path": ".github/workflows/frontend-pre-check.yml", "conclusion": "success", "pull_requests": [{"number": pr}]}
    return [{"workflow_runs": [run] * count}]


def gh(permission="write", run_pages=None):
    routes = {"repos/gi-org-pl/app/collaborators/someone/permission": {"permission": permission}}
    routes[RUNS] = run_pages if run_pages is not None else runs(0)
    return FakeGitHub(routes)


def decide(environment, github=None):
    slept = []
    verdict, _ = gate.decide(github or gh(), environment, now=NOW, sleep=slept.append)
    return verdict, slept


class DecisionTableTest(unittest.TestCase):
    def test_run(self):
        self.assertEqual(decide(env())[0], "run")

    def test_merge_queue(self):
        self.assertEqual(decide(env(EVENT="merge_group"))[0], "queue")

    def test_skips(self):
        cases = [env(EVENT="push"), env(HEAD_REPO="someone/fork"), env(DRAFT="true"), env(HAS_TOKEN="false"),
                 env(AUTHOR_TYPE="Bot"), env(ACTOR="dependabot[bot]")]
        for case in cases:
            self.assertEqual(decide(case)[0], "skip", case)
        self.assertEqual(decide(env(), gh(permission="read"))[0], "skip")

    def test_permission_api_failure_is_a_skip(self):
        github = FakeGitHub({"repos/gi-org-pl/app/collaborators/someone/permission": GitHubError("down"), RUNS: runs(0)})
        self.assertEqual(decide(env(), github)[0], "skip")

    def test_run_limit_over_every_page_and_only_this_pr(self):
        self.assertEqual(decide(env(), gh(run_pages=runs(5) + runs(4)))[0], "block")
        self.assertEqual(decide(env(), gh(run_pages=runs(5) + runs(4, pr=8)))[0], "run")
        self.assertEqual(decide(env(MAX_RUNS="20"), gh(run_pages=runs(5) + runs(4)))[0], "run")

    def test_run_count_api_failure_does_not_block(self):
        github = FakeGitHub({"repos/gi-org-pl/app/collaborators/someone/permission": {"permission": "write"}, RUNS: GitHubError("down")})
        self.assertEqual(decide(env(), github)[0], "run")

    def test_edits_are_debounced(self):
        verdict, slept = decide(env(ACTION="edited"))
        self.assertEqual((verdict, slept), ("run", [30]))


class InputTest(unittest.TestCase):
    def test_valid_inputs(self):
        gate.check_inputs(env())

    def test_invalid_inputs(self):
        for extra in [{"MODEL": "sonnet --mcp-config x"}, {"MODEL": "a\nb"}, {"MAX_TURNS": "0"}, {"MAX_TURNS": "60 --x"},
                      {"MAX_DIFF_LINES": "50"}, {"TIMEOUT": "60"}, {"MAX_RUNS": "100"}, {"EXCLUDE_PATHS": "a b"},
                      {"DOC_REPOS": "other/repo"}, {"WORKFLOW_SHA": ""}, {"WORKFLOW_REPOSITORY": "../x"}]:
            with self.assertRaises(gate.Invalid, msg=str(extra)):
                gate.check_inputs(env(**extra))


if __name__ == "__main__":
    unittest.main()
