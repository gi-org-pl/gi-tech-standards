# Security standards

Welcome to organization security standards.

Our services hold personal data, and the answers given in myPolitics reveal political opinions, which GDPR treats as
a [special category of personal data](https://gdpr-info.eu/art-9-gdpr/). A mistake here can hurt real people, so
security is a part of the work, not a step at the end of it.

These standards apply to all backend projects. Each rule describes something that already runs in production in at
least one of our backend services. Not every project follows every rule yet: new projects MUST follow them from the
start, and existing projects move towards them.

In each document, rules are numbered within each section and written as `> **#1. …**`, with the reason for the rule
below it. The keywords MUST, SHOULD and MAY are explained in [RFC keywords](../backend/conventions/RFC.md).

## Reporting a problem

> **#1. An unfixed security problem MUST NOT be described in a public repository, issue, pull request or channel.**
>
> A description of an open problem is an instruction for using it, and this repository is public too. Tell the
> _Engineering_ team directly, and keep the details in a place only they can read until the fix is deployed.

## Topics

- [Secrets](SECRETS.md) - where secrets are kept and how they reach a container, who can read them, keeping them out of
  AI tools and chats, and rotating them.
- [Pipelines](PIPELINES.md) - job permissions, `persist-credentials`, production builds without the Docker cache, and
  protection of the default branch, release tags and forks.
- [Dependencies](DEPENDENCIES.md) - Dependabot, `npm ci`, `overrides` for vulnerable packages, and install scripts in
  `allowScripts`.
- [Containers](CONTAINERS.md) - an unprivileged user, minimal images pinned by digest, a read-only file system without
  capabilities, and failing on start-up errors.
- [Infrastructure](INFRASTRUCTURE.md) - encrypted OpenTofu state, no inbound traffic and limited egress, a private
  database with verified TLS, minimal permissions, and log retention.
- [Application](APPLICATION.md) - request validation, CORS and `trust proxy`, passwords and sign-in, session tokens and
  cookies, and rate limits.
- [Personal data](PERSONAL_DATA.md) - what logs may contain and how long they are kept, and what an export may return.
