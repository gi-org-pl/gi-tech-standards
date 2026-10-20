#!/usr/bin/env python3
"""Classifies the changed files of a pull request for the front-end pre-check.

Deterministic rules, no model: which files the reviewer gets as a diff, which
are left out by policy, and which make the pull request one that only a person
can judge. A file counts as reviewed only when its text diff is in the
reviewer's context; everything else is either excluded by the immutable
policy below, a known-safe asset, or a reason for a person.

classify(files, excludes, max_lines, max_patch_bytes) returns the scope part
of the classification and the text of diff.patch; it raises Abort with
"exclusion_policy" or "unsafe_names" when the pull request cannot be
classified safely.
"""

import fnmatch
import re

# The only exclusions a caller may choose from. They are anchored on file
# suffixes or whole directory names; a caller can narrow them, never widen
# them. In fnmatch, "*" also matches "/", so "*.test.ts" matches any depth.
EXCLUDE_POLICY = [
    "*.test.ts", "*.test.tsx", "*.test.js", "*.test.jsx",
    "*.spec.ts", "*.spec.tsx", "*.spec.js", "*.spec.jsx",
    "__tests__/*", "*/__tests__/*", "__mocks__/*", "*/__mocks__/*",
    "e2e/*", "*.fixture.ts", "*.fixtures.ts", "setupTests.ts",
    "src/utils/vitest/*", "*.snap",
    "yarn.lock", "*/yarn.lock", "package-lock.json", "*/package-lock.json",
    "pnpm-lock.yaml", "*/pnpm-lock.yaml",
]

# Changes to these always need a person, whatever the model says: CI,
# code owners, dependency manifests and resolution, package-manager and
# build configuration, container and deployment descriptors.
HUMAN_REVIEW = [
    (".github/workflows/*", "CI workflow"),
    (".github/actions/*", "CI action"),
    (".github/CODEOWNERS", "code owners"),
    ("docs/CODEOWNERS", "code owners"),
    ("CODEOWNERS", "code owners"),
    ("package.json", "dependency manifest"),
    ("*/package.json", "dependency manifest"),
    ("yarn.lock", "lock file"), ("*/yarn.lock", "lock file"),
    ("package-lock.json", "lock file"), ("*/package-lock.json", "lock file"),
    ("npm-shrinkwrap.json", "lock file"), ("*/npm-shrinkwrap.json", "lock file"),
    ("pnpm-lock.yaml", "lock file"), ("*/pnpm-lock.yaml", "lock file"),
    ("bun.lock", "lock file"), ("bun.lockb", "lock file"),
    ("*/bun.lock", "lock file"), ("*/bun.lockb", "lock file"),
    ("pnpm-workspace.yaml", "workspace configuration"),
    (".npmrc", "package-manager configuration"), ("*/.npmrc", "package-manager configuration"),
    (".yarnrc", "package-manager configuration"), (".yarnrc.yml", "package-manager configuration"),
    (".yarn/*", "package-manager plugins and releases"),
    (".pnpmfile.cjs", "package-manager hooks"),
    (".husky/*", "git hooks"),
    ("*.config.js", "build configuration"), ("*.config.cjs", "build configuration"),
    ("*.config.mjs", "build configuration"), ("*.config.ts", "build configuration"),
    ("*.config.mts", "build configuration"),
    ("tsconfig*.json", "build configuration"), ("*/tsconfig*.json", "build configuration"),
    ("biome.json", "build configuration"),
    (".storybook/*", "build configuration"),
    ("scripts/*", "build scripts"),
    ("Dockerfile*", "container descriptor"), ("*/Dockerfile*", "container descriptor"),
    ("docker-compose*", "container descriptor"), ("compose.y*ml", "container descriptor"),
    ("vercel.json", "deployment descriptor"), ("netlify.toml", "deployment descriptor"),
    (".releaserc*", "release configuration"),
]

# Files without a text diff that may be listed instead of reviewed: raster
# images only, and only when added, modified or removed (not renamed, copied
# or with a changed mode).
SAFE_ASSET = re.compile(r"\.(png|jpe?g|gif|webp|avif|ico)$", re.IGNORECASE)
SAFE_ASSET_STATUS = {"added", "modified", "removed"}
UNSAFE_NAME = re.compile(r"[\x00-\x1f\x7f`]")
CODE = re.compile(r"\.(ts|tsx|js|jsx|mjs|cjs|css)$")
TEXTISH = re.compile(r"\.(ts|tsx|js|jsx|mjs|cjs|css|html|json|ya?ml)$")
DOC = re.compile(r"\.(md|mdx|txt)$")
MAX_PATCH_BYTES = 150000
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", re.MULTILINE)


class Abort(Exception):
    pass


def rank(name):
    if name.startswith("src/") and CODE.search(name):
        return 0
    if TEXTISH.search(name):
        return 1
    if DOC.search(name):
        return 3
    return 2


def matches(name, patterns):
    return any(fnmatch.fnmatchcase(name, p) for p in patterns)


def protected(name):
    for pattern, reason in HUMAN_REVIEW:
        if fnmatch.fnmatchcase(name, pattern):
            return reason
    return None


def hunks(patch):
    out = []
    for m in HUNK.finditer(patch):
        left, left_len, right, right_len = m.groups()
        left, right = int(left), int(right)
        out.append({
            "LEFT": [left, left + int(left_len or 1) - 1],
            "RIGHT": [right, right + int(right_len or 1) - 1],
        })
    return out


def classify(files, excludes, max_lines, max_patch_bytes):
    for pattern in excludes:
        if pattern not in EXCLUDE_POLICY:
            raise Abort("exclusion_policy")
    for f in files:
        for name in (f.get("filename", ""), f.get("previous_filename") or ""):
            if UNSAFE_NAME.search(name):
                raise Abort("unsafe_names")

    result = {
        "reviewed": [], "not_reviewed": [], "excluded": [], "excluded_lines": 0,
        "safe_assets": [], "unreviewable": [], "human_paths": [], "workflow_changes": [],
        "renamed": [], "diff_lines": 0, "hunks": {}, "file_count": len(files),
    }
    diff = []
    for f in sorted(files, key=lambda f: (rank(f["filename"]), f["filename"])):
        name = f["filename"]
        old = f.get("previous_filename")
        status = f.get("status", "modified")
        changes = int(f.get("changes", 0))
        patch = f.get("patch")
        names = [name] + ([old] if old and old != name else [])

        for n in names:
            reason = protected(n)
            if reason:
                result["human_paths"].append({"path": n, "reason": reason})
            if n.startswith(".github/workflows/") or n.startswith(".github/actions/"):
                result["workflow_changes"].append(n)
        if old and old != name:
            result["renamed"].append({"from": old, "to": name, "status": status})

        if status == "changed":
            result["unreviewable"].append({"path": name, "reason": "the file mode or type changed"})
            continue
        if status in ("renamed", "copied") and patch is None:
            result["unreviewable"].append({"path": name, "reason": "{} without a diff".format(status)})
            continue
        if matches(name, excludes) and (not old or matches(old, excludes)):
            result["excluded"].append(name)
            result["excluded_lines"] += changes
            continue
        if patch is None:
            if SAFE_ASSET.search(name) and status in SAFE_ASSET_STATUS and not old:
                result["safe_assets"].append(name)
            elif changes > 0:
                result["unreviewable"].append({"path": name, "reason": "too large for GitHub to show a diff"})
            else:
                result["unreviewable"].append({"path": name, "reason": "no text diff (binary or empty)"})
            continue
        if len(patch.encode("utf-8")) > max_patch_bytes:
            result["unreviewable"].append({"path": name, "reason": "the diff is too large to review"})
            continue
        if result["diff_lines"] + changes > max_lines:
            result["not_reviewed"].append(name)
            continue
        result["diff_lines"] += changes
        result["reviewed"].append(name)
        result["hunks"][name] = hunks(patch)
        diff += [
            "diff --git a/{} b/{}".format(old or name, name),
            "status: {}, +{} -{}".format(status, f.get("additions", 0), f.get("deletions", 0)),
            "--- a/{}".format(old or name),
            "+++ b/{}".format(name),
            patch,
            "",
        ]
    return result, "\n".join(diff) + ("\n" if diff else "")
