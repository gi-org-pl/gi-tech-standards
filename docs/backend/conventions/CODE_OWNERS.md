# Code owners

Setting code owners for directories and files is a good practice to automatically summon reviewers and catch the
attention of other developers when pull requests are created.

> **#1. Every backend repository MUST contain `CODEOWNERS` file, to prevent editing specific files unintentionally.**
>
> This applies to every [project type](/docs/backend/conventions/STRUCTURE.md#project-types), not only to services.
> File should be named `CODEOWNERS` and located in the `.github/` directory.

> **#2. By default, all files in backend repositories should be owned by the `@gi-org-pl/backs` team.**
>
> This team is responsible for all backend projects, and they will be summoned to all PRs created in this
> repository.

> **#3. If there are files that editing should be restricted or is considered risky, it should be owned by the admins
> `@gi-org-pl/admins` team.**
>
> Files are considered risky if they relate to the environment and project configuration, security advisories, CI/CD
> configuration and so on.
>
> See example files:
>
> - [mypolitics-survey-producer-api](https://github.com/gi-org-pl/mypolitics-survey-producer-api/blob/main/.github/CODEOWNERS)
> - [mypolitics-survey-consumer](https://github.com/gi-org-pl/mypolitics-survey-consumer/blob/main/.github/CODEOWNERS)

> **#4. Code owners MUST tag teams, not people.**
>
> When a PR is created, the correct team will be notified and can decide who should review the code.
