# Instructions for AI agents

This repository holds the technical standards of Generacja Innowacja. These instructions are for agents that read the
standards to check or write code in other repositories, and for agents that edit the standards here.

## Reading the standards

- Start at the index of the area: `docs/frontend/INDEX.md`, `docs/backend/INDEX.md`, `docs/github/INDEX.md`,
  `docs/infrastructure/INDEX.md` or `docs/ai/INDEX.md`. The review process is in `docs/process/CODE_REVIEW.md`. Each
  index says what every document decides, so open only the documents the task needs.
- A rule is a numbered blockquote, `> **#1. … MUST …**`, followed by the reason for it. Numbers restart in each
  section, so cite a rule by file, section and number, for example `docs/backend/tools/RUNTIME.md`, Docker #3. To list
  every rule of an area: `grep -rn '^> \*\*#' docs/backend`.
- Documents that are not written as numbered rules yet describe their rules in prose.
- The keywords MUST, SHOULD, MAY and the others mean what RFC 2119 says (`docs/backend/conventions/RFC.md`).
- `research/` holds research behind past decisions. It is not a standard.

## Editing the standards

- Write a new rule in the format above: one bold sentence with an RFC keyword, then the reason in plain English for
  volunteers and interns. Link to an example in our repositories when there is one.
- Keep every rule in one place. Link to it from other documents instead of repeating it.
- Do not move or rename documents. Repositories, issue templates and tasks across the organization link to them by
  path.
- A new document gets a line in the index of its area that says what it decides. Do not add a page before it has
  content.
- Use relative links between documents.
- Wrap lines at 120 characters. CI runs markdownlint on every pull request: `npx markdownlint-cli '**/*.md'`.
- `.github/CODEOWNERS` says which team reviews each area: the front-end team owns `docs/frontend/`, the back-end team
  owns `docs/backend/` and `docs/ai/`.
