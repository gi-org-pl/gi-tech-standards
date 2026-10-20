"""Tests of review/evidence.py: the measured reading of the diff."""

import unittest

import fakes  # noqa: F401  (import paths)
import evidence

DIFF = "/w/.pre-check-context/diff.patch"


def read(path=DIFF, **args):
    data = {"file_path": path}
    data.update(args)
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read", "input": data}]}}


class CoverageTest(unittest.TestCase):
    def test_full_in_one_read(self):
        self.assertEqual(evidence.coverage([read()], DIFF, 1500), "full")

    def test_full_in_parts(self):
        self.assertEqual(evidence.coverage([read(limit=1000), read(offset=1001, limit=1000)], DIFF, 1800), "full")

    def test_a_gap_or_a_short_read_is_partial(self):
        self.assertEqual(evidence.coverage([read(limit=500), read(offset=700, limit=2000)], DIFF, 2500), "partial")
        self.assertEqual(evidence.coverage([read()], DIFF, 2500), "partial")

    def test_other_files_and_grep_do_not_count(self):
        grep = {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Grep", "input": {"path": DIFF}}]}}
        self.assertEqual(evidence.coverage([read(path="/w/src/a.ts"), grep], DIFF, 10), "none")

    def test_empty_diff_is_full(self):
        self.assertEqual(evidence.coverage([], DIFF, 0), "full")

    def test_tools_and_usage(self):
        messages = [{"type": "system", "subtype": "init", "tools": ["Read", "Glob", "Grep", "bad name!"]},
                    {"type": "result", "num_turns": 3, "duration_ms": 1000, "total_cost_usd": 0.1, "usage": {"input_tokens": "x"}}]
        self.assertEqual(evidence.tools(messages), "Read,Glob,Grep")
        self.assertEqual(evidence.usage(messages)["usage"]["input_tokens"], None)


if __name__ == "__main__":
    unittest.main()
