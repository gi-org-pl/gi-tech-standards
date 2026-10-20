"""The text context of a review: the pull request description, linked issues,
linked documents and the repository's guide.

All of it is untrusted, whoever wrote it. What people wrote is wrapped in
quoted-data markers with a nonce its author cannot know (provenance, not a
security boundary); only issues of the organisation and only what its members
wrote are used; documents come only from the default branch of an allowed
repository, pinned to a commit; every cut at a size limit is recorded.
"""

import os
import re

from github import GitHubError

TRUSTED = {"OWNER", "MEMBER", "COLLABORATOR"}
MAX_ISSUES = 5
MAX_COMMENTS = 50
MAX_COMMENT_CHARS = 8000
MAX_ISSUE_BYTES = 60000
MAX_BODY_BYTES = 60000
MAX_DOC_FILES = 20
MAX_FILE_BYTES = 200000
MAX_GUIDE_DOCS = 40
SEGMENT = re.compile(r"^[A-Za-z0-9._-]+$")
NAME = re.compile(r"^[A-Za-z0-9_.-]+$")
GUIDE = re.compile(r"(^|/)(AGENTS|CLAUDE)\.md$|^(README\.md|CONTRIBUTING\.md|docs/.*\.mdx?|\.github/pull_request_template\.md)$")
FIGMA = re.compile(r"https://([a-z]+\.)?figma\.com/[A-Za-z0-9._~/?=&%:+-]+")


class Context:
    """Collects notes and cut sources while the pieces are gathered."""

    def __init__(self, nonce):
        self.nonce = nonce
        self.notes = []
        self.cut_sources = []

    def quote(self, label, data, limit):
        if isinstance(data, str):
            data = data.encode("utf-8")
        if len(data) > limit:
            self.cut_sources.append(label)
            data = data[:limit]
        text = data.decode("utf-8", errors="ignore")  # a cut never leaves half a character
        return "BEGIN QUOTED DATA {} ({})\n{}\nEND QUOTED DATA {}\n".format(self.nonce, label, text, self.nonce)


def safe_relpath(path):
    """A plain relative path: no empty, "." or ".." segment, no leading slash
    or backslash, a plain character set."""
    if not isinstance(path, str) or not path or path.startswith("/") or "\\" in path:
        return False
    return all(SEGMENT.match(s) and s not in (".", "..") for s in path.split("/"))


def inside(target, base):
    target, base = os.path.realpath(target), os.path.realpath(base)
    return target.startswith(base + os.sep)


def issue_refs(body, closing, repo):
    """Candidate references, closing references first, in order, unique."""
    found = list(closing)
    found += ["{}#{}".format(m.group(1), m.group(2)) for m in
              re.finditer(r"https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/([0-9]+)", body)]
    for m in re.finditer(r"(?:^|[^A-Za-z0-9_/.-])((?:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)?)#([0-9]+)", body):
        found.append("{}#{}".format(m.group(1) or repo, m.group(2)))
    seen, out = set(), []
    for ref in found:
        if ref not in seen:
            seen.add(ref)
            out.append(ref)
    return out


def valid_ref(ref, owner):
    match = re.match(r"^([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)#([0-9]{1,7})$", ref)
    if not match:
        return False
    ref_owner, name, _ = match.groups()
    return ref_owner == owner and NAME.match(name) and name not in (".", "..")


def collect_issues(gh, ctx, refs, owner, out_dir):
    """Writes the issues to OUT_DIR, returns (issue refs, text to search for links)."""
    issues, not_read, outside, links = [], [], 0, ""
    for ref in refs:
        if not valid_ref(ref, owner):
            continue
        if len(issues) >= MAX_ISSUES:
            not_read.append(ref)
            continue
        repo, number = ref.split("#")
        try:
            issue = gh.api("repos/{}/issues/{}".format(repo, number))
        except GitHubError:
            ctx.notes.append("Could not read the linked issue {}.".format(ref))
            continue
        if "pull_request" in issue:
            continue
        try:
            comments = gh.api("repos/{}/issues/{}/comments?per_page=100".format(repo, number), paginate=True)
        except GitHubError:
            comments = []
            ctx.notes.append("Could not read the comments of {}.".format(ref))
        trusted = [c for c in comments if c.get("author_association") in TRUSTED]
        outside += len(comments) - len(trusted)
        if issue.get("author_association") in TRUSTED:
            text = "Title: {}\nState: {}\n\n{}".format(issue.get("title", ""), issue.get("state", ""), issue.get("body") or "(empty)")
        else:
            text = "State: {}\n\n(The issue was opened by someone outside the organisation; its title and description are left out.)".format(issue.get("state", ""))
        cut_comments = len(trusted) > MAX_COMMENTS
        for c in trusted[:MAX_COMMENTS]:
            body = c.get("body") or ""
            if len(body) > MAX_COMMENT_CHARS:
                body, cut_comments = body[:MAX_COMMENT_CHARS] + "\n(cut)", True
            text += "\n\n--- Comment by {} ({}), {}\n\n{}".format(
                c.get("user", {}).get("login", ""), c.get("author_association", ""), c.get("created_at", ""), body)
        if cut_comments:
            ctx.cut_sources.append("comments of issue {}".format(ref))
        name = "{}-{}.md".format(repo.replace("/", "-"), number)
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as fh:
            fh.write("# Issue {}\n\n".format(ref) + ctx.quote("issue " + ref, text, MAX_ISSUE_BYTES))
        issues.append(ref)
        links += "\n" + text[:MAX_ISSUE_BYTES]
    if not_read:
        ctx.notes.append("Only the first {} linked issues were read; these further references were not: {}.".format(MAX_ISSUES, " ".join(not_read)))
    if outside:
        ctx.notes.append("{} comment(s) on the linked issues by people outside the organisation were left out.".format(outside))
    return issues, links


def figma_links(text):
    seen, out = set(), []
    for m in FIGMA.finditer(text):
        if m.group(0) not in seen:
            seen.add(m.group(0))
            out.append(m.group(0))
    return out[:20]


def resolve_ref(gh, repo, ref, cache):
    """The commit of REF if it is the default branch or a commit on it."""
    if repo not in cache:
        branch = gh.api("repos/{}".format(repo))["default_branch"]
        cache[repo] = (branch, gh.api("repos/{}/commits/{}".format(repo, branch))["sha"])
    branch, sha = cache[repo]
    if ref == branch:
        return sha
    if re.match(r"^[0-9a-f]{7,40}$", ref):
        status = gh.api("repos/{}/compare/{}...{}".format(repo, ref, sha)).get("status")
        if status in ("ahead", "identical"):
            return ref
    return None


def collect_documents(gh, ctx, text, doc_repos, owner, out_dir):
    docs, skipped, cache = [], [], {}

    def fetch(repo, sha, path):
        if len(docs) >= MAX_DOC_FILES:
            skipped.append("{}/{}".format(repo, path))
            return
        target = os.path.join(out_dir, repo, path)
        if not safe_relpath(path) or not inside(target, out_dir):
            ctx.notes.append("A linked document path was rejected as unsafe.")
            return
        try:
            data = gh.raw("repos/{}/contents/{}?ref={}".format(repo, path, sha))
        except GitHubError:
            ctx.notes.append("Could not read the linked document {}/{}.".format(repo, path))
            return
        os.makedirs(os.path.dirname(target), exist_ok=True)
        label = "document {}/{} at {}".format(repo, path, sha[:7])
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(ctx.quote(label, data, MAX_FILE_BYTES))
        docs.append("{}/{}@{}".format(repo, path, sha[:7]))

    for repo in doc_repos:
        if not re.match(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", repo) or repo.split("/")[0] != owner:
            continue
        seen = set()
        for m in re.finditer(r"https://github\.com/{}/(blob|tree)/([A-Za-z0-9._/-]+)".format(re.escape(repo)), text):
            if m.group(0) in seen:
                continue
            seen.add(m.group(0))
            kind, rest = m.group(1), m.group(2)
            if "/" not in rest:
                continue
            ref, path = rest.split("/", 1)
            try:
                sha = resolve_ref(gh, repo, ref, cache) if safe_relpath(ref) and safe_relpath(path) else None
            except GitHubError:
                sha = None
            if not sha:
                ctx.notes.append("A linked document outside the default branch, or with an unsafe path, was skipped.")
                continue
            if kind == "blob":
                fetch(repo, sha, path)
                continue
            try:
                entries = gh.api("repos/{}/contents/{}?ref={}".format(repo, path, sha))
            except GitHubError:
                entries = []
            for entry in entries if isinstance(entries, list) else []:
                if entry.get("type") == "file" and re.search(r"\.(md|mdx|txt)$", entry.get("name", "")):
                    fetch(repo, sha, entry["path"])
    if skipped:
        ctx.notes.append("Only the first {} linked documents were read; not read: {}.".format(MAX_DOC_FILES, " ".join(skipped)))
    return docs


def collect_guide(gh, ctx, repo, base_sha, out_dir):
    """The repository's guide at the base commit: every AGENTS.md and CLAUDE.md,
    then at most MAX_GUIDE_DOCS other documents."""
    tree = gh.api("repos/{}/git/trees/{}?recursive=1".format(repo, base_sha))
    if tree.get("truncated"):
        ctx.cut_sources.append("the file list of the base branch")
    guide, others, skipped = [], 0, 0
    for item in tree.get("tree", []):
        path = item.get("path", "")
        if item.get("type") != "blob" or not GUIDE.search(path) or not safe_relpath(path):
            continue
        if not re.search(r"(^|/)(AGENTS|CLAUDE)\.md$", path):
            if others >= MAX_GUIDE_DOCS:
                skipped += 1
                continue
            others += 1
        target = os.path.join(out_dir, path)
        if not inside(target, out_dir):
            continue
        try:
            data = gh.raw("repos/{}/contents/{}?ref={}".format(repo, path, base_sha))
        except GitHubError:
            continue
        if len(data) > MAX_FILE_BYTES:
            ctx.cut_sources.append("repository guide " + path)
            data = data[:MAX_FILE_BYTES]
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as fh:
            fh.write(data)
        guide.append(path)
    if skipped:
        ctx.notes.append("Only {} documents of the repository guide besides AGENTS.md and CLAUDE.md were read; {} more were not.".format(MAX_GUIDE_DOCS, skipped))
    return guide
