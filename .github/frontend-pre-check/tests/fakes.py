"""Shared test helpers: import paths and a fake of context/github.py."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ("", "context", "review"):
    path = os.path.join(ROOT, sub)
    if path not in sys.path:
        sys.path.insert(0, path)

import github  # noqa: E402

GitHubError = github.GitHubError


class FakeGitHub:
    """Answers api()/raw() from ROUTES: {path or path prefix: value}. A value
    that is an Exception is raised; a missing route raises GitHubError."""

    def __init__(self, routes, raw=None):
        self.routes = routes
        self.raws = raw or {}
        self.calls = []

    def _find(self, table, path):
        if path in table:
            return table[path]
        for key, value in table.items():
            if key.endswith("*") and path.startswith(key[:-1]):
                return value
        raise GitHubError("no route for " + path)

    def api(self, path, paginate=False, fields=None):
        self.calls.append(path)
        value = self._find(self.routes, path)
        if isinstance(value, Exception):
            raise value
        return value

    def raw(self, path):
        self.calls.append("raw " + path)
        value = self._find(self.raws, path)
        if isinstance(value, Exception):
            raise value
        return value if isinstance(value, bytes) else value.encode("utf-8")
