# Security standards

Welcome to organization security standards.

Our services hold personal data, and the answers given in myPolitics reveal political opinions, which GDPR treats as
a [special category of personal data](https://gdpr-info.eu/art-9-gdpr/). A mistake here can hurt real people, so
security is a part of the work, not a step at the end of it.

These standards apply to all backend projects. Each rule describes something that already runs in production in at
least one of our backend services. Not every project follows every rule yet: new projects MUST follow them from the
start, and existing projects move towards them.

Keywords like **MUST** and **SHOULD** are used as described in [RFC](/docs/backend/conventions/RFC.md).

## Reporting a problem

> **#1. An unfixed security problem MUST NOT be described in a public repository, issue, pull request or channel.**
>
> A description of an open problem is an instruction for using it, and this repository is public too. Tell the
> _Engineering_ team directly, and keep the details in a place only they can read until the fix is deployed.

## Topics

> **Secrets** are the keys to everything else. These rules say where secrets are kept, who can see them and how to
> replace them.
>
> [Read more about secrets](/docs/security/SECRETS.md)

> **Pipelines** can reach the code, the secrets and the production servers. These rules say what a job can do and what
> protects the branch it runs from.
>
> [Read more about pipelines](/docs/security/PIPELINES.md)

> **Dependencies** are code written by other people that runs on our machines. These rules say how they get updated
> and what they can do during installation.
>
> [Read more about dependencies](/docs/security/DEPENDENCIES.md)

> **Containers** decide how far an attacker gets after breaking into the application. These rules say how images are
> built and what a running container can do.
>
> [Read more about containers](/docs/security/CONTAINERS.md)

> **Infrastructure** covers the OpenTofu state, the network, the database and the permissions of our services.
>
> [Read more about infrastructure](/docs/security/INFRASTRUCTURE.md)

> **Application** rules cover the code of a service: requests, passwords, sessions and rate limits.
>
> [Read more about the application](/docs/security/APPLICATION.md)

> **Personal data** rules say what can be logged and what can leave the database in an export.
>
> [Read more about personal data](/docs/security/PERSONAL_DATA.md)
