# Git & Github: Repository settings

*The settings of our GitHub organization and of every repository in it are managed as code. Only admins change
them.*

## What is managed this way

Everything you would normally change in the **Settings** tab of a repository or of the organization, including small
things like a repository description:

* repository name, description, website and topics,
* visibility and features (issues, wiki, projects, discussions),
* merge options (allowed merge methods, auto-merge, deleting branches after merge),
* which teams have access to a repository, and with what role,
* organization members, teams and their members,
* security and GitHub Actions settings (Dependabot, allowed actions, workflow token permissions).

## How to request a change

1. Ask one of the admins (the `@gi-org-pl/admins` team) and tell them what should change and why.
2. The admin makes the change in a dedicated private repository and opens a pull request there. The pull request
   shows exactly what will change on GitHub.
3. Once the pull request is reviewed and merged, the change is applied automatically.

**Do not change these settings by hand**, even if your role in a repository lets you (for example, maintainers can
edit a description or topics). A nightly check reports every manual change, and the next applied change reverts it.
