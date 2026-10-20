#!/usr/bin/env python3
"""The gate of the front-end pre-check: checks the inputs and decides.

In Python rather than Bash because it is decision logic - input shapes, the
eligibility rules, the run limit - and tests/test_gate.py exercises every
branch of it without GitHub.

Verdicts (written to GITHUB_OUTPUT as verdict= and reason=):
  run     review the pull request
  queue   a merge queue entry; the review job checks its pull requests
  skip    not pre-checked (fork, draft, no secret, bot, no write access, other
          event); the review job FAILS - a skip is never a green check
  block   over the hourly run limit; the review job fails as well
An invalid input exits 1, which fails the review job too.
"""

import datetime
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "context"))

import github  # noqa: E402


class Invalid(Exception):
    pass


def in_range(value, low, high):
    return bool(re.match(r"^[0-9]{1,6}$", value or "")) and low <= int(value) <= high


def check_inputs(env):
    repo_owner = env.get("REPO", "").split("/")[0]
    if not re.match(r"^[A-Za-z0-9._-]{1,64}$", env.get("MODEL", "")):
        raise Invalid("model")
    for key, low, high in (("MAX_TURNS", 1, 200), ("MAX_DIFF_LINES", 100, 20000), ("TIMEOUT", 1, 50), ("MAX_RUNS", 1, 60)):
        if not in_range(env.get(key), low, high):
            raise Invalid(key.lower())
    for pattern in env.get("EXCLUDE_PATHS", "").splitlines():
        if pattern and not re.match(r"^[A-Za-z0-9._*/-]{1,200}$", pattern):
            raise Invalid("exclude_paths")
    for repo in env.get("DOC_REPOS", "").splitlines():
        if repo and not re.match(r"^{}/[A-Za-z0-9._-]+$".format(re.escape(repo_owner)), repo):
            raise Invalid("doc_repos")
    if not re.match(r"^[0-9a-f]{40}$", env.get("WORKFLOW_SHA", "")):
        raise Invalid("job.workflow_sha is empty; the scripts cannot be pinned")
    workflow_repository = env.get("WORKFLOW_REPOSITORY", "")
    if not re.match(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", workflow_repository) or any(
            part in (".", "..") for part in workflow_repository.split("/")):
        raise Invalid("job.workflow_repository")


def runs_last_hour(gh, env, now):
    """Runs of this caller workflow for this pull request in the last hour,
    over every page, not counting runs the caller's own `if` skipped."""
    repo, caller = env["REPO"], env.get("CALLER_REF", "")
    path = caller[len(repo) + 1:] if caller.startswith(repo + "/") else caller
    path = path.split("@")[0]
    if not re.match(r"^[A-Za-z0-9._/-]+$", path):
        return 0
    since = (now - datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    branch = re.sub(r"[^A-Za-z0-9._/-]", lambda m: "%{:02X}".format(ord(m.group(0))), env.get("HEAD_REF", ""))
    pages = gh.api("repos/{}/actions/runs?event=pull_request&branch={}&created=%3E%3D{}&per_page=100".format(repo, branch, since), paginate=True)
    number = int(env["PR_NUMBER"])
    count = 0
    for page in pages:
        for run in page.get("workflow_runs", []):
            if run.get("path") == path and run.get("conclusion") != "skipped" and any(
                    p.get("number") == number for p in run.get("pull_requests") or []):
                count += 1
    return count


def decide(gh, env, now=None, sleep=time.sleep):
    """Returns (verdict, reason)."""
    event = env.get("EVENT", "")
    if event == "merge_group":
        return "queue", "a merge queue entry; its pull requests must have passed the pre-check on their heads."
    if event != "pull_request":
        return "skip", "the event is {}, which the pre-check does not review.".format(re.sub(r"[^a-z_]", "", event))
    if env.get("HEAD_REPO") != env.get("REPO"):
        return "skip", "the pull request comes from a fork, where secrets are not available."
    if env.get("DRAFT") == "true":
        return "skip", "the pull request is a draft; it is reviewed when it is marked ready for review."
    if env.get("HAS_TOKEN") != "true":
        return "skip", "the secret CLAUDE_CODE_OAUTH_TOKEN is not available to this repository."
    if env.get("AUTHOR_TYPE") == "Bot" or env.get("ACTOR", "").endswith("[bot]"):
        return "skip", "the pull request or the push comes from a bot."
    # Cost control, not a trust boundary: the actor only triggered the event;
    # the content may come from anyone.
    try:
        permission = gh.api("repos/{}/collaborators/{}/permission".format(env["REPO"], env.get("ACTOR", ""))).get("permission")
    except github.GitHubError:
        permission = "unknown"
    if permission not in ("admin", "write"):
        return "skip", "the person who triggered the run has no write access."
    if env.get("ACTION") == "edited":
        sleep(30)  # debounce: a newer edit within this time cancels this gate
    try:
        runs = runs_last_hour(gh, env, now or datetime.datetime.now(datetime.timezone.utc))
    except github.GitHubError:
        runs = 0  # the limit is cost control; an API failure does not block a review
    limit = int(env["MAX_RUNS"])
    if runs > limit:
        return "block", "this pull request had {} pre-check runs in the last hour, more than {}; re-run the job later.".format(runs, limit)
    return "run", "reviewing."


def main():
    env = dict(os.environ)
    try:
        check_inputs(env)
    except Invalid as name:
        print("::error title=Pre-check::Invalid setting: {}".format(name))
        return 1
    verdict, reason = decide(github, env)
    print("::notice title=Pre-check::" + reason)
    with open(env["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
        fh.write("verdict={}\nreason={}\n".format(verdict, reason))
    if env.get("GITHUB_STEP_SUMMARY"):
        with open(env["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fh:
            fh.write("Pre-check: {}\n".format(reason))
    return 0


if __name__ == "__main__":
    sys.exit(main())
