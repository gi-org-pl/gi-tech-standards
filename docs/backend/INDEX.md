# Backend standards

Standards for the server-side projects of the organization. In each document, rules are numbered within each section
and written as `> **#1. …**`, with the reason for the rule below it. The keywords MUST, SHOULD and MAY are explained
in [RFC keywords](conventions/RFC.md).

## Tools

- [Runtime](tools/RUNTIME.md) - Docker and base images, Node.js and npm, TypeScript, Nest.js, PostgreSQL and Prisma,
  and how each project type runs.
- [Code quality](tools/CODE_QUALITY.md) - ESLint and Prettier, their configuration files, and when to run them.
- [CI/CD](tools/CI_CD.md) - which GitHub Actions a workflow may use and how to pin them, and how to create and release
  our own actions.

Testing has no document of its own yet. The layout of test directories is in
[Structure](conventions/STRUCTURE.md#tests), and the names of Gherkin files and scenarios are in
[Naming](conventions/NAMING.md#cucumberjs).

## Conventions

- [Structure](conventions/STRUCTURE.md) - the four project types (service, Lambda function, CLI tool, scheduled
  script) and the directory layout of each, including tests and Nest.js modules.
- [Naming](conventions/NAMING.md) - names of files, classes, functions and directories in TypeScript and Nest.js,
  exports, function syntax, and names of Gherkin files and scenarios.
- [Code owners](conventions/CODE_OWNERS.md) - the `CODEOWNERS` file that every repository needs, and which team owns
  which files.
- [RFC keywords](conventions/RFC.md) - what MUST, SHOULD, MAY and the other keywords mean in these documents.

## Learning

The learning curve for backend developers is steep. [Learning materials](LEARNING.md) list the documentation and
roadmaps to start with, and the libraries our projects depend on.
