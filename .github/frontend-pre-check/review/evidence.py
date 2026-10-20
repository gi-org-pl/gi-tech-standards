#!/usr/bin/env python3
"""Deterministic evidence from the reviewer's own log (the action's execution
file, which is not uploaded): whether it read every line of diff.patch, which
tools the session had, and the usage numbers.

Usage: evidence.py EXECUTION_FILE DIFF_PATCH
Writes coverage= (full | partial | none), tools= and usage= to GITHUB_OUTPUT.
Only a fixed word, tool names and numbers leave the job.
"""

import json
import os
import re
import sys

DEFAULT_LIMIT = 2000  # lines the Read tool returns without a limit


def coverage(messages, diff_path, lines):
    """full when the Read calls on DIFF_PATH cover lines 1..LINES."""
    if lines == 0:
        return "full"
    ranges = []
    for message in messages:
        if message.get("type") != "assistant":
            continue
        for block in (message.get("message") or {}).get("content") or []:
            if not isinstance(block, dict) or block.get("type") != "tool_use" or block.get("name") != "Read":
                continue
            data = block.get("input") or {}
            if data.get("file_path") != diff_path:
                continue
            start = data.get("offset") or 1
            limit = data.get("limit") or DEFAULT_LIMIT
            if isinstance(start, int) and isinstance(limit, int) and start >= 1 and limit >= 1:
                ranges.append((start, start + limit - 1))
    if not ranges:
        return "none"
    end = 0
    for start, stop in sorted(ranges):
        if start > end + 1:
            return "partial"
        end = max(end, stop)
    return "full" if end >= lines else "partial"


def tools(messages):
    for message in messages:
        if message.get("type") == "system" and message.get("subtype") == "init":
            names = [t for t in message.get("tools") or [] if isinstance(t, str) and re.match(r"^[A-Za-z0-9_:-]{1,64}$", t)]
            return ",".join(names)
    return ""


def usage(messages):
    results = [m for m in messages if m.get("type") == "result"]
    if not results:
        return {}
    last = results[-1]
    raw = last.get("usage") or {}

    def number(value):
        return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None

    return {
        "num_turns": number(last.get("num_turns")),
        "duration_ms": number(last.get("duration_ms")),
        "total_cost_usd": number(last.get("total_cost_usd")),
        "permission_denials_count": len(last.get("permission_denials") or []),
        "usage": {key: number(raw.get(key)) for key in
                  ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")},
    }


def main(argv):
    execution_file, diff_path = argv[1:3]
    try:
        with open(execution_file, encoding="utf-8") as fh:
            messages = json.load(fh)
    except (OSError, ValueError):
        messages = []
    try:
        with open(diff_path, encoding="utf-8") as fh:
            lines = sum(1 for _ in fh)
    except OSError:
        lines = 0
    messages = [m for m in messages if isinstance(m, dict)] if isinstance(messages, list) else []
    values = {"coverage": coverage(messages, diff_path, lines), "tools": tools(messages), "usage": json.dumps(usage(messages))}
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
        for key, value in values.items():
            fh.write("{}={}\n".format(key, value))
    print("Diff read: {}. Tools available: {}. Usage: {}".format(values["coverage"], values["tools"], values["usage"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
