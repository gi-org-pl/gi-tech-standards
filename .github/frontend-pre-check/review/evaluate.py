#!/usr/bin/env python3
"""The authoritative outcome of a pre-check run.

Computed from the complete, validated reviewer result, the collected scope and
the measured coverage of the diff - before anything is shortened for display,
so that no presentation limit can change whether the check passes. The
reviewer's own "result" field is ignored. The outcome is one of
contracts.OUTCOMES.

Usage:
  evaluate.py RESULT_JSON SCOPE_JSON EVALUATION_JSON
      Environment: COVERAGE (full | partial | none). Writes the evaluation.
  evaluate.py check-output EVALUATION_JSON COMMENT INLINE_JSON
      Scans what render.py would publish; on a hit the evaluation becomes
      "human" with withheld=true (a scan can only fail a run, never pass it).
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import contracts  # noqa: E402

MAX_FINDINGS = 30

# Known credential shapes, redacted from everything published. The last one
# over-redacts on purpose (see PROCESS.md, "The Pre-check comment").
SECRET_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_-]{8,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
    re.compile(r"(AKIA|ASIA)[A-Z0-9]{16}"),
    re.compile(r"xox[abpsr]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"[A-Za-z0-9+/_-]{80,}={0,2}"),
]
# What still looks like a credential after redaction withholds the result.
LEAK_PATTERNS = [
    # A secret-named key with a value that looks generated: letters and
    # digits, 12 or more characters, no dots or parentheses (so not code such
    # as `token = getToken()` or `process.env.SECRET`).
    re.compile(r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|client[_-]?secret|access[_-]?key)\b\s*[:=]\s*['\"]?(?=[A-Za-z0-9_+/-]*\d)(?=[A-Za-z0-9_+/-]*[A-Za-z])[A-Za-z0-9_+/-]{12,}"),
    re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^\s/:@]+:[^\s/@]+@"),
    re.compile(r"(?i)\bauthorization\s*:\s*(bearer|basic|token)\s+\S{8,}"),
    re.compile(r"\b(sk|rk|pk)_(live|test)_[A-Za-z0-9]{16,}"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}"),
]


def redact(text):
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[redacted]", text)
    return text


def leaks(text):
    return any(p.search(text) for p in LEAK_PATTERNS)


def model_texts(result):
    texts = [result["summary"]] + result["checked"] + result["not_checked"] + result["qa"]
    texts += [item for items in result["decisions"].values() for item in items]
    texts += [f["title"] + "\n" + f.get("body", "") for f in result["findings"]]
    return texts


def valid_result(result, schema):
    """The schema, without its display limit on findings (more findings than
    allowed is an outcome, not a malformed result)."""
    if not isinstance(result, dict):
        return False
    lenient = json.loads(json.dumps(schema))
    lenient["properties"]["findings"].pop("maxItems", None)
    return contracts.validate(result, lenient)


def human_reasons(scope, findings, coverage):
    reasons = []
    if scope["file_count"] > 0 and not scope["reviewed"]:
        reasons.append("no file of it could be reviewed")
    if scope["truncated"]:
        reasons.append("the pull request is too large for a full pre-check")
    if scope["unreviewable"]:
        reasons.append("some changes have no reviewable diff")
    if scope["workflow_changes"]:
        reasons.append("it changes CI workflows")
    if any(not p["path"].startswith((".github/workflows/", ".github/actions/")) for p in scope["human_paths"]):
        reasons.append("it changes code owners, dependencies or build configuration")
    if scope["cut_sources"]:
        reasons.append("some linked context was cut at its size limit")
    if scope["reviewed"] and coverage != "full":
        reasons.append("the reviewer did not read the whole diff")
    if len(findings) > MAX_FINDINGS:
        reasons.append("the reviewer returned more findings than allowed")
    return reasons


def evaluate(result, scope, coverage, result_schema, scope_schema):
    if not contracts.validate(scope, scope_schema):
        return {"outcome": "invalid", "reasons": ["the collected scope does not match its schema"],
                "blocking": 0, "advisory": 0, "total": 0, "withheld": False}
    if not valid_result(result, result_schema):
        return {"outcome": "invalid", "reasons": ["the reviewer returned no valid result"],
                "blocking": 0, "advisory": 0, "total": 0, "withheld": False}
    findings = result["findings"]
    blocking = sum(1 for f in findings if f["severity"] == "blocking")
    advisory = len(findings) - blocking
    reasons = human_reasons(scope, findings, coverage)
    withheld = any(leaks(redact(t)) for t in model_texts(result))
    if withheld:
        reasons.append("the reviewer's output contains text that looks like a credential")
    if blocking:
        outcome = "changes"
    elif reasons:
        outcome = "human"
    elif advisory:
        outcome = "advisory"
    else:
        outcome = "clean"
    if withheld:
        outcome = "human"
    return {"outcome": outcome, "reasons": reasons, "blocking": blocking, "advisory": advisory,
            "total": len(findings), "withheld": withheld}


def load_or_none(path):
    try:
        return contracts.load(path)
    except (OSError, ValueError):
        return None


def main(argv):
    if len(argv) == 5 and argv[1] == "check-output":
        evaluation = contracts.load(argv[2])
        with open(argv[3], encoding="utf-8") as fh:
            published = fh.read()
        published += "\n".join(item["body"] for item in contracts.load(argv[4]))
        if leaks(published):
            evaluation.update({"outcome": "human", "withheld": True})
            evaluation["reasons"].append("the rendered output contains text that looks like a credential")
            with open(argv[2], "w", encoding="utf-8") as fh:
                json.dump(evaluation, fh)
        return 0
    if len(argv) != 4:
        print(__doc__, file=sys.stderr)
        return 2
    result, scope = load_or_none(argv[1]), load_or_none(argv[2])
    coverage = os.environ.get("COVERAGE", "none")
    evaluation = evaluate(result, scope, coverage,
                          contracts.load(os.path.join(HERE, "schema.json")),
                          contracts.load(os.path.join(os.path.dirname(HERE), "context", "scope.schema.json")))
    assert evaluation["outcome"] in contracts.OUTCOMES
    with open(argv[3], "w", encoding="utf-8") as fh:
        json.dump(evaluation, fh)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
