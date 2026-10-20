#!/usr/bin/env python3
"""Turns the reviewer's structured result into what the pre-check publishes.

Everything the reviewer returns is untrusted: it read text written by the
author of the pull request and by others, and may have been steered by it.
This script therefore
  - checks the result against the schema by hand and derives the outcome from
    the findings and the scope alone (the reviewer's own "result" is ignored),
  - never lets a cut-off review, a change to CI or dependency resolution, or a
    file nobody could see end as "passed",
  - escapes every piece of model text before it reaches Markdown: no HTML, no
    images, no mentions, no links outside an allowlist, no suggestion blocks,
    no line breaks in single-line fields, capped lengths,
  - redacts anything that looks like a credential.

Usage: render.py RESULT_JSON SCOPE_JSON OUT_DIR
Environment: HEAD_SHA, RUN_URL, MODEL, STANDARDS_SHA, REPO.
Writes OUT_DIR/outcome (passed | changes | human | invalid), OUT_DIR/comment.md
and OUT_DIR/inline.json; prints nothing taken from the result.
"""

import hashlib
import json
import os
import re
import sys

MARKER = "<!-- gi-pre-check -->"
FINDING_MARKER = "<!-- gi-pre-check-finding {} -->"
MAX_COMMENT = 60000
MAX_ITEMS = 20
MAX_FINDINGS = 30
MAX_INLINE = 15
ALLOWED_LINK = re.compile(
    r"^https://(github\.com/gi-org-pl/|gi\.org\.pl/|(www\.)?figma\.com/)[A-Za-z0-9._~/?=&%:+#-]*$"
)
SECRET_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_-]{8,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
    re.compile(r"(AKIA|ASIA)[A-Z0-9]{16}"),
    re.compile(r"xox[abpsr]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    # Long encoded runs: a token may come back base64- or hex-encoded.
    re.compile(r"[A-Za-z0-9+/_-]{80,}={0,2}"),
]
CATEGORIES = [
    ("data_structures", "Data structures"),
    ("state", "State"),
    ("api_contracts", "API contracts"),
    ("ux_behaviours", "UX behaviours"),
    ("new_dependencies", "New dependencies"),
    ("architecture", "Architecture"),
]
ZWSP = "​"


def redact(text):
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[redacted]", text)
    return text


def escape_plain(text):
    """Escapes text outside code: HTML, entities, mentions, images, links."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"@(?=[A-Za-z0-9_-])", "@" + ZWSP, text)
    text = text.replace("![", "[")

    def link(match):
        label, url = match.group(1), match.group(2)
        if ALLOWED_LINK.match(url):
            return "[{}]({})".format(label, url)
        return "{} (`{}`)".format(label, url.replace("`", ""))

    text = re.sub(r"\[([^\]\n]*)\]\(([^)\s]*)\)", link, text)

    def bare(match):
        url = match.group(0)
        return url if ALLOWED_LINK.match(url) else "`{}`".format(url)

    # Bare addresses outside an allowlisted link become code, not links.
    parts = re.split(r"(\[[^\]\n]*\]\([^)\s]*\))", text)
    for i in range(0, len(parts), 2):
        parts[i] = re.sub(r"(?<![(`])\b(?:https?|ftp)://[^\s)`]+", bare, parts[i])
    return "".join(parts)


def escape_line(text):
    """Escapes one line, keeping inline code spans literal."""
    parts = text.split("`")
    out = []
    for i, part in enumerate(parts):
        unterminated_last = len(parts) % 2 == 0 and i == len(parts) - 1
        if i % 2 == 1 and not unterminated_last:
            out.append("`" + part.replace("\n", " ") + "`")
        else:
            out.append(("`" if unterminated_last else "") + escape_plain(part))
    return "".join(out)


def one_line(value, limit):
    """A single-line field: no line breaks, so no headings or blocks of its own."""
    text = redact(" ".join(str(value).split()))
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    text = escape_line(text)
    # A leading character that would start a heading, quote or list in Markdown.
    return re.sub(r"^([#>+*-])", r"\\\1", text)


def multi_line(value, limit):
    """A multi-line body: fenced code stays literal, suggestion blocks become
    plain code, everything else is escaped line by line."""
    text = redact(str(value).replace("\r", ""))
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    out, fence = [], None
    for line in text.split("\n"):
        match = re.match(r"^(\s*)(`{3,}|~{3,})(.*)$", line)
        if fence is None and match:
            fence = match.group(2)
            out.append(match.group(1) + fence)  # the info string goes: no `suggestion`
            continue
        if fence is not None:
            if match and match.group(2).startswith(fence[0] * len(fence)) and not match.group(3).strip():
                out.append(match.group(1) + match.group(2))
                fence = None
            else:
                out.append(line)
            continue
        out.append(escape_line(line))
    if fence is not None:
        out.append(fence)
    return "\n".join(out)


def code(name):
    # Scope values are file names without backticks (collect-context.sh
    # refuses others) or our own references; keep them literal.
    return "`{}`".format(str(name).replace("`", ""))


def is_str_list(value):
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


def validate(result):
    if not isinstance(result, dict):
        return False
    if result.get("result") not in ("passed", "changes"):
        return False
    if not isinstance(result.get("summary"), str):
        return False
    decisions = result.get("decisions")
    if not isinstance(decisions, dict) or not all(is_str_list(decisions.get(k)) for k, _ in CATEGORIES):
        return False
    for key in ("checked", "not_checked", "qa"):
        if not is_str_list(result.get(key)):
            return False
    findings = result.get("findings")
    if not isinstance(findings, list):
        return False
    for f in findings:
        if not isinstance(f, dict):
            return False
        if f.get("severity") not in ("blocking", "non-blocking"):
            return False
        if not isinstance(f.get("path"), str) or not isinstance(f.get("title"), str):
            return False
        if not isinstance(f.get("body", ""), str) or not isinstance(f.get("inline", False), bool):
            return False
        line = f.get("line")
        if line is not None and (not isinstance(line, int) or isinstance(line, bool) or not 0 < line < 10**7):
            return False
        if f.get("side", "RIGHT") not in ("RIGHT", "LEFT"):
            return False
    return True


def main():
    result_path, scope_path, out_dir = sys.argv[1:4]
    head = os.environ.get("HEAD_SHA", "")
    run_url = os.environ.get("RUN_URL", "")
    model = re.sub(r"[^A-Za-z0-9._-]", "", os.environ.get("MODEL", ""))[:64] or "default"
    standards = re.sub(r"[^0-9a-f]", "", os.environ.get("STANDARDS_SHA", ""))[:40]

    with open(scope_path, encoding="utf-8") as fh:
        scope = json.load(fh)
    try:
        with open(result_path, encoding="utf-8") as fh:
            result = json.load(fh)
    except (OSError, ValueError):
        result = None

    def write(name, content):
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as fh:
            fh.write(content)

    if not validate(result):
        write("outcome", "invalid")
        write("comment.md", "")
        write("inline.json", "[]")
        return

    findings = result["findings"][:MAX_FINDINGS]
    blocking = sum(1 for f in findings if f["severity"] == "blocking")

    human = []
    if scope.get("truncated"):
        human.append("the pull request is too large for a full pre-check")
    if scope.get("too_large"):
        human.append("some files are too large for GitHub to show their diff")
    if scope.get("workflow_changes"):
        human.append("it changes CI workflows")
    if set(scope.get("human_paths", [])) - set(scope.get("workflow_changes", [])):
        human.append("it changes code owners or dependency resolution")

    outcome = "changes" if blocking else ("human" if human else "passed")

    hunks = scope.get("hunks", {})

    def in_diff(f):
        side = f.get("side", "RIGHT")
        return any(h[side][0] <= f["line"] <= h[side][1] for h in hunks.get(f["path"], []))

    inline = []
    for f in findings:
        if not (f.get("inline") and f.get("line") and in_diff(f) and len(inline) < MAX_INLINE):
            f["_inline"] = None
            continue
        fingerprint = hashlib.sha256(
            (f["path"] + "\n" + " ".join(f["title"].lower().split())).encode("utf-8")
        ).hexdigest()[:16]
        body = "**[{}]** {}\n\n{}\n\n{}".format(
            f["severity"],
            one_line(f["title"], 200),
            multi_line(f.get("body", ""), 3000),
            FINDING_MARKER.format(fingerprint),
        )
        inline.append(
            {"path": f["path"], "line": f["line"], "side": f.get("side", "RIGHT"), "body": body, "fingerprint": fingerprint}
        )
        f["_inline"] = fingerprint

    lines = []
    if outcome == "passed":
        lines.append("**Result:** no findings - the reviewer found nothing to fix. This is not an approval.")
    elif outcome == "changes":
        lines.append("**Result:** changes needed - {} blocking finding(s).".format(blocking))
    else:
        lines.append("**Result:** needs a person's review - " + "; ".join(human) + ". The pre-check does not pass such a pull request.")
    if outcome == "changes" and human:
        lines.append("")
        lines.append("A person has to look at it in any case: " + "; ".join(human) + ".")
    lines.append("")
    lines.append("Reviewer's summary: " + one_line(result["summary"], 600))

    if findings:
        lines += ["", "### Findings", ""]
        for f in findings:
            where = code(f["path"] + (":{}".format(f["line"]) if f.get("line") else ""))
            # report.sh replaces the marker once it knows whether the comment
            # was attached; model text cannot contain "<", so it cannot forge one.
            note = "<!-- inline {} -->".format(f["_inline"]) if f.get("_inline") else ""
            lines.append("- **[{}]** {} - {}{}".format(f["severity"], where, one_line(f["title"], 200), note))

    lines += ["", "### Technical decisions in this PR"]
    for key, label in CATEGORIES:
        lines += ["", "**{}**".format(label), ""]
        items = result["decisions"][key][:MAX_ITEMS]
        lines += ["- " + one_line(item, 400) for item in items] or ["- None."]

    lines += ["", "### What was checked", ""]
    lines.append("- The diff of {} file(s), {} changed lines, at commit {}, reviewed in risk order (application code first).".format(
        len(scope.get("reviewed", [])), int(scope.get("diff_lines", 0)), code(str(scope.get("head", ""))[:7])))
    issues = scope.get("issues", [])
    lines.append("- Linked issues: " + (", ".join(code(i) for i in issues) if issues else "none found") + " (comments by members of the organisation only).")
    repo_docs = scope.get("repo_docs", [])
    lines.append("- Standards: gi-tech-standards at {}; the repository guide on the base branch: {}.".format(
        code(str(scope.get("standards", ""))[:7]), ", ".join(code(d) for d in repo_docs) if repo_docs else "none found"))
    if scope.get("docs"):
        lines.append("- Linked documents: " + ", ".join(code(d) for d in scope["docs"]) + ".")
    lines += ["- " + one_line(item, 400) for item in result["checked"][:MAX_ITEMS]]

    lines += ["", "### What was not checked", ""]
    lines.append("- Runtime behaviour: nothing was built, run or tested by the pre-check.")
    if scope.get("truncated"):
        text = "- **Too large for a full pre-check** (cap: {} changed lines) - reviewed: {}.".format(
            int(scope.get("max_diff_lines", 0)), ", ".join(code(n) for n in scope.get("reviewed", [])) or "none")
        if scope.get("not_reviewed"):
            text += " Not reviewed: " + ", ".join(code(n) for n in scope["not_reviewed"]) + "."
        lines.append(text)
    if scope.get("too_large"):
        lines.append("- Too large for GitHub to show a diff, so not reviewed: " + ", ".join(code(n) for n in scope["too_large"]) + ".")
    if scope.get("human_paths"):
        lines.append("- Changes a person has to review (CI, code owners, dependency resolution): " + ", ".join(code(n) for n in scope["human_paths"]) + ".")
    left_out = scope.get("excluded", []) + scope.get("binary", [])
    if left_out:
        lines.append("- Left out of the diff as tests, test helpers, generated, lock or binary files: " + ", ".join(code(n) for n in left_out) + ".")
    if scope.get("figma"):
        links = " ".join("[{}]({})".format(i + 1, url) for i, url in enumerate(scope["figma"]) if ALLOWED_LINK.match(url))
        lines.append("- Visual fidelity against the Figma design was judged only from the design comparison in the pull request description: the reviewer checks that it is there and covers the changed views, but sees neither Figma nor the images. Figma links: " + links + ".")
    lines += ["- " + one_line(note, 400) for note in scope.get("notes", [])]
    lines += ["- " + one_line(item, 400) for item in result["not_checked"][:MAX_ITEMS]]

    lines += ["", "### For QA", ""]
    lines += ["- " + one_line(item, 400) for item in result["qa"][:MAX_ITEMS]] or ["- Nothing specific beyond the issue's acceptance criteria."]

    body = "\n".join(lines)
    if len(body) > MAX_COMMENT:
        body = body[:MAX_COMMENT] + "\n\n(The rest was cut: the comment would be too long.)"

    footer = (
        "\n\n<sub>AI pre-check of commit `{}` with model `{}` ([workflow run]({})), following "
        "[the reviewer instructions](https://github.com/gi-org-pl/gi-tech-standards/blob/{}/docs/frontend/PRE_CHECK_REVIEWER.md). "
        "Advisory only: the reviewer can be misled by the content it reviews. The result that counts is the "
        "`pre-check / review` check of the head commit; a person accepts or rejects the pull request.</sub>"
    ).format(re.sub(r"[^0-9a-f]", "", head)[:7], model, run_url if ALLOWED_LINK.match(run_url) else "", standards)

    write("outcome", outcome)
    write("comment.md", MARKER + "\n## Pre-check\n\n" + body + footer + "\n")
    write("inline.json", json.dumps(inline))


if __name__ == "__main__":
    main()
