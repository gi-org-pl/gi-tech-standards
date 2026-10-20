#!/usr/bin/env python3
"""Presents a pre-check run: the Pre-check comment and the inline comments.

Presentation only. The outcome comes from evaluate.py, computed from the
complete result before anything here is shortened; nothing in this file can
change whether the check passes.

Everything the reviewer wrote is rendered as escaped plain text: no links of
any kind, no images, no HTML, no mentions, no Markdown structure, no
suggestion blocks; fenced and inline code stay literal. Known credential
shapes are redacted. The only links are the ones built here from the scope,
each checked by allowed_link().

Usage:
  render.py RESULT_JSON SCOPE_JSON EVALUATION_JSON OUT_DIR   writes comment.md and inline.json
  render.py withheld EVALUATION_JSON OUT_DIR                 writes the notice that replaces a withheld result
Environment: HEAD_SHA, RUN_URL, MODEL, STANDARDS_SHA, COVERAGE.
"""

import hashlib
import json
import os
import re
import sys
from urllib.parse import unquote, urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import contracts  # noqa: E402
from evaluate import redact  # noqa: E402

MARKER = "<!-- gi-pre-check -->"
FINDING_MARKER = "<!-- gi-pre-check-finding {} -->"
MAX_COMMENT = 60000
MAX_ITEMS = 20
MAX_SHOWN = 30
MAX_INLINE = 15
MAX_BODY = 3000

LINK_SHAPE = re.compile(
    r"^https://(github\.com/gi-org-pl/|gi\.org\.pl/|(www\.)?figma\.com/)[A-Za-z0-9._~/?=&%:+#-]*$"
)
ALLOWED_HOSTS = {"github.com", "gi.org.pl", "figma.com", "www.figma.com"}
CATEGORIES = [
    ("data_structures", "Data structures"),
    ("state", "State"),
    ("api_contracts", "API contracts"),
    ("ux_behaviours", "UX behaviours"),
    ("new_dependencies", "New dependencies"),
    ("architecture", "Architecture"),
]
ZWSP = "​"
MARKDOWN_PUNCTUATION = re.compile(r"([\\`*_{}\[\]()#+\-.!|~=:\"'])")


def allowed_link(url):
    """True for a link to an allowlisted place, and only there: the shape,
    then the host (no user information, no port), then the path percent-decoded
    until stable (catching %252e) without ".", ".." or empty segments or a
    backslash; github.com only under /gi-org-pl/."""
    if not isinstance(url, str) or not LINK_SHAPE.match(url):
        return False
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    netloc = parts.netloc.lower()
    if parts.scheme != "https" or "@" in netloc or ":" in netloc or netloc not in ALLOWED_HOSTS:
        return False
    path = parts.path
    for _ in range(10):
        decoded = unquote(path)
        if decoded == path:
            break
        path = decoded
    else:
        return False
    if "\\" in path or "//" in path or path.startswith("/.."):
        return False
    if any(segment in (".", "..") for segment in path.split("/")):
        return False
    if netloc == "github.com" and not path.startswith("/gi-org-pl/"):
        return False
    return True


def plain(text):
    """Escaped plain text: no HTML, entities, mentions, links or Markdown."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = MARKDOWN_PUNCTUATION.sub(r"\\\1", text)
    text = re.sub(r"(?i)([a-z][a-z0-9+\\.-]*)\\:/", lambda m: m.group(1) + "\\:" + ZWSP + "/", text)
    text = re.sub(r"(?i)\bwww\\\.", "www" + ZWSP + "\\.", text)
    return text.replace("@", "@" + ZWSP)


def code_span(text):
    text = text.replace("`", "'").replace("\n", " ")
    return "`" + text + "`" if text.strip() else ""


def escape_line(text):
    """One line: inline code spans stay literal, everything else is plain."""
    parts = text.split("`")
    if len(parts) % 2 == 0:  # an unterminated span is plain text
        last = parts.pop()
        parts[-1] = parts[-1] + "`" + last
    return "".join(code_span(p) if i % 2 == 1 else plain(p) for i, p in enumerate(parts))


def one_line(value, limit):
    text = redact(" ".join(str(value).split()))
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return escape_line(text)


def multi_line(value, limit):
    """A body: fenced code stays literal (suggestion blocks become plain code),
    everything else is escaped line by line."""
    text = redact(str(value).replace("\r", ""))
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    out, fence = [], None
    for line in text.split("\n"):
        match = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
        if fence is None and match:
            fence = match.group(1)
            out.append(fence)
            continue
        if fence is not None:
            if match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence) and not match.group(2).strip():
                out.append(fence)
                fence = None
            else:
                out.append(line.replace("\t", "    "))
            continue
        out.append(escape_line(line))
    if fence is not None:
        out.append(fence)
    return "\n".join(out)


def code(name):
    return "`{}`".format(str(name).replace("`", "'"))


def fingerprint(f):
    identity = "\n".join([f["path"], str(f.get("line") or ""), f.get("side", "RIGHT"), " ".join(f["title"].lower().split())])
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]


def footer():
    head = re.sub(r"[^0-9a-f]", "", os.environ.get("HEAD_SHA", ""))[:7]
    model = re.sub(r"[^A-Za-z0-9._-]", "", os.environ.get("MODEL", ""))[:64] or "default"
    standards = re.sub(r"[^0-9a-f]", "", os.environ.get("STANDARDS_SHA", ""))[:40]
    run_url = os.environ.get("RUN_URL", "")
    return (
        "\n\n<sub>AI pre-check of commit `{}` with model `{}` ([workflow run]({})), following "
        "[the reviewer instructions](https://github.com/gi-org-pl/gi-tech-standards/blob/{}/docs/frontend/pre-check/REVIEWER.md). "
        "Advisory only: the reviewer can be misled by the content it reviews and can miss things; a clean result is "
        "never a person's sign-off. The result that counts is the `frontend-pre-check / review` check of the head "
        "commit.</sub>"
    ).format(head, model, run_url if allowed_link(run_url) else "", standards)


def result_line(evaluation):
    outcome, reasons = evaluation["outcome"], evaluation["reasons"]
    if outcome == "clean":
        return "**Result:** clean - the reviewer reported no findings. This is not an approval and not a proof that the change is safe."
    if outcome == "advisory":
        return "**Result:** passed with {} advisory finding(s) and no blocking one. This is not an approval.".format(evaluation["advisory"])
    if outcome == "changes":
        line = "**Result:** changes needed - {} blocking finding(s).".format(evaluation["blocking"])
        if reasons:
            line += "\n\nA person has to look at it in any case: " + "; ".join(reasons) + "."
        return line
    return "**Result:** needs a person's review - " + "; ".join(reasons) + ". The pre-check does not pass such a pull request."


def render(result, scope, evaluation, coverage):
    findings = result["findings"]
    shown = sorted(findings, key=lambda f: f["severity"] != "blocking")[:MAX_SHOWN]

    def in_diff(f):
        side = f.get("side", "RIGHT")
        return bool(f.get("line")) and any(h[side][0] <= f["line"] <= h[side][1] for h in scope["hunks"].get(f["path"], []))

    body_limit = MAX_BODY if len(shown) <= 10 else 1200
    inline, entries = [], []
    for f in shown:
        fp = fingerprint(f)
        title = one_line(f["title"], 200)
        body = multi_line(f.get("body", ""), body_limit)
        marker = ""
        if f.get("inline") and in_diff(f) and len(inline) < MAX_INLINE:
            inline.append({
                "path": f["path"], "line": f["line"], "side": f.get("side", "RIGHT"), "fingerprint": fp,
                "body": "**[{}]** {}\n\n{}\n\nThe Pre-check comment of this pull request holds every finding.\n\n{}".format(
                    f["severity"], title, body, FINDING_MARKER.format(fp)),
            })
            # report.sh replaces the marker once it knows whether the comment
            # was attached; model text cannot contain "<", so cannot forge one.
            marker = "<!-- inline {} -->".format(fp)
        where = code(f["path"] + (":{}".format(f["line"]) if f.get("line") else ""))
        entries.append("#### [{}] {}\n\n{}{}\n\n{}".format(f["severity"], title, where, marker, body or "(no details given)"))

    lines = [result_line(evaluation), "", "Reviewer's summary: " + one_line(result["summary"], 600)]
    if entries:
        lines += ["", "### Findings", ""]
        if len(findings) > len(shown):
            lines += ["{} findings were returned; the first {} are shown, blocking ones first. The result above counts all of them.".format(len(findings), len(shown)), ""]
        lines.append("\n\n".join(entries))

    lines += ["", "### Technical decisions in this PR"]
    for key, label in CATEGORIES:
        lines += ["", "**{}**".format(label), ""]
        lines += ["- " + one_line(item, 400) for item in result["decisions"][key][:MAX_ITEMS]] or ["- None."]

    reading = {"full": "complete", "partial": "incomplete", "none": "not observed"}.get(coverage, "not observed")
    lines += ["", "### What was checked", ""]
    lines.append("- The diff of {} file(s), {} changed lines, of head commit {} against base commit {} - the head as it is, not the result of merging it. Files in risk order (application code first); the reviewer's reading of the diff: {}.".format(
        len(scope["reviewed"]), scope["diff_lines"], code(scope["head"][:7]), code(scope["base"][:7]), reading))
    lines.append("- Linked issues: " + (", ".join(code(i) for i in scope["issues"]) if scope["issues"] else "none found") + " (members of the organisation only).")
    lines.append("- Standards: gi-tech-standards at {}; the repository guide on the base branch: {}.".format(
        code(scope["standards"][:7]), ", ".join(code(d) for d in scope["repo_docs"]) if scope["repo_docs"] else "none found"))
    if scope["docs"]:
        lines.append("- Linked documents (default branch): " + ", ".join(code(d) for d in scope["docs"]) + ".")
    lines += ["- " + one_line(item, 400) for item in result["checked"][:MAX_ITEMS]]

    lines += ["", "### What was not checked", "", "- Runtime behaviour: nothing was built, run or tested by the pre-check."]
    if scope["truncated"]:
        text = "- **Too large for a full pre-check** (cap: {} changed lines).".format(scope["max_diff_lines"])
        if scope["not_reviewed"]:
            text += " Not reviewed: " + ", ".join(code(n) for n in scope["not_reviewed"]) + "."
        lines.append(text)
    lines += ["- No reviewable diff: {} - {}.".format(code(u["path"]), u["reason"]) for u in scope["unreviewable"]]
    lines += ["- Needs a person: {} - {}.".format(code(u["path"]), u["reason"]) for u in scope["human_paths"]]
    lines += ["- Renamed or copied: {} to {}.".format(code(r["from"]), code(r["to"])) for r in scope["renamed"]]
    if scope["excluded"]:
        lines.append("- Left out of the diff by policy ({} file(s), {} changed lines): {}.".format(
            len(scope["excluded"]), scope["excluded_lines"], ", ".join(code(n) for n in scope["excluded"])))
    if scope["safe_assets"]:
        lines.append("- Images, listed but not inspected: " + ", ".join(code(n) for n in scope["safe_assets"]) + ".")
    if scope["figma"]:
        links = " ".join("[{}]({})".format(i + 1, url) for i, url in enumerate(scope["figma"]) if allowed_link(url))
        lines.append("- Visual fidelity against the Figma design was judged only from the design comparison in the pull request description: the reviewer checks that it is there and covers the changed views, but sees neither Figma nor the images. Figma links: " + links + ".")
    lines += ["- Cut at its size limit: " + one_line(c, 200) + "." for c in scope["cut_sources"]]
    lines += ["- " + one_line(n, 400) for n in scope["notes"]]
    lines += ["- " + one_line(item, 400) for item in result["not_checked"][:MAX_ITEMS]]

    lines += ["", "### For QA", ""]
    lines += ["- " + one_line(item, 400) for item in result["qa"][:MAX_ITEMS]] or ["- Nothing specific beyond the issue's acceptance criteria."]

    body = "\n".join(lines)
    if len(body) > MAX_COMMENT:
        body = body[:MAX_COMMENT] + "\n\n(The rest was cut: the comment would be too long. The result above counts every finding.)"
    return MARKER + "\n## Pre-check\n\n" + body + footer() + "\n", inline


def withheld_notice():
    return (MARKER + "\n## Pre-check\n\n**Result:** withheld - the reviewer's output contains text that looks like a "
            "credential, so it is not published. A person reviews the pull request; ask an organisation owner to look "
            "at the workflow run if a credential may be involved." + footer() + "\n")


def main(argv):
    if len(argv) == 4 and argv[1] == "withheld":
        with open(os.path.join(argv[3], "comment.md"), "w", encoding="utf-8") as fh:
            fh.write(withheld_notice())
        with open(os.path.join(argv[3], "inline.json"), "w", encoding="utf-8") as fh:
            fh.write("[]")
        return 0
    if len(argv) != 5:
        print(__doc__, file=sys.stderr)
        return 2
    result, scope, evaluation = (contracts.load(p) for p in argv[1:4])
    if evaluation["outcome"] == "invalid":
        return 1
    comment, inline = render(result, scope, evaluation, os.environ.get("COVERAGE", "none"))
    with open(os.path.join(argv[4], "comment.md"), "w", encoding="utf-8") as fh:
        fh.write(comment)
    with open(os.path.join(argv[4], "inline.json"), "w", encoding="utf-8") as fh:
        json.dump(inline, fh)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
