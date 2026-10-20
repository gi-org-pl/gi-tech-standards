#!/usr/bin/env python3
"""Turns the reviewer's structured result into what the pre-check publishes.

Everything the reviewer returns is untrusted: it read text written by the
author of the pull request and by others, and may have been steered by it, or
may simply be wrong. This script therefore
  - checks the whole result against the schema by hand and derives the outcome
    from all findings (before any display cap), the deterministic scope and the
    reviewer's measured coverage of the diff; the reviewer's own "result" is
    ignored,
  - never lets a cut-off review, an unreviewable change, a change to CI,
    dependencies or build configuration, cut context, or an incomplete reading
    of the diff end as a pass,
  - renders every piece of model text as escaped plain text: no links of any
    kind, no images, no HTML, no mentions, no Markdown structure, no suggestion
    blocks; fenced and inline code stay literal,
  - publishes every finding with its body in the main comment (inline comments
    are a convenience),
  - redacts known credential shapes and then scans the final output for
    anything that still looks like a credential, withholding the result if so.
    This is a heuristic backstop, not data-loss prevention.

Usage: render.py RESULT_JSON SCOPE_JSON OUT_DIR
Environment: HEAD_SHA, RUN_URL, MODEL, STANDARDS_SHA, COVERAGE (full | partial |
none). Writes OUT_DIR/outcome (clean | advisory | changes | human |
quarantine | invalid), OUT_DIR/comment.md and OUT_DIR/inline.json; prints
nothing taken from the result.
"""

import hashlib
import json
import os
import re
import sys
from urllib.parse import unquote, urlsplit

MARKER = "<!-- gi-pre-check -->"
FINDING_MARKER = "<!-- gi-pre-check-finding {} -->"
MAX_COMMENT = 60000
MAX_ITEMS = 20
MAX_FINDINGS = 30
MAX_INLINE = 15
MAX_BODY = 3000

LINK_SHAPE = re.compile(
    r"^https://(github\.com/gi-org-pl/|gi\.org\.pl/|(www\.)?figma\.com/)[A-Za-z0-9._~/?=&%:+#-]*$"
)
ALLOWED_HOSTS = {"github.com", "gi.org.pl", "figma.com", "www.figma.com"}

SECRET_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_-]{8,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
    re.compile(r"(AKIA|ASIA)[A-Z0-9]{16}"),
    re.compile(r"xox[abpsr]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    # Long encoded runs: a token may come back base64- or hex-encoded. This
    # over-redacts on purpose (see PROCESS.md, "The Pre-check comment").
    re.compile(r"[A-Za-z0-9+/_-]{80,}={0,2}"),
]
# Checked on the final output after redaction; a hit withholds the result.
LEAK_PATTERNS = [
    # A secret-named key with a value that looks generated: letters and digits,
    # 12 or more characters, no dots or parentheses (so not code such as
    # `token = getToken()` or `process.env.SECRET`).
    re.compile(r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|client[_-]?secret|access[_-]?key)\b\s*[:=]\s*['\"]?(?=[A-Za-z0-9_+/-]*\d)(?=[A-Za-z0-9_+/-]*[A-Za-z])[A-Za-z0-9_+/-]{12,}"),
    re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^\s/:@]+:[^\s/@]+@"),
    re.compile(r"(?i)\bauthorization\s*:\s*(bearer|basic|token)\s+\S{8,}"),
    re.compile(r"\b(sk|rk|pk)_(live|test)_[A-Za-z0-9]{16,}"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}"),
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
MARKDOWN_PUNCTUATION = re.compile(r"([\\`*_{}\[\]()#+\-.!|~=:\"'])")


def allowed_link(url):
    """True for a link to an allowlisted place, and only there.

    The shape check alone would pass https://github.com/gi-org-pl/../other,
    which a browser resolves outside the organisation. So the path is also
    percent-decoded until it is stable (catching double encoding such as
    %252e) and rejected if it holds a "." or ".." segment, a backslash or an
    empty segment; the host must be one of the allowlisted ones, without
    user information or a port. Only links the workflow builds itself (from
    the scope) are ever rendered as links; model text never is.
    """
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


def redact(text):
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[redacted]", text)
    return text


def leaks(text):
    return any(p.search(text) for p in LEAK_PATTERNS)


def plain(text):
    """Escaped plain text: no HTML, entities, mentions, links or Markdown."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = MARKDOWN_PUNCTUATION.sub(r"\\\1", text)
    # No autolinks: break schemes, "www." and e-mail addresses.
    text = re.sub(r"(?i)([a-z][a-z0-9+\\.-]*)\\:/", lambda m: m.group(1) + "\\:" + ZWSP + "/", text)
    text = re.sub(r"(?i)\bwww\\\.", "www" + ZWSP + "\\.", text)
    text = text.replace("@", "@" + ZWSP)
    return text


def code_span(text):
    """Literal inline code; a backtick inside cannot close it."""
    text = text.replace("`", "'").replace("\n", " ")
    return "`" + text + "`" if text.strip() else ""


def escape_line(text):
    """One line: inline code spans stay literal, everything else is plain."""
    parts = text.split("`")
    if len(parts) % 2 == 0:  # an unterminated span is plain text
        last = parts.pop()
        parts[-1] = parts[-1] + "`" + last
    out = []
    for i, part in enumerate(parts):
        out.append(code_span(part) if i % 2 == 1 else plain(part))
    return "".join(out)


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
            out.append(fence)  # the info string goes: no `suggestion`
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


def fingerprint(f):
    identity = "\n".join([f["path"], str(f.get("line") or ""), f.get("side", "RIGHT"), " ".join(f["title"].lower().split())])
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]


def human_reasons(scope, findings, coverage):
    reasons = []
    if scope.get("file_count", 0) > 0 and not scope.get("reviewed"):
        reasons.append("no file of it could be reviewed")
    if scope.get("truncated"):
        reasons.append("the pull request is too large for a full pre-check")
    if scope.get("unreviewable"):
        reasons.append("some changes have no reviewable diff")
    if scope.get("workflow_changes"):
        reasons.append("it changes CI workflows")
    if any(not p["path"].startswith((".github/workflows/", ".github/actions/")) for p in scope.get("human_paths", [])):
        reasons.append("it changes code owners, dependencies or build configuration")
    if scope.get("cut_sources"):
        reasons.append("some linked context was cut at its size limit")
    if scope.get("reviewed") and coverage != "full":
        reasons.append("the reviewer did not read the whole diff")
    if len(findings) > MAX_FINDINGS:
        reasons.append("the reviewer returned more findings than allowed")
    return reasons


def main():
    result_path, scope_path, out_dir = sys.argv[1:4]
    head = re.sub(r"[^0-9a-f]", "", os.environ.get("HEAD_SHA", ""))[:40]
    run_url = os.environ.get("RUN_URL", "")
    model = re.sub(r"[^A-Za-z0-9._-]", "", os.environ.get("MODEL", ""))[:64] or "default"
    standards = re.sub(r"[^0-9a-f]", "", os.environ.get("STANDARDS_SHA", ""))[:40]
    coverage = os.environ.get("COVERAGE", "none")

    def write(name, content):
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as fh:
            fh.write(content)

    with open(scope_path, encoding="utf-8") as fh:
        scope = json.load(fh)
    try:
        with open(result_path, encoding="utf-8") as fh:
            result = json.load(fh)
    except (OSError, ValueError):
        result = None
    if not validate(result):
        write("outcome", "invalid")
        write("comment.md", "")
        write("inline.json", "[]")
        return

    findings = result["findings"]
    # The verdict uses every finding; only the display is capped.
    blocking = sum(1 for f in findings if f["severity"] == "blocking")
    advisory = len(findings) - blocking
    human = human_reasons(scope, findings, coverage)
    if blocking:
        outcome = "changes"
    elif human:
        outcome = "human"
    elif advisory:
        outcome = "advisory"
    else:
        outcome = "clean"
    shown = sorted(findings, key=lambda f: f["severity"] != "blocking")[:MAX_FINDINGS]

    hunks = scope.get("hunks", {})

    def in_diff(f):
        side = f.get("side", "RIGHT")
        return bool(f.get("line")) and any(h[side][0] <= f["line"] <= h[side][1] for h in hunks.get(f["path"], []))

    body_limit = MAX_BODY if len(shown) <= 10 else 1200
    inline = []
    entries = []
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
        entries.append("#### [{}] {}\n\n{}{}\n\n{}".format(
            f["severity"], title, where, marker, body or "(no details given)"))

    lines = []
    if outcome == "clean":
        lines.append("**Result:** clean - the reviewer reported no findings. This is not an approval and not a proof that the change is safe.")
    elif outcome == "advisory":
        lines.append("**Result:** passed with {} advisory finding(s) and no blocking one. This is not an approval.".format(advisory))
    elif outcome == "changes":
        lines.append("**Result:** changes needed - {} blocking finding(s).".format(blocking))
    else:
        lines.append("**Result:** needs a person's review - " + "; ".join(human) + ". The pre-check does not pass such a pull request.")
    if outcome == "changes" and human:
        lines += ["", "A person has to look at it in any case: " + "; ".join(human) + "."]
    lines += ["", "Reviewer's summary: " + one_line(result["summary"], 600)]

    if entries:
        lines += ["", "### Findings", ""]
        if len(findings) > len(shown):
            lines += ["{} findings were returned; the first {} are shown, blocking ones first.".format(len(findings), len(shown)), ""]
        lines.append("\n\n".join(entries))

    lines += ["", "### Technical decisions in this PR"]
    for key, label in CATEGORIES:
        lines += ["", "**{}**".format(label), ""]
        items = result["decisions"][key][:MAX_ITEMS]
        lines += ["- " + one_line(item, 400) for item in items] or ["- None."]

    lines += ["", "### What was checked", ""]
    lines.append("- The diff of {} file(s), {} changed lines, of head commit {} against base commit {} - the head as it is, not the result of merging it. Files in risk order (application code first); the reviewer's reading of the diff: {}.".format(
        len(scope.get("reviewed", [])), int(scope.get("diff_lines", 0)), code(str(scope.get("head", ""))[:7]),
        code(str(scope.get("base", ""))[:7]), {"full": "complete", "partial": "incomplete", "none": "not observed"}.get(coverage, "not observed")))
    issues = scope.get("issues", [])
    lines.append("- Linked issues: " + (", ".join(code(i) for i in issues) if issues else "none found") + " (members of the organisation only).")
    repo_docs = scope.get("repo_docs", [])
    lines.append("- Standards: gi-tech-standards at {}; the repository guide on the base branch: {}.".format(
        code(str(scope.get("standards", ""))[:7]), ", ".join(code(d) for d in repo_docs) if repo_docs else "none found"))
    if scope.get("docs"):
        lines.append("- Linked documents (default branch): " + ", ".join(code(d) for d in scope["docs"]) + ".")
    lines += ["- " + one_line(item, 400) for item in result["checked"][:MAX_ITEMS]]

    lines += ["", "### What was not checked", ""]
    lines.append("- Runtime behaviour: nothing was built, run or tested by the pre-check.")
    if scope.get("truncated"):
        text = "- **Too large for a full pre-check** (cap: {} changed lines).".format(int(scope.get("max_diff_lines", 0)))
        if scope.get("not_reviewed"):
            text += " Not reviewed: " + ", ".join(code(n) for n in scope["not_reviewed"]) + "."
        lines.append(text)
    for item in scope.get("unreviewable", []):
        lines.append("- No reviewable diff: {} - {}.".format(code(item["path"]), item["reason"]))
    for item in scope.get("human_paths", []):
        lines.append("- Needs a person: {} - {}.".format(code(item["path"]), item["reason"]))
    for item in scope.get("renamed", []):
        lines.append("- Renamed or copied: {} to {}.".format(code(item["from"]), code(item["to"])))
    if scope.get("excluded"):
        lines.append("- Left out of the diff by policy ({} file(s), {} changed lines): {}.".format(
            len(scope["excluded"]), int(scope.get("excluded_lines", 0)), ", ".join(code(n) for n in scope["excluded"])))
    if scope.get("safe_assets"):
        lines.append("- Images, listed but not inspected: " + ", ".join(code(n) for n in scope["safe_assets"]) + ".")
    if scope.get("figma"):
        links = " ".join("[{}]({})".format(i + 1, url) for i, url in enumerate(scope["figma"]) if allowed_link(url))
        lines.append("- Visual fidelity against the Figma design was judged only from the design comparison in the pull request description: the reviewer checks that it is there and covers the changed views, but sees neither Figma nor the images. Figma links: " + links + ".")
    for source in scope.get("cut_sources", []):
        lines.append("- Cut at its size limit: " + one_line(source, 200) + ".")
    lines += ["- " + one_line(note, 400) for note in scope.get("notes", [])]
    lines += ["- " + one_line(item, 400) for item in result["not_checked"][:MAX_ITEMS]]

    lines += ["", "### For QA", ""]
    lines += ["- " + one_line(item, 400) for item in result["qa"][:MAX_ITEMS]] or ["- Nothing specific beyond the issue's acceptance criteria."]

    body = "\n".join(lines)
    if len(body) > MAX_COMMENT:
        body = body[:MAX_COMMENT] + "\n\n(The rest was cut: the comment would be too long. The outcome above counts every finding.)"

    footer = (
        "\n\n<sub>AI pre-check of commit `{}` with model `{}` ([workflow run]({})), following "
        "[the reviewer instructions](https://github.com/gi-org-pl/gi-tech-standards/blob/{}/docs/frontend/pre-check/REVIEWER.md). "
        "Advisory only: the reviewer can be misled by the content it reviews and can miss things; a clean result is "
        "never a person's sign-off. The result that counts is the `frontend-pre-check / review` check of the head "
        "commit.</sub>"
    ).format(head[:7], model, run_url if allowed_link(run_url) else "", standards)

    # Scanned twice: the model's text as it came (after redaction), and the
    # final output, so that escaping cannot hide a value from the scan.
    texts = [result["summary"]] + result["checked"] + result["not_checked"] + result["qa"]
    texts += [item for key, _ in CATEGORIES for item in result["decisions"][key]]
    texts += [f["title"] + "\n" + f.get("body", "") for f in findings]
    published = body + "\n".join(item["body"] for item in inline)
    if any(leaks(redact(t)) for t in texts) or leaks(published):
        write("outcome", "quarantine")
        write("comment.md", MARKER + "\n## Pre-check\n\n**Result:** withheld - the reviewer's output contains text that looks like a credential, so it is not published. A person reviews the pull request; ask an organisation owner to look at the workflow run if a credential may be involved." + footer + "\n")
        write("inline.json", "[]")
        return

    write("outcome", outcome)
    write("comment.md", MARKER + "\n## Pre-check\n\n" + body + footer + "\n")
    write("inline.json", json.dumps(inline))


if __name__ == "__main__":
    main()
