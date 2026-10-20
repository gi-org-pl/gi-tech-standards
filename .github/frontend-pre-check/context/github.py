"""A thin wrapper around `gh api`, the only way the pre-check talks to GitHub.

The token comes from GH_TOKEN in the environment of the step. Tests replace
`run` to feed fixtures and to simulate API failures.
"""

import json
import subprocess


class GitHubError(Exception):
    pass


def run(args):
    """Runs gh with ARGS and returns stdout as bytes; raises GitHubError."""
    try:
        done = subprocess.run(["gh"] + list(args), capture_output=True, check=False)
    except OSError as error:
        raise GitHubError(str(error)) from error
    if done.returncode != 0:
        raise GitHubError("gh api call failed")
    return done.stdout


def api(path, paginate=False, fields=None):
    """GET, or a GraphQL query with FIELDS, parsed as JSON. With PAGINATE, the
    pages of a list are joined into one list."""
    args = ["api"] + (["--paginate"] if paginate else []) + [path]
    for key, value in (fields or {}).items():
        args += ["-F" if isinstance(value, int) else "-f", "{}={}".format(key, value)]
    text = run(args).decode("utf-8", errors="replace").strip()
    if not paginate:
        return json.loads(text) if text else None
    decoder, items, index = json.JSONDecoder(), [], 0
    while index < len(text):
        value, index = decoder.raw_decode(text, index)
        items += value if isinstance(value, list) else [value]
        while index < len(text) and text[index].isspace():
            index += 1
    return items


def raw(path):
    """The raw content of a file from the contents API, as bytes."""
    return run(["api", path, "-H", "Accept: application/vnd.github.raw"])
