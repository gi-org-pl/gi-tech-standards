# Front-end pre-check

Pre-check is an AI review that every front-end pull request gets before a person looks at it. It is a step of the
[code review](../../process/CODE_REVIEW.md) process, not a replacement for it, and it is **advisory**: the reviewer can be misled by
the content it reviews, so it never replaces a person's approval. Back end is out of scope.

## Why

With AI writing code fast, reading every line of a pull request is no longer a good use of a person's time. What a
person has to judge are the **decisions**: data structures, state management, API contracts, the specific behaviour a
user sees. Preferences about naming or about how code is split into files, which no standard defines, are not worth a
review round.

So after the implementing agent (or developer) finishes, a second, isolated AI checks the work: the code as such,
compliance with the standards, the design and the documentation, and the typical bugs. If it finds nothing to fix, it
says so and posts a short summary of the technical decisions the pull request makes. The functionality is still
tested in the normal QA process. Finally a person reads the pull request description and the summary of decisions,
and accepts the pull request or rejects it with suggestions.

## The flow

1. **Implementation.** A developer or an AI agent implements the issue and opens a pull request with a description
   that states decisions, deviations and verification, as the repository's guide asks.
2. **Pre-check.** When the pull request is opened, updated, reopened, marked ready for review, or its description or
   base branch changes, the reviewer runs:
   - real findings become inline comments, each with what is wrong, why and how to fix it, labelled with
     [conventional comments](../../process/CODE_REVIEW.md#conventional-comments) (`[blocking]` or `[non-blocking]`),
   - one comment headed **Pre-check** summarises the outcome and the technical decisions,
   - one label is set: `pre-check: no findings`, `pre-check: changes` or `pre-check: human review`,
   - the check `frontend-pre-check / review` passes only for "no findings"; it fails for changes needed and for a pull request
     the pre-check cannot judge.
3. **Fixes.** The author fixes the blocking findings and pushes. The pre-check runs again and updates the same
   Pre-check comment. A finding the author thinks is wrong is answered in its thread with the reason; the person
   reviewing decides.
4. **QA.** The functionality is tested by hand, guided by the "For QA" part of the summary.
5. **Decision.** A person reads the pull request description and the Pre-check summary, and accepts the pull request or
   rejects it with suggestions. Reading the code is the person's choice, not a duty.

## Outcomes

| Outcome | When | Label | `frontend-pre-check / review` |
| --- | --- | --- | --- |
| No findings | no blocking finding, and the whole pull request could be reviewed | `pre-check: no findings` | passes |
| Changes needed | at least one blocking finding | `pre-check: changes` | fails |
| Needs a person | the diff was cut off at the cap, a file is too large for GitHub to show its diff, or the pull request changes CI workflows, code owners or dependency resolution (lock files, `.npmrc`) | `pre-check: human review` | fails |
| Not finished | the reviewer failed, returned no valid result, or a file name contains a control character or a backtick | none | fails |
| Skipped | see [When it does not run](#when-it-does-not-run) | none | skipped (counts as passed) |

The labels keep the short `pre-check:` prefix; they are the one exception to "we do not use GitHub labels for pull
requests" in [code review](../../process/CODE_REVIEW.md).

**"No findings" is not "reviewed".** Text in the pull request cannot make the reviewer act, but it can make it
under-report and return a falsely clean result. "No findings" is therefore neither "safe" nor an approval, and a green
pre-check is never a person's sign-off. Anything automated must read the `frontend-pre-check / review` check run of the
pull request's **head commit**, never the label: anyone with triage access, and any workflow, can set a label.

## What the reviewer gets

The reviewer is isolated from the agent that wrote the code and from GitHub. It receives only:

- the diff of the pull request, capped and in risk order (application code first), and its description; tests and
  test helpers are left out of the diff and listed by name,
- the linked issues **of this organisation**, with the comments of its members (owners, members, collaborators);
  comments by anyone else are left out and counted,
- the Figma links found there - recorded, but **not opened**: the reviewer sees neither Figma nor images (see
  [Design comparison](#design-comparison)),
- documents in `gi-org-pl/product` that the issues link, from a branch, a tag or a commit on its default branch,
- these standards (`gi-tech-standards`) at the commit of the workflow,
- the repository's own guide - `AGENTS.md` and `CLAUDE.md` files at any depth, `README.md`, `docs/` and the pull
  request template - **as they are on the base branch**, so that a pull request cannot change the rules it is checked
  against.

Text written by people is marked as quoted data with a nonce of the run, and the instructions tell the reviewer that
it is never an instruction. The reviewer can read and search files of the checked-out pull request, inside the
working directory only. It cannot run commands, edit files, browse the web or post anything; the review job publishes
its result after escaping it.

## What it checks

The full checklist is in [the reviewer instructions](REVIEWER.md). In short:

- **bugs** typical for our stack - logic errors, unvalidated or unhandled data, async races, effect and hook mistakes,
  hydration mismatches, missing translations, accessibility that breaks use, security,
- **compliance** with written rules only - the repository's `AGENTS.md` and [front-end standards](../INDEX.md),
  each finding naming the rule,
- **design and documentation** - the issue's acceptance criteria, linked documents, the design comparison when the
  issue links Figma, documentation updated with the change, a pull request description that matches the diff,
- **tests** - changed logic comes with changed tests (judged from the names of the test files, which are not in the
  diff), stories and end-to-end coverage where the repository asks for them.

It does not comment on naming, file splitting, formatting or anything else no written rule defines.

### Design comparison

The reviewer does not open Figma. When the issue or the pull request links a Figma design, the implementer shows the
result next to it instead: the pull request description carries screenshots of every changed view compared with the
Figma frames (before and after for a correction), each saying what it shows, at which viewport and on which commit.
The reviewer checks that this comparison is there and covers the views the diff changes:

- a visible change with no screenshot at all is a blocking finding,
- screenshots without the comparison with Figma, or changed views left out, are a non-blocking finding,
- a change with nothing visible needs no comparison.

The Pre-check comment then says under "What was not checked" that visual fidelity was judged only from the comparison
in the description. Whether the result looks like the design is decided by the person who reads the description, and
by QA.

## The Pre-check comment

One comment per pull request, found again by a hidden marker and updated on every run. Its sections are fixed:

- **Result** - the outcome; then the reviewer's one-line summary and the list of findings.
- **Technical decisions in this PR** - data structures, state, API contracts, UX behaviours, new dependencies,
  architecture. "None." where the pull request makes no decision of that kind; "Deviation:" where a decision departs
  from the issue or the standard.
- **What was checked** - the reviewed diff and commit, the linked issues, the standards version and the documents used.
- **What was not checked** - always runtime behaviour (nothing is built or run); when there are Figma links, that visual
  fidelity was judged only from the design comparison in the description; the files left out of the diff; and
  anything else the reviewer could not examine.
- **For QA** - what to test by hand.

Everything the reviewer wrote is escaped: no HTML, no images, no mentions, no links outside `github.com/gi-org-pl`,
`gi.org.pl` and Figma (a link is checked after percent-decoding, so `..` segments cannot leave the allowlisted place),
no one-click suggestions, no line breaks in one-line fields, capped lengths, and strings that look like credentials are
redacted. `test_render.py` locks these rules in and runs in this repository's CI.

The redaction also replaces any run of 80 or more base64- or hex-like characters, because a token may come back
encoded. That is a conscious choice: it can hide a legitimate long hash or encoded blob quoted in a finding, but it
errs towards redacting too much, never too little. If false redactions get in the way, narrow it by an entropy
threshold (redact only runs whose character entropy is high), never by dropping it.

## When it does not run

The `frontend-pre-check / gate` job decides. It skips the review, green and with a notice, when:

- the event is a merge queue entry (`merge_group`) - the pull request was pre-checked already,
- the pull request comes from a fork - secrets are not available there,
- the pull request is a draft (it runs when it is marked ready for review),
- the secret `CLAUDE_CODE_OAUTH_TOKEN` is not set - the pre-check is not enabled,
- the pull request or the push comes from a bot (Dependabot and similar),
- the person who triggered the run has no write access.

A skipped `frontend-pre-check / review` job counts as passed for a required status check. Except for `merge_group`, a skip
also withdraws an earlier result - labels off, the Pre-check comment marked "not run for commit ..." - on a best-effort
basis; a person's approval is then the only check, as before the pre-check.

The gate **stops** a run, with a failing `frontend-pre-check / review`, when the pull request had more than
`max_runs_per_hour` runs in the last hour. If the gate itself fails, the review job runs anyway and fails, so a broken
gate cannot pass a required check. A run whose commit is no longer the head of the pull request publishes nothing.

## Limits and cost

The reviewer uses a Claude subscription through an OAuth token, with the same limits as the rest of the AI work done
on that subscription. The workflow keeps one review small:

| Setting | Default | Input |
| --- | --- | --- |
| Model | `sonnet` | `model` |
| Maximum agent turns | 60 | `max_turns` |
| Reviewed diff | 3000 changed lines, in risk order; more needs a person | `max_diff_lines` |
| Files left out of the diff | tests (`*.test.ts(x)`, `*.spec.ts(x)`, `__tests__/`, top-level `e2e/`), test helpers (`__mocks__/`, `*.fixture(s).ts`, `setupTests.ts`, `src/utils/vitest/`), snapshots, lock files (a lock file change still needs a person) | `exclude_paths` |
| Review timeout | 20 minutes (at most 50; the job stops at 60) | `timeout_minutes` |
| Runs per pull request | 8 in the last hour | `max_runs_per_hour` |

A burst of events on one pull request is debounced: an edit waits 30 seconds, and a newer event cancels the waiting
gate and a review that is still running. GitHub lists at most 3000 files of a pull request; the files beyond that
count as not reviewed. The number of turns, the duration, the tokens, the permission denials and the API-price
estimate of each run are in the summary of the run (on a subscription the estimate is not money spent).

If a run does not finish - most often because the subscription limit is reached - the Pre-check comment says so and
the check fails; re-run it later.

## Setting it up in a repository

The workflow is reusable: it lives here, in [`.github/workflows/frontend-pre-check.yml`](../../../.github/workflows/frontend-pre-check.yml),
with its scripts in [`.github/frontend-pre-check/`](../../../.github/frontend-pre-check/). A repository calls it with a short workflow:

```yaml
name: frontend-pre-check

on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review, converted_to_draft, edited]
  merge_group:

permissions: {}

jobs:
  frontend-pre-check:
    name: frontend-pre-check
    if: github.event.action != 'edited' || github.event.changes.body != null || github.event.changes.base != null
    permissions:
      contents: read
      pull-requests: write
      issues: write
      actions: read
    uses: gi-org-pl/gi-tech-standards/.github/workflows/frontend-pre-check.yml@<full commit SHA> # main on <date>
    secrets:
      CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
```

- **Pin a full commit SHA** of `main` in `uses:`. The workflow takes its scripts and the reviewer instructions from
  the same commit (`job.workflow_sha`), so the SHA pins all of it, and a later change here reaches a repository only
  when its caller is bumped in a reviewed pull request.
- **`edited` with the job's `if`** re-runs the pre-check when the description changes - it carries the design
  comparison - or the pull request gets a new base branch; edits of the title alone start nothing. The filter sits in
  the caller on purpose: a run skipped there creates no `frontend-pre-check / review` check, so it cannot replace the last
  result, while a review skipped by the gate would count as passed.
- **`converted_to_draft`** withdraws the result when a pull request goes back to draft.
- **`merge_group`** keeps a required `frontend-pre-check / review` from blocking a merge queue.
- **`actions: read`** lets the gate count the runs of the last hour.

## Approval

The pre-check never approves. Its label and its check inform; a person accepts:

- the bot account that opens pull requests cannot approve its own pull requests,
- an approval submitted with the workflow token would come from `github-actions[bot]`, could be forged by any workflow
  in the repository, and never counts as a code owner's review. The pre-check does not submit one.

The options, from the simplest:

1. **Required status check** `frontend-pre-check / review` plus the existing human approval (recommended): nothing merges with
   unresolved blocking findings or with changes the pre-check cannot judge, and a person still accepts the pull
   request. A pull request that needs a person (CI, lock files, too large) then also needs someone with the right to
   bypass the ruleset, or a split into smaller pull requests.
2. **Label only**: the check is not required; the label and the summary inform the person, who decides.

A blocking finding that the person reviewing considers wrong is resolved by that person: either the author changes the
code anyway, or someone with the right to bypass the ruleset merges.

## Security

### Threat model

Three kinds of actors matter:

1. **Anyone with write access to the repository.** Under `pull_request`, the caller workflow is read from the pull
   request's merge ref. A writer can change the caller's inputs, add a job named `review`, or add a step that prints
   `CLAUDE_CODE_OAUTH_TOKEN`. Nothing inside the reusable workflow can prevent that; it is handled by the settings
   below.
2. **Outsiders who write text the reviewer reads.** Anyone on GitHub can comment on a public issue. The pre-check reads
   only issues of this organisation and only their members' comments; the pull request description, the diff, linked
   documents and file names remain attacker-influenced input. The reviewer has nothing to leak them with: a read-only
   token, read tools confined to the workspace, no shell, no web, no posting.
3. **Whoever can push to `main` of gi-tech-standards.** A caller that pins a commit SHA runs only what was pinned; one
   that uses a branch runs whatever lands there.

### What the workflow does

- **No job holds both the secret and a write token.** `analyse` has the secret and a read-only token; `review` has a
  write token and neither the secret nor code of the pull request; `gate` has neither the secret nor a checkout of the
  pull request. `GH_TOKEN` is set only on the steps that call `gh`; the action uses the read-only token.
- **The reviewer cannot publish.** It has `Read` (confined to `./**`, with the runner's `/proc`, temp, tool and home
  configuration paths and `.git/` denied), `Glob` and `Grep`; no MCP servers (`--strict-mcp-config`), no hooks
  (`disableAllHooks`), no project or local settings (`--setting-sources user`), the default permission mode. Its
  findings come back as structured output; `render.py` escapes them and `report.sh` posts them.
- **Nothing from the pull request runs.** The scripts and instructions come from gi-tech-standards at
  `job.workflow_sha`. After the checkout every symbolic link is deleted, and so are `CLAUDE.md`, `CLAUDE.local.md`,
  `AGENTS.md`, `.claude/`, `.mcp.json` and `.claude.json` at any depth; the action restores the root ones from the base
  branch, and with `--setting-sources user` and `--strict-mcp-config` they are not loaded anyway.
- **Context comes from the API only, never from the checkout**, with paths and refs validated (no `.` or `..`
  segments, a plain character set, `realpath` under the target directory), issue references limited to this
  organisation, comment authors limited to its members, and sizes capped per comment, issue, document and patch. A
  file name with a control character or a backtick stops the run.
- **No false passes.** The outcome is derived from the findings and the scope, never taken from the reviewer: a cut-off
  diff, a file too large to show, or a change to CI, code owners or dependency resolution needs a person.
- **Escaped output.** See [The Pre-check comment](#the-pre-check-comment). Nothing the reviewer wrote reaches a workflow
  command or the log; the execution log is not uploaded, and only usage numbers leave the job.
- **Every action is pinned by a full commit SHA** (`actions/checkout`, `anthropics/claude-code-action`; the latter pins
  its own dependencies and the Claude Code version).
- **Inputs are validated** in the gate: the model name, numbers within ranges, plain glob characters, document
  repositories of the same organisation.

Evidence from `anthropics/claude-code-action` at the pinned commit (v1.0.254): in automation mode (a `prompt` on a
`pull_request` event) it adds an MCP server only for tools named in `--allowedTools` (`github_comment`,
`github_inline_comment`, `github_ci`) or for commit signing, none of which apply here; it passes no
`--permission-mode` in this mode (tag mode uses `acceptEdits`); with `github_token` given it uses that token and asks
for no OIDC token, and it removes the OIDC request variables from the CLI's environment. It does write
`enableAllProjectMcpServers: true` into the user settings, which `--strict-mcp-config` overrides. Check on the first
real run that the job summary shows zero permission denials of expected reads and that the review finished.

### What an organisation owner sets

These are not code. Without them a writer can bypass the pre-check, or read the secret:

1. **Require a person's approval.** Repository → Settings → Rules → Rulesets → the ruleset of `main` → "Require a pull
   request before merging" with at least one approval, "Dismiss stale pull request approvals when new commits are
   pushed" and "Require approval of the most recent reviewable push". The pre-check never replaces this.
2. **Protect CI configuration.** Add `.github/CODEOWNERS` with `/.github/ @gi-org-pl/admins` to each repository, and
   turn on "Require review from Code Owners" in the same ruleset, so a change to the caller needs an admin.
3. **Protect gi-tech-standards.** Its `main` already requires a code owner's review for `.github/` (owned by the
   admins) and squash merges only; keep it so, and add "Require approval of the most recent reviewable push" there too.
   Pin callers to a commit SHA and bump them in reviewed pull requests.
4. **Limit the secret.** Organisation → Settings → Secrets and variables → Actions → `CLAUDE_CODE_OAUTH_TOKEN` →
   Repository access: "Selected repositories", only the repositories that run the pre-check. Rotate the token
   (`claude setup-token`) when someone with write access leaves.
5. **Stronger: keep the secret in an environment.** Repository → Settings → Environments → New environment
   `pre-check` → Environment secrets: `CLAUDE_CODE_OAUTH_TOKEN`, then delete the organisation secret. With "Required
   reviewers" on the environment, no job - including one a writer adds in a pull request - gets the token without an
   approval; the price is approving every run. Deployment-branch rules alone do not help here, because pull request
   runs are not on a protected branch. The `analyse` job needs one line (`environment: pre-check`) for this; ask for it
   when you decide.
6. **Forks.** Organisation → Settings → Actions → General → "Approval for running fork pull request workflows from
   contributors": "Require approval for all external contributors". Fork runs never get secrets on public
   repositories; this also stops them from using runner time unasked.
7. **Allowed actions.** Organisation → Settings → Actions → General → Policies: allow `anthropics/claude-code-action`,
   `actions/checkout` and reusable workflows from `gi-org-pl/gi-tech-standards`.
8. **Read the right signal.** Automation that depends on the pre-check reads the `frontend-pre-check / review` check run
   of the head commit, never the label, and nobody treats a green pre-check as a sign-off.
9. **Re-audit on every bump of the action.** The secret stays safe because of the reviewer's sandbox in `analyse`: the
   `Read` scope and denylist (`/proc`, `~/.ssh`, `~/.claude*`, `/tmp`, runner temp and tools, `.git/`), no shell, no web,
   no MCP servers, with the redaction in `render.py` only as a backstop. When the pinned SHA of
   `anthropics/claude-code-action` (or the Claude Code version it installs) is bumped, check again in its source and in
   the first run's log which tools, MCP servers, settings sources and permission mode it uses, and whether the
   denylist still covers where it keeps prompts, logs and credentials.

**Required workflows.** An organisation ruleset that requires a workflow would run the pre-check without a caller file
in the repository, so a pull request could not edit it. GitHub offers that rule ("Require workflows to pass before
merging") to GitHub Enterprise Cloud organisations; gi-org-pl is on the Team plan, so the repositories keep their
callers and the settings above. Should the plan change, the caller's content moves into a workflow in this repository
that the ruleset points at, pinned by SHA.

## Files

| File | What it is |
| --- | --- |
| [`docs/frontend/pre-check/REVIEWER.md`](REVIEWER.md) | The reviewer's instructions and checklist, used word for word as its prompt |
| [`.github/workflows/frontend-pre-check.yml`](../../../.github/workflows/frontend-pre-check.yml) | The reusable workflow (`workflow_call`) |
| [`.github/frontend-pre-check/collect-context.sh`](../../../.github/frontend-pre-check/collect-context.sh) | Collects what the reviewer may read, from the API |
| [`.github/frontend-pre-check/result.schema.json`](../../../.github/frontend-pre-check/result.schema.json) | The structured result the reviewer returns |
| [`.github/frontend-pre-check/render.py`](../../../.github/frontend-pre-check/render.py) | Validates and escapes the result, derives the outcome |
| [`.github/frontend-pre-check/test_render.py`](../../../.github/frontend-pre-check/test_render.py) | Tests of the escaping, run in CI |
| [`.github/frontend-pre-check/report.sh`](../../../.github/frontend-pre-check/report.sh) | Posts the Pre-check comment and the inline comments, sets the label and the status |
