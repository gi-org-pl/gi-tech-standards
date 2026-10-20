"""Fixture tests of classify.py. Run: python3 -m unittest discover -s .github/frontend-pre-check"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import classify  # noqa: E402

PATCH = "@@ -1,2 +1,3 @@\n a\n+b\n c"
DEFAULT = list(classify.EXCLUDE_POLICY)


def f(name, status="modified", patch=PATCH, changes=1, old=None):
    record = {"filename": name, "status": status, "changes": changes, "additions": changes, "deletions": 0}
    if patch is not None:
        record["patch"] = patch
    if old:
        record["previous_filename"] = old
    return record


def run(files, excludes=None, max_lines=3000):
    return classify.classify(files, DEFAULT if excludes is None else excludes, max_lines, 150000)[0]


def human_paths(result):
    return {p["path"] for p in result["human_paths"]}


def unreviewable(result):
    return {p["path"] for p in result["unreviewable"]}


class PolicyTest(unittest.TestCase):
    def test_wildcard_exclusions_are_refused(self):
        for pattern in ["*", "src/*", "*.tsx", "*.ts", "**"]:
            with self.assertRaises(classify.Abort):
                run([f("src/a.tsx")], excludes=[pattern])

    def test_a_subset_of_the_policy_is_accepted(self):
        result = run([f("src/a.test.tsx"), f("src/a.tsx")], excludes=["*.test.tsx"])
        self.assertEqual(result["excluded"], ["src/a.test.tsx"])
        self.assertEqual(result["reviewed"], ["src/a.tsx"])
        self.assertEqual(result["excluded_lines"], 1)

    def test_mixed_test_and_source(self):
        result = run([f("src/a.tsx"), f("src/a.test.tsx"), f("e2e/x.spec.ts")])
        self.assertEqual(result["reviewed"], ["src/a.tsx"])
        self.assertEqual(sorted(result["excluded"]), ["e2e/x.spec.ts", "src/a.test.tsx"])

    def test_suffix_anchoring(self):
        result = run([f("src/auth.test.d/backdoor.ts"), f("src/config.spec.prod.ts")])
        self.assertEqual(sorted(result["reviewed"]), ["src/auth.test.d/backdoor.ts", "src/config.spec.prod.ts"])

    def test_unsafe_names_abort(self):
        for name in ["src/a`b.ts", "src/a\nb.ts", "src/\x7f.ts"]:
            with self.assertRaises(classify.Abort):
                run([f(name)])
        with self.assertRaises(classify.Abort):
            run([f("src/a.ts", status="renamed", old="src/`x.ts")])


class HumanReviewTest(unittest.TestCase):
    def test_protected_paths(self):
        for name in [".github/workflows/ci.yml", ".github/CODEOWNERS", "docs/CODEOWNERS", "CODEOWNERS",
                     "package.json", "apps/web/package.json", "npm-shrinkwrap.json", "bun.lock", "bun.lockb",
                     "pnpm-workspace.yaml", "yarn.lock", ".npmrc", ".yarn/releases/yarn.cjs", "vite.config.ts",
                     "Dockerfile", ".husky/pre-commit", "tsconfig.json"]:
            self.assertIn(name, human_paths(run([f(name)])), name)

    def test_rename_out_of_a_protected_path(self):
        result = run([f("docs/old-owners.txt", status="renamed", old=".github/CODEOWNERS")])
        self.assertIn(".github/CODEOWNERS", human_paths(result))
        result = run([f("ci/build.yml", status="renamed", old=".github/workflows/build.yml")])
        self.assertIn(".github/workflows/build.yml", human_paths(result))
        self.assertIn(".github/workflows/build.yml", result["workflow_changes"])

    def test_rename_into_a_protected_path(self):
        result = run([f(".github/workflows/x.yml", status="renamed", old="tmp/x.yml")])
        self.assertIn(".github/workflows/x.yml", human_paths(result))

    def test_rename_without_patch(self):
        result = run([f("ci/build.yml", status="renamed", old=".github/workflows/build.yml", patch=None, changes=0)])
        self.assertIn("ci/build.yml", unreviewable(result))
        result = run([f("src/b.ts", status="renamed", old="src/a.ts", patch=None, changes=0)])
        self.assertIn("src/b.ts", unreviewable(result))

    def test_removal_of_protected_and_lock_files(self):
        for name in [".github/workflows/ci.yml", "yarn.lock", ".github/CODEOWNERS"]:
            result = run([f(name, status="removed")])
            self.assertIn(name, human_paths(result), name)

    def test_lock_file_is_excluded_and_still_needs_a_person(self):
        result = run([f("yarn.lock", changes=500)])
        self.assertIn("yarn.lock", result["excluded"])
        self.assertIn("yarn.lock", human_paths(result))


class NoPatchTest(unittest.TestCase):
    def test_binary_and_mode_changes_are_unreviewable(self):
        for record in [f("bin/tool", patch=None, changes=0), f("public/app.wasm", patch=None, changes=0),
                       f("dist/bundle.js", patch=None, changes=900), f("scripts/run.sh", status="changed", changes=0),
                       f("src/a.ts", status="changed")]:
            self.assertIn(record["filename"], unreviewable(run([record])), record["filename"])

    def test_images_are_safe_assets(self):
        result = run([f("public/logo.png", status="added", patch=None, changes=0)])
        self.assertEqual(result["safe_assets"], ["public/logo.png"])
        self.assertEqual(result["unreviewable"], [])

    def test_renamed_image_is_not_a_safe_asset(self):
        result = run([f("public/b.png", status="renamed", old="public/a.png", patch=None, changes=0)])
        self.assertIn("public/b.png", unreviewable(result))

    def test_svg_without_patch_is_unreviewable(self):
        result = run([f("public/icon.svg", patch=None, changes=0)])
        self.assertIn("public/icon.svg", unreviewable(result))


class OrderAndCapTest(unittest.TestCase):
    def test_application_code_first_and_cap(self):
        files = [f("aaa/noise{}.md".format(i), changes=100) for i in range(5)] + [f("src/real.ts", changes=100)]
        result = run(files, max_lines=150)
        self.assertEqual(result["reviewed"], ["src/real.ts"])
        self.assertEqual(len(result["not_reviewed"]), 5)

    def test_hunk_ranges(self):
        result = run([f("src/a.ts", patch="@@ -10,3 +12,4 @@\n a\n+b\n c\n d")])
        self.assertEqual(result["hunks"]["src/a.ts"], [{"LEFT": [10, 12], "RIGHT": [12, 15]}])


if __name__ == "__main__":
    unittest.main()
