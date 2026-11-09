# Code Quality

## Linting

Biome is a fast, all-in-one toolchain for JavaScript, TypeScript, and JSON. It combines a linter and formatter in a
single tool, providing:

- **Speed**: Written in Rust, Biome is significantly faster than ESLint
- **Simplicity**: One tool instead of multiple (ESLint + Prettier + more)
- **Zero configuration**: Works out of the box with sensible defaults
- **Unicorn ruleset**: Additional rules for catching common bugs and enforcing best practices

> **#1. Biome MUST be used for linting and formatting, instead of ESLint and Prettier.**

> **#2. Biome's base ruleset MUST be used together with the Unicorn overrides.**
>
> This ensures code quality and consistency across all projects.

> **#3. A Biome rule MUST NOT be disabled without a comment that says why.**

- [Biome documentation](https://biomejs.dev/)
- [Biome GitHub repository](https://github.com/biomejs/biome)
- [Biome rules reference](https://biomejs.dev/linter/rules/)
- [Unicorn ruleset](https://github.com/sindresorhus/eslint-plugin-unicorn)

## Automation

> **#1. Code MUST be linted automatically on every commit.**

> **#2. Build, lint, test and e2e jobs MUST run in CI and pass before a pull request is merged.**
>
> This ensures that code quality issues and security vulnerabilities are caught early in the development process,
> not after deployment.
