# AI agents in repositories

An AI agent, such as Claude Code, Codex, Cursor or Copilot, reads a repository and writes code in it. The rules below
cover what a repository gives every agent: the instructions it reads, the files it must not open, the skills it uses,
and the review of what it writes. How people work with AI is in [Reflective AI usage](REFLECTIVE_AI_USAGE.md). Keeping
secrets and personal data away from AI tools is in [Secrets](../security/SECRETS.md#keeping-secrets-out-of-sight) and
[Personal data](../security/PERSONAL_DATA.md).

The keywords MUST, SHOULD and MAY are explained in [RFC keywords](../backend/conventions/RFC.md).

## Instructions

> **#1. Every repository MUST have an `AGENTS.md` file at its root.**
>
> Agents follow written rules literally: a missing rule makes them guess, and an outdated one makes them "fix" code that
> is correct. `AGENTS.md` says what the repository does, how to run and test it, its ground rules, how pull requests
> and releases work, and where it deviates from these standards. Write it with RFC keywords, about how the repository
> works today. When reviewers or the people who work with agents correct the same thing twice, add it to `AGENTS.md`:
> an agent's personal memory reaches only one person.

> **#2. The root `CLAUDE.md` MUST contain only `@AGENTS.md`.**
>
> Codex, Cursor and Copilot read `AGENTS.md`. Not every version and setup of Claude Code does: when a `CLAUDE.md` file
> exists in the working directory or in any directory above it, Claude Code reads only `CLAUDE.md` files. The
> `@AGENTS.md` import loads the same file in every tool, so there is one set of rules to keep up to date. Change
> `AGENTS.md`, never `CLAUDE.md`.

## Settings

> **#1. A repository that uses `.env`, `*.tfvars` or OpenTofu state and plan files MUST commit deny rules that stop
> agents from reading them.**
>
> [Secrets](../security/SECRETS.md#keeping-secrets-out-of-sight) #1 says that agents must not open these files. A deny
> rule makes sure they cannot, whether the agent read that rule or not. For Claude Code, commit
> `.claude/settings.json` with at least:
>
> ```json
> {
>   "permissions": {
>     "deny": [
>       "Read(**/.env)",
>       "Read(**/*.tfvars)",
>       "Read(**/*.tfstate)",
>       "Read(**/*.tfstate.backup)",
>       "Read(**/tfplan)"
>     ]
>   }
> }
> ```
>
> Do not deny `.env.*`, because that also hides `.env.dist`, which agents need. The rules also stop file commands that
> name the file, such as `cat .env`, but not a recursive `grep` or a script that opens files itself, so they narrow the
> risk without replacing the rule in Secrets. Personal permissions go to `.claude/settings.local.json`, which MUST be
> listed in `.gitignore`.

> **#2. `.claude/` and `CLAUDE.md` MUST be owned by the admins in `.github/CODEOWNERS`.**
>
> Settings in `.claude/` can allow commands and run hooks on the computer of everyone who opens the repository with an
> agent, and skills tell agents what to do. A change there needs the same review as a change to CI. `AGENTS.md` MAY
> stay with the team, because pull requests update it together with the code they change. Read more about
> [code owners](../backend/conventions/CODE_OWNERS.md).

## Skills

> **#1. Skills that describe how a team works SHOULD be committed to the repository, in
> `.claude/skills/<name>/SKILL.md`.**
>
> A review checklist or a task template that lives in one person's prompts has to be typed again in every session, and
> nobody else's agent knows it. A committed skill is reviewed, versioned and shared like code. When the way the team
> works changes, change the skill in the same pull request.

## Pull requests

> **#1. A pull request prepared with an AI agent MUST be reviewed outside the session that wrote it before it is
> merged.**
>
> The session that wrote the code shares its blind spots and is sure of its own work. A person reviews it, or at least
> a fresh agent session, such as `/code-review` in Claude Code, whose findings the author reads and answers. This also
> applies to admins, who can merge without an approval, and matters most in repositories where merging deploys to
> production.
