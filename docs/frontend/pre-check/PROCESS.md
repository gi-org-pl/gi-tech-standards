# Front-end pre-check

Pre-check is an AI review that every front-end pull request gets before a person looks at it. It is a step of the
[code review](../../process/CODE_REVIEW.md) process, not a replacement for it, and it is **advisory**: the reviewer
can be misled by the content it reviews or simply miss things, so it never replaces a person's approval. Back end is
out of scope.

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
   - one comment headed **Pre-check** holds the outcome, **every finding with its full explanation**, labelled with
     [conventional comments](../../process/CODE_REVIEW.md#conventional-comments) (`[blocking]` or `[non-blocking]`),
     and the technical decisions; findings on lines of the diff are also posted as inline comments, for convenience,
   - one label is set (see [Outcomes](#outcomes)),
   - the check `frontend-pre-check / review` passes only for "clean" and "advisory".
3. **Fixes.** The author fixes the blocking findings and pushes. The pre-check runs again and updates the same
   Pre-check comment. A finding the author thinks is wrong is answered with the reason; the person reviewing decides.
4. **QA.** The functionality is tested by hand, guided by the "For QA" part of the summary.
5. **Decision.** A person reads the pull request description and the Pre-check summary, and accepts the pull request or
   rejects it with suggestions. Reading the code is the person's choice, not a duty.

## Outcomes

`frontend-pre-check / review` runs for every event and is the check to require. It passes only in the first three
rows; every other outcome, a skip included, fails it.

| Outcome | When | Label | Check |
| --- | --- | --- | --- |
| Clean | no findings, and the whole pull request was deterministically covered | `pre-check: clean` | passes |
| Advisory | only non-blocking findings, and the whole pull request was covered | `pre-check: advisory` | passes |
| Merge queue | a `merge_group` entry whose pull requests passed this check on their current heads | none | passes |
| Changes needed | at least one blocking finding, anywhere in the reviewer's list | `pre-check: changes` | fails |
| Needs a person | see the list below | `pre-check: human review` | fails |
| Withheld | the reviewer's output contains text that looks like a credential; nothing of it is published | `pre-check: human review` | fails |
| Not pre-checked | a fork, a draft, a bot, an actor without write access, no secret, or the hourly run limit | none | fails |
| Not finished | the reviewer failed, returned no valid result, an exclusion is outside the policy, or a file name contains a control character or a backtick | none | fails |

A pull request **needs a person** when any of these holds - each is decided by a rule, not by the model:

- no changed file could be reviewed, or the diff was cut at the cap, or GitHub did not list all files,
- a change has no reviewable diff: a binary or empty file (raster images excepted), a file too large to show, a mode or
  type change, a rename or copy without a diff,
- a changed path, old or new, is CI (`.github/workflows/`, `.github/actions/`), code owners (any supported
  `CODEOWNERS` location), a dependency manifest or lock file (`package.json`, npm, Yarn, pnpm, Bun), package-manager
  configuration, plugins or hooks, git hooks, build configuration (`*.config.*`, `tsconfig*.json`, `biome.json`,
  `.storybook/`, `scripts/`), container or deployment descriptors or release configuration,
- a source of context was cut at its size limit,
- the reviewer did not read every line of the diff (measured from its own log),
- the reviewer returned more findings than allowed.

The labels keep the short `pre-check:` prefix; they are the one exception to "we do not use GitHub labels for pull
requests" in [code review](../../process/CODE_REVIEW.md).

**"Clean" is not "reviewed".** Text in the pull request cannot make the reviewer act, but it can make it under-report
and return a falsely clean result. "Clean" and "advisory" are therefore neither "safe" nor an approval, and a green
pre-check is never a person's sign-off. Anything automated must read the `frontend-pre-check / review` check run of the
pull request's **head commit**, never the label: anyone with triage access, and any workflow, can set a label.

**Bots and forks.** Because a skip fails the check, a Dependabot or other bot pull request, a fork pull request, and
every pull request in a repository where the secret is not available fail `frontend-pre-check / review`. Where the
check is required, such a pull request is merged by a person with the right to bypass the ruleset, after their own
review - deliberately: nothing reviewed it otherwise.

## What the reviewer gets

The reviewer is isolated from the agent that wrote the code and from GitHub. It receives only:

- the diff of the pull request, classified by `classify.py` and in risk order (application code first), and its
  description; tests and test helpers are left out of the diff by an immutable policy and listed with their size,
- the linked issues **of this organisation** opened by its members, with its members' comments (owners, members,
  collaborators); the title and body of an issue opened by anyone else, and comments by anyone else, are left out,
- the Figma links found there - recorded, but **not opened**: the reviewer sees neither Figma nor images (see
  [Design comparison](#design-comparison)),
- documents in `gi-org-pl/product` that the issues link, **only from its default branch**, pinned to the commit it
  pointed at during the run (a link to another branch or a tag is skipped),
- these standards (`gi-tech-standards`) at the commit of the workflow,
- the repository's own guide - `AGENTS.md` and `CLAUDE.md` files at any depth, `README.md`, `docs/` and the pull
  request template - **as they are on the base branch**, so that a pull request cannot change the rules it is checked
  against.

All of it is untrusted, whoever wrote it. Text written by people is marked as quoted data with a nonce of the run; that
marks provenance and helps the reviewer, but it is no security boundary. The reviewer can read and search files of the
checked-out pull request, inside the working directory only. It cannot run commands, edit files, browse the web or
post anything; the review job publishes its result after escaping it.

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

- **Result** - the outcome and the reviewer's one-line summary.
- **Findings** - every finding (up to 30 shown, blocking ones first; the outcome counts all of them) with severity,
  location and its full explanation; whether it was also attached inline.
- **Technical decisions in this PR** - data structures, state, API contracts, UX behaviours, new dependencies,
  architecture. "None." where the pull request makes no decision of that kind; "Deviation:" where a decision departs
  from the issue or the standard.
- **What was checked** - the reviewed diff, its head and base commits (the head as it is, not the merged result),
  whether the reviewer read the whole diff, the linked issues, the standards version and the documents used.
- **What was not checked** - always runtime behaviour; every change without a reviewable diff, every path that needs
  a person, renames, the files left out by policy with their size, images, the Figma note, cut sources and notes.
- **For QA** - what to test by hand.

**Everything the reviewer wrote is rendered as escaped plain text.** HTML, entities and Markdown structure are escaped,
so no link of any kind (inline, reference, shortcut, angle-bracket, protocol-relative or bare `www.`), no image, no
mention, no heading, list or table can come from the model; schemes, `www.` and `@` are broken so GitHub does not
autolink them. Fenced and inline code stay literal, and `suggestion` blocks become plain code. The only links in the
comment are built by the workflow itself (the run, the reviewer instructions, Figma links from the scope), each checked
by `allowed_link()` after percent-decoding, so `..` segments cannot leave the allowlisted place.

**Credentials.** Known credential shapes are redacted, including any run of 80 or more base64- or hex-like characters,
because a token may come back encoded - a conscious, fail-safe choice that can hide a legitimate long hash; narrow it
by an entropy threshold if it gets in the way, never by dropping it. After that, the reviewer's text and the final
output are scanned for anything that still looks like a credential (secret-named keys with generated-looking values,
URLs with passwords, authorization headers, common provider key shapes); a hit withholds the whole result. This is a
heuristic backstop, **not data-loss prevention**: a credential in a pull request has to be rotated by a person in any
case.

`test_render.py`, `test_classify.py` and `test_report.sh` lock these rules in and run in this repository's CI.

## When it does not review

The `frontend-pre-check / gate` job decides, and the review job then **fails** with "not pre-checked" (labels off, the
Pre-check comment saying why):

- the pull request comes from a fork - secrets are not available there,
- the pull request is a draft (it is reviewed when it is marked ready for review),
- the secret `CLAUDE_CODE_OAUTH_TOKEN` is not available to the repository,
- the pull request or the push comes from a bot,
- the person who triggered the run has no write access,
- the pull request had more than `max_runs_per_hour` runs in the last hour.

For a **merge queue** entry (`merge_group`) the review job does not run the reviewer again: it passes when every pull
request named in the entry has a successful `frontend-pre-check / review` check on its current head, and fails
otherwise. The merged result - the pull request on top of the latest base - is not reviewed; that is what the merge
queue's other checks are for.

If the gate fails, the review job fails. A run whose commit is no longer the head of the pull request publishes
nothing; a run whose base moved during the review fails with "not current".

## Limits and cost

The reviewer uses a Claude subscription through an OAuth token, with the same limits as the rest of the AI work done
on that subscription. The workflow keeps one review small:

| Setting | Default | Input |
| --- | --- | --- |
| Model | `sonnet` | `model` |
| Maximum agent turns | 60 | `max_turns` |
| Reviewed diff | 3000 changed lines, in risk order; more needs a person | `max_diff_lines` |
| Files left out of the diff | the exclusion policy in `classify.py`: tests (`*.test.ts(x)`, `*.spec.ts(x)`, `__tests__/`, top-level `e2e/`), test helpers (`__mocks__/`, `*.fixture(s).ts`, `setupTests.ts`, `src/utils/vitest/`), snapshots, lock files (which still need a person). A caller can choose a subset, never add to it | `exclude_paths` |
| Review timeout | 20 minutes (at most 50; the job stops at 60) | `timeout_minutes` |
| Runs per pull request | 8 in the last hour, counted over every page of runs of this pull request | `max_runs_per_hour` |

A burst of events on one pull request is debounced: an edit waits 30 seconds, and a newer event cancels the waiting
gate and a review that is still running. Publication is serialised per pull request across runs, and every write is
preceded by a check that the pull request is still at the reviewed head and base. The number of turns, the duration,
the tokens, the permission denials, the API-price estimate (on a subscription not money spent), whether the diff was
read in full, and the tools the reviewer had are in the summary of each run.

If a run does not finish - most often because the subscription limit is reached - the Pre-check comment says so and
the check fails; re-run it later.

## Setting it up in a repository

The workflow is reusable: it lives here, in
[`.github/workflows/frontend-pre-check.yml`](../../../.github/workflows/frontend-pre-check.yml), with its scripts in
[`.github/frontend-pre-check/`](../../../.github/frontend-pre-check/). A repository calls it with a short workflow:

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
      checks: read
    uses: gi-org-pl/gi-tech-standards/.github/workflows/frontend-pre-check.yml@<full commit SHA> # main on <date>
    secrets:
      CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
```

- **Pin a full commit SHA** of `main` in `uses:`. The workflow takes its scripts and the reviewer instructions from
  the same commit (`job.workflow_sha`), so the SHA pins all of it, and a later change here reaches a repository only
  when its caller is bumped in a reviewed pull request.
- **The job name** `frontend-pre-check` makes the check `frontend-pre-check / review` - the one to require.
- **`edited` with the job's `if`** re-runs the pre-check when the description changes - it carries the design
  comparison - or the pull request gets a new base branch; edits of the title alone start nothing. A run skipped by
  this `if` creates no `frontend-pre-check / review` check, so it cannot replace the last result.
- **`converted_to_draft`** withdraws the result when a pull request goes back to draft.
- **`merge_group`** lets the check pass for queue entries whose pull requests passed.
- **`actions: read`** lets the gate count the runs of the last hour; **`checks: read`** lets the review job read the
  pull requests' check runs for a merge queue entry.

## Approval

The pre-check never approves. Its label and its check inform; a person accepts:

- the bot account that opens pull requests cannot approve its own pull requests,
- an approval submitted with the workflow token would come from `github-actions[bot]`, could be forged by any workflow
  in the repository, and never counts as a code owner's review. The pre-check does not submit one.

The options, from the simplest:

1. **Required status check** `frontend-pre-check / review` plus the existing human approval (recommended): nothing merges with
   unresolved blocking findings, with changes the pre-check cannot judge, or without a pre-check at all, and a person
   still accepts the pull request. Pull requests that need a person, and bot and fork pull requests, then need someone
   with the right to bypass the ruleset.
2. **Label only**: the check is not required; the label and the summary inform the person, who decides.

Until the organisation has made the settings below and the first weeks of runs have been looked at, use option 2: the
pre-check is not yet a security-enforcing gate.

## Security

### Threat model

Three kinds of actors matter:

1. **Anyone with write access to the repository.** Under `pull_request`, the caller workflow is read from the pull
   request's merge ref. A writer can change the caller's inputs, add a job named `review`, or add a step that prints
   `CLAUDE_CODE_OAUTH_TOKEN`. Nothing inside the reusable workflow can prevent that; it is handled by the settings
   below.
2. **Anyone who writes text or code the reviewer reads.** The diff, the description, linked issues and documents and
   file names are attacker-influenced. They can make the reviewer report wrongly - prompt injection is assumed to work
   sometimes - but they cannot make it act: it has a read-only token, read tools confined to the workspace, no shell,
   no web and nothing to post with, and the verdict does not rest on its word alone.
3. **Whoever can push to `main` of gi-tech-standards.** A caller that pins a commit SHA runs only what was pinned; one
   that uses a branch runs whatever lands there.

### What the workflow does

- **No job holds both the secret and a write token.** `analyse` has the secret and a read-only token; `review` has a
  write token and neither the secret nor code of the pull request; `gate` has neither the secret nor a checkout of the
  pull request. `GH_TOKEN` is set only on the steps that call `gh`; the action uses the read-only token.
- **The reviewer's tools are limited at the source.** `--tools "Read,Glob,Grep"` makes these the only built-in tools
  that exist in the session; `--restricted` confines the file tools to the working directory, ignores settings files
  and refuses `bypassPermissions`; `--strict-mcp-config` with no `--mcp-config` leaves no MCP server, so no MCP tool
  exists; `disableAllHooks`, user settings only, the default permission mode. On top: `Read` is allowed for `./**`
  only, and the runner's `/proc`, temp, tool and home configuration paths and `.git/` are denied. The tools the session
  really had are read from its log and shown in the run summary.
- **Nothing from the pull request runs.** The scripts and instructions come from gi-tech-standards at
  `job.workflow_sha`. After the checkout every symbolic link is deleted, and so are `CLAUDE.md`, `CLAUDE.local.md`,
  `AGENTS.md`, `.claude/`, `.mcp.json` and `.claude.json` at any depth.
- **Context comes from the API only, never from the checkout**, with paths and refs validated (no `.` or `..`
  segments, a plain character set, `realpath` under the target directory), issues limited to this organisation and its
  members, documents limited to the default branch, sizes capped and every cut recorded. A file name with a control
  character or a backtick stops the run.
- **The verdict is deterministic where it can be.** `classify.py` decides coverage from GitHub's file records (both
  paths of a rename, the status, the patch); the reviewer's reading of the diff is measured from its own log (every line
  of `diff.patch` must have been read); the outcome counts every finding and ignores the reviewer's own `result`.
- **Escaped plain-text output and a final credential scan.** See [The Pre-check comment](#the-pre-check-comment).
  Nothing the reviewer wrote reaches a workflow command or the log; the execution log is not uploaded, and only
  numbers, a fixed word and tool names leave the job.
- **Fresh and ordered publication.** One publisher per pull request at a time, and a head and base check before every
  write.
- **Every action is pinned by a full commit SHA** (`actions/checkout`, `anthropics/claude-code-action`; the latter pins
  its own dependencies and the Claude Code version, 2.1.304; `--tools` and `--restricted` exist since at least
  2.1.285, and the run summary shows the tool set the session really had).
- **Inputs are validated** in the gate (the model name, numbers within ranges, document repositories of the same
  organisation) and the exclusions against the policy in `classify.py`.

What is **not** done, and why:

- The reviewer's true coverage beyond reading the diff - whether it understood every change - cannot be measured. The
  check therefore claims an advisory analysis, and hard guarantees stay with branch rules, human review and the
  deterministic rules above.
- Prompt-injection fixtures against the model are not part of CI: they need the subscription and are not
  deterministic. Run them by hand when the reviewer instructions or the model change.
- A Markdown AST parser is not used: escaping every model text to plain text is simpler and leaves nothing to parse.

Evidence from `anthropics/claude-code-action` at the pinned commit (v1.0.254): in automation mode (a `prompt` on a
`pull_request` event) it adds an MCP server only for tools named in `--allowedTools` (`github_comment`,
`github_inline_comment`, `github_ci`) or for commit signing, none of which apply here; it passes no
`--permission-mode` in this mode; it hands the remaining `claude_args` to the CLI; with `github_token` given it uses
that token and asks for no OIDC token, and it removes the OIDC request variables from the CLI's environment. It writes
`enableAllProjectMcpServers: true` into the user settings, which `--strict-mcp-config` overrides.

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
8. **Require the right check, read the right signal.** If the check is required: Repository → Settings → Rules →
   Rulesets → "Require status checks to pass" → `frontend-pre-check / review` from GitHub Actions, and decide who may
   bypass it (bot, fork and "needs a person" pull requests depend on that). Automation that depends on the pre-check
   reads that check run for the head commit, never the label, and nobody treats a green pre-check as a sign-off.
9. **Re-audit on every bump of the action.** The secret stays safe because of the reviewer's sandbox in `analyse`: the
   tool set, the `Read` scope and denylist (`/proc`, `~/.ssh`, `~/.claude*`, `/tmp`, runner temp and tools, `.git/`), no
   shell, no web, no MCP servers, with the redaction and the credential scan only as a backstop. When the pinned SHA of
   `anthropics/claude-code-action` (or the Claude Code version it installs) is bumped, check again in its source and in
   the first run's summary which tools, MCP servers, settings sources and permission mode it uses, and whether the
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
| [`.github/frontend-pre-check/classify.py`](../../../.github/frontend-pre-check/classify.py) | Classifies the changed files: reviewed, excluded by policy, safe assets, unreviewable, needs a person |
| [`.github/frontend-pre-check/result.schema.json`](../../../.github/frontend-pre-check/result.schema.json) | The structured result the reviewer returns |
| [`.github/frontend-pre-check/render.py`](../../../.github/frontend-pre-check/render.py) | Validates the result, derives the outcome, escapes and scans the output |
| [`.github/frontend-pre-check/report.sh`](../../../.github/frontend-pre-check/report.sh) | Publishes the comment, inline comments and label, and sets the status of the required check |
| [`.github/frontend-pre-check/test_classify.py`](../../../.github/frontend-pre-check/test_classify.py), [`test_render.py`](../../../.github/frontend-pre-check/test_render.py), [`test_report.sh`](../../../.github/frontend-pre-check/test_report.sh) | The tests, run in CI |
