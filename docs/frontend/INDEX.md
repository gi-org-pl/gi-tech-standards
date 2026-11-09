# Front-end Standards

This document outlines the core technologies, tools, and libraries used in our front-end projects. Each choice has been
made with careful consideration of maintainability, developer experience, and long-term sustainability.

> **All new front-end projects in the organization should follow these configuration standards.**
>
> These standards ensure consistency across projects, making it easier for developers to switch between projects
> and maintain code quality. If you need to use a different technology, please seek approval from the Technical Leader
> first.

In each document, rules are numbered within each section and written as `> **#1. …**`, with the reason for the rule
below it. The keywords MUST, SHOULD and MAY are explained in [RFC keywords](../backend/conventions/RFC.md).

## Conventions

- [Project structure](conventions/PROJECT_STRUCTURE.md) - where pages, components, API clients, constants, types,
  utils, assets and end-to-end tests live, and when a component becomes shared.
- [Component structure](conventions/COMPONENT_STRUCTURE.md) - the files of a component, and what stays inside its
  directory.
- [Naming](conventions/NAMING.md) - camelCase, PascalCase or kebab-case for each kind of file, directory and name.
- [Testing convention](conventions/TESTING_CONVENTION.md) - the Given-When-Then structure of unit and end-to-end
  tests.

## Tools

- [Fundamentals](tools/FUNDAMENTALS.md) - Node.js, Yarn and TypeScript, and how a new project starts.
- [React](tools/REACT.md) - React, Vite, Storybook, React Router and Tailwind CSS.
- [State management](tools/STATE_MANAGEMENT.md) - when to use React Context and when to use Zustand.
- [API communication](tools/API_COMMUNICATION.md) - Axios for requests and Zod for validating responses.
- [Code quality](tools/CODE_QUALITY.md) - Biome, and the checks that run on every commit and in CI.
- [Testing](tools/TESTING.md) - unit tests with Vitest, end-to-end tests with Playwright, and their coverage.

## Definition of Done

A front-end task is done when:

- [ ] new files follow the [project structure](conventions/PROJECT_STRUCTURE.md), the
  [component structure](conventions/COMPONENT_STRUCTURE.md) and the [naming](conventions/NAMING.md),
- [ ] unit tests are added or updated in the [Given-When-Then structure](conventions/TESTING_CONVENTION.md), and they
  cover at least 95% of the changed files ([Testing](tools/TESTING.md), Unit testing #2),
- [ ] a change to a user-facing flow adds or updates its Playwright end-to-end test ([Testing](tools/TESTING.md),
  End-to-end testing #2),
- [ ] Biome reports no errors, and no rule is disabled without a comment that says why
  ([Code quality](tools/CODE_QUALITY.md), Linting #3),
- [ ] TypeScript reports no errors, with no `any` and no `@ts-ignore` without a comment
  ([Fundamentals](tools/FUNDAMENTALS.md), Language #3),
- [ ] API responses are validated with Zod ([API communication](tools/API_COMMUNICATION.md), Data validation #1),
- [ ] a new shared component has a Storybook story ([React](tools/REACT.md), Design system documentation #1),
- [ ] a new Zustand store is justified in the pull request description
  ([State management](tools/STATE_MANAGEMENT.md), Secondary strategy #2),
- [ ] build, lint, test and e2e jobs pass in CI ([Code quality](tools/CODE_QUALITY.md), Automation #2).

## Resources

- [Vite Project Boilerplate](https://github.com/gi-org-pl/vite-project-boilerplate)
