# Pre-check

Pre-check is an AI review that every front-end pull request gets before a person looks at it. It is a step of the
[code review](CODE_REVIEW.md) process, not a replacement for it. Back end is out of scope.

## Why

With AI writing code fast, reading every line of a pull request is no longer a good use of a person's time. What a
person has to judge are the **decisions**: data structures, state management, API contracts, the specific behaviour a
user sees. Preferences about naming or about how code is split into files, which no standard defines, are not worth a
review round.

So after the implementing agent (or developer) finishes, a second, isolated AI checks the work: the code as such,
compliance with the standards, the design and the documentation, and the typical bugs. If it finds nothing to fix, it
pre-approves the pull request and posts a short summary of the technical decisions the pull request makes. The
functionality is still tested in the normal QA process. Finally a person reads the pull request description and the
summary of decisions, and accepts the pull request or rejects it with suggestions.

## The flow

1. **Implementation.** A developer or an AI agent implements the issue and opens a pull request with a description
   that states decisions, deviations and verification, as the repository's guide asks.
2. **Pre-check.** When the pull request is opened, updated, reopened or marked ready for review, the reviewer runs:
   - real findings become inline comments, each with what is wrong, why and how to fix it, labelled with
     [conventional comments](CODE_REVIEW.md#conventional-comments) (`[blocking]` or `[non-blocking]`),
   - one comment headed **Pre-check** summarises the result and the technical decisions,
   - the label `pre-check: passed` or `pre-check: changes` is set,
   - the check `pre-check / review` passes (passed) or fails (changes needed).
3. **Fixes.** The author fixes the blocking findings and pushes. The pre-check runs again and updates the same
   Pre-check comment. A finding the author thinks is wrong is answered in its thread with the reason; the person
   reviewing decides.
4. **QA.** The functionality is tested by hand, guided by the "For QA" part of the summary.
5. **Decision.** A person reads the pull request description and the Pre-check summary, and accepts the pull request or
   rejects it with suggestions. Reading the code is the person's choice, not a duty.

## What the reviewer gets

The reviewer is isolated from the agent that wrote the code. It receives only:

- the diff of the pull request (capped, see [Limits](#limits-and-cost)) and its description,
- the linked issues with their comments,
- the Figma links found in the pull request and the issues - recorded, but **not opened**: the reviewer cannot see
  Figma and says so in its summary,
- documents in `gi-org-pl/product` that the issues link (the workflow token reads only public repositories besides the
  pull request's own; an issue or a document it cannot read is listed in the summary as not read),
- these standards (`gi-tech-standards`),
- the repository's own guide - `AGENTS.md` and `CLAUDE.md` files at any depth, `README.md`, `docs/` and the pull
  request template - **as they are on the base branch**, so that a pull request cannot change the rules it is checked
  against,
- its own inline comments from earlier runs, so that it does not repeat them.

It can read files of the checked-out pull request and post inline comments on the diff. It cannot run commands, edit
files, push, browse the web, approve or merge. The summary comment, the label and the status are set by the workflow
from the reviewer's structured result, not by the reviewer.

## What it checks

The full checklist is in [the reviewer instructions](../frontend/PRE_CHECK_REVIEWER.md). In short:

- **bugs** typical for our stack - logic errors, unvalidated or unhandled data, async races, effect and hook mistakes,
  hydration mismatches, missing translations, accessibility that breaks use, security,
- **compliance** with written rules only - the repository's `AGENTS.md` and [front-end standards](../frontend/INDEX.md),
  each finding naming the rule,
- **design and documentation** - the issue's acceptance criteria, linked documents, documentation updated with the
  change, a pull request description that matches the diff,
- **tests** - logic covered by meaningful tests, stories and end-to-end coverage where the repository asks for them.

It does not comment on naming, file splitting, formatting or anything else no written rule defines.

## The Pre-check comment

One comment per pull request, found again by a hidden marker and updated on every run. Its sections are fixed:

- **Result** - passed, or changes needed with the number of blocking findings; then a one-line summary and the list of
  findings.
- **Technical decisions in this PR** - data structures, state, API contracts, UX behaviours, new dependencies,
  architecture. "None." where the pull request makes no decision of that kind; "Deviation:" where a decision departs
  from the issue or the standard.
- **What was checked** - the reviewed diff and commit, the linked issues, the standards version and the documents used.
- **What was not checked** - always runtime behaviour (nothing is built or run), the Figma design when there are links,
  files left out of the diff, and anything else the reviewer could not examine.
- **For QA** - what to test by hand.

## When it does not run

The `pre-check / gate` job decides, and ends green with a notice when the review is skipped:

- the pull request is a draft (it runs when it is marked ready for review),
- the pull request comes from a fork - secrets are not available there,
- the secret `CLAUDE_CODE_OAUTH_TOKEN` is not set - the pre-check is not enabled,
- the pull request or the push comes from a bot (Dependabot and similar),
- the person who triggered the run has no write access,
- the event is a merge queue entry (`merge_group`) - the pull request was pre-checked already.

A skipped `pre-check / review` job counts as passed for a required status check, so a skipped pre-check never blocks a
merge. If the gate itself fails, the review job runs anyway and fails, so a broken gate cannot pass a required check. When new commits go unreviewed - a fork, a bot or a person without write access pushed them, or the secret is gone -
the gate also takes the pre-check labels off and replaces an earlier Pre-check comment with "not run for commit ...", so an old "passed"
does not stand for code nobody pre-checked. The person reviewing is then the only check, as before the pre-check.

## Limits and cost

The reviewer uses a Claude subscription through an OAuth token, with the same limits as the rest of the AI work done
on that subscription. The workflow keeps one review small:

| Setting | Default | Input |
| --- | --- | --- |
| Model | `sonnet` | `model` |
| Maximum agent turns | 60 | `max_turns` |
| Reviewed diff | 3000 changed lines | `max_diff_lines` |
| Files never reviewed | lock files, snapshots, minified files, source maps, `dist/` | `exclude_paths` |
| Review timeout | 20 minutes (at most 50) | `timeout_minutes` |

A larger pull request is reviewed up to the cap. Its summary says "too large for a full pre-check" and lists the
reviewed and the unreviewed files; the result covers only the reviewed ones. GitHub lists at most 3000 files of a pull
request; the files beyond that are counted as not reviewed. The review timeout is cut to 50 minutes, because the job
itself stops at 60 and needs the rest to report a review that ran out of time. A newer push cancels a review that is still
running for the same pull request, and a run whose commit is no longer the head of the pull request (a late finish, or a
re-run of an old run) publishes nothing. The number of turns, the duration, the tokens and the API-price estimate of each run
are in the job summary of the run (on a subscription the estimate is not money spent).

If a run does not finish - most often because the subscription limit is reached - the Pre-check comment says so and
the job fails; re-run it later.

## Setting it up in a repository

The workflow is reusable: it lives here, in [`.github/workflows/pre-check.yml`](../../.github/workflows/pre-check.yml),
with its scripts in [`.github/pre-check/`](../../.github/pre-check/). A repository calls it with a short workflow:

```yaml
name: pre-check

on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
  merge_group:

permissions: {}

jobs:
  pre-check:
    name: pre-check
    permissions:
      contents: read
      pull-requests: write
      issues: write
    uses: gi-org-pl/gi-tech-standards/.github/workflows/pre-check.yml@main
    secrets:
      CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
```

Callers use `@main`: the reviewer then always follows the current standards and instructions, and a change to them is
reviewed once, here. The price is that a change here reaches every repository at once, so changes to `.github/` and to
the reviewer instructions go through the code owners of this repository. To pin a version instead, use a tag or a
commit in `uses:` and pass the same ref as the `standards_ref` input.

Steps outside the repository, done by an organisation owner:

1. **The secret.** Run `claude setup-token` with the Claude account whose subscription the pre-check should use, and store the token as the
   organisation secret `CLAUDE_CODE_OAUTH_TOKEN`, available to the repositories that use the pre-check. Until then the
   workflow is a no-op.
2. **Allowed actions.** The organisation's Actions policy must allow `anthropics/claude-code-action` and reusable
   workflows from `gi-org-pl/gi-tech-standards`.
3. **Labels.** The workflow creates `pre-check: passed` and `pre-check: changes` on its first run. To create them
   beforehand:

   ```shell
   gh label create "pre-check: passed" --color 0e8a16 --description "AI pre-check found nothing to fix" -R gi-org-pl/<repo>
   gh label create "pre-check: changes" --color d93f0b --description "AI pre-check found something to fix" -R gi-org-pl/<repo>
   ```

4. **Required status check (optional).** In the repository's ruleset for `main`, require the status check
   `pre-check / review`. A repository with a merge queue must keep the `merge_group` trigger in the caller, or queue
   entries wait for the check forever.

## Approval

The pre-check pre-approves by its label and its check, not by a GitHub review:

- the bot account that opens pull requests cannot approve its own pull requests,
- an approval submitted with the workflow token comes from `github-actions[bot]`, which needs the organisation setting
  "Allow GitHub Actions to create and approve pull requests". Whether it counts toward the required approvals depends on
  the ruleset, and it never counts as a code owner's review. We do not rely on it.

The options, from the simplest:

1. **Required status check** `pre-check / review` plus the existing human approval (recommended): nothing merges with
   unresolved blocking findings, and a person still accepts the pull request.
2. **Label only**: the check is not required; the label and the summary inform the person, who decides.
3. **A dedicated GitHub App** that submits the approval, if one day an approval of the pre-check should count on its
   own. This needs an App of the organisation and a change of the workflow.

A blocking finding that the person reviewing considers wrong is resolved by that person: either the author changes the
code anyway, or someone with the right to bypass the ruleset merges. A dedicated override (for example a label that
makes the check pass) does not exist yet.

## Security

- The pull request is untrusted input: the reviewer treats its text, the issues and the code as data and reports any
  attempt to steer it as a blocking finding. Its tools are read-only, it has no shell and no web access, and the
  workflow redacts token-like strings from the summary before posting it.
- The reviewer instructions and the scripts are taken from this repository, never from the pull request. Agent
  instruction files of the pull request (`CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md` and `.claude/` at any depth, also as
  symbolic links) are
  removed from the checkout before the reviewer starts, because Claude Code would load them as instructions; the
  base-branch versions are in the context, and the action restores the root `CLAUDE.md`, `.claude/` and `.mcp.json`
  from the base branch.
- A pull request can still change its repository's caller workflow. The reviewer reports such a change as blocking,
  and the repository's code owners should own `.github/workflows/`.

## Files

| File | What it is |
| --- | --- |
| [`docs/frontend/PRE_CHECK_REVIEWER.md`](../frontend/PRE_CHECK_REVIEWER.md) | The reviewer's instructions and checklist, used word for word as its prompt |
| [`.github/workflows/pre-check.yml`](../../.github/workflows/pre-check.yml) | The reusable workflow (`workflow_call`) |
| [`.github/pre-check/collect-context.sh`](../../.github/pre-check/collect-context.sh) | Collects what the reviewer may read |
| [`.github/pre-check/result.schema.json`](../../.github/pre-check/result.schema.json) | The structured result the reviewer returns |
| [`.github/pre-check/report.sh`](../../.github/pre-check/report.sh) | Posts the Pre-check comment, sets the label and the status |
