# Code quality

Two programmers, three opinions. To keep the code review process clean, free of code style comments, certains tools and
sets of rules are adapted.

## ESLint

ESLint is a static analysis tool that automatically checks TypeScript code for errors, unsafe patterns and violations
of the agreed coding style, improving overall quality and maintainability.

> **#1: ESLint in version 10 MUST be used in services and Lambda functions.**
>
> Developers use ESLint to automatically analyze their JavaScript and TypeScript code for potential errors, bad
> patterns and style violations before the code runs, so that the codebase stays consistent and easier to maintain.
>
> CLI tools and scheduled scripts MAY skip ESLint (see [project types](/docs/backend/conventions/STRUCTURE.md#project-types)).

> **#2: ESLint configuration MUST be kept in `eslint.config.mjs` file.**

> **#3: Each project SHOULD share an identical ESLint configuration file.**
>
> Recommended ESLint configuration is committed to the repository and used consistently in local development and
> continuous integration.
>
> [See the recommended ESLint configuration in mypolitics-survey-producer-api repository.](https://github.com/gi-org-pl/mypolitics-survey-producer-api/blob/main/eslint.config.mjs)

> **#4: Code quality tools SHOULD be run before committing code.**
>
> Publishing incorrectly formatted code is wasting resources (GitHub Actions is not free) and time. Pipelines will
> fail, preventing Pull Requests from being merged, and developers will have to fix the code style issues before
> merging.

Read more about ESLint:

- [ESLint (official docs)](https://eslint.org/)

## Prettier

Prettier is an opinionated code formatter that automatically rewrites source code to follow a consistent style so that
formatting becomes predictable and independent of individual developer preferences.

> **#1: Prettier MUST be used for all languages supported by its formatter within the project.**
>
> Each project MUST define a shared Prettier configuration that is committed to the repository and used consistently in
> local development and continuous integration.

> **#2: Prettier configuration MUST be kept in `.prettierrc` file.**

> **#3: Each project SHOULD use a common Prettier configuration.**
>
> Recommended Prettier configuration is committed to the repository and used consistently in local development and
> continuous integration.
>
> [See the recommended Prettier configuration in mypolitics-survey-producer-api repository.](https://github.com/gi-org-pl/mypolitics-survey-producer-api/blob/main/.prettierrc)

> **#4. Code MUST be correctly formatted with Prettier before review.**
>
> New code and refactors SHOULD be fully formatted with Prettier before review, so that code reviews focus on
> correctness, design and behavior rather than formatting details.
