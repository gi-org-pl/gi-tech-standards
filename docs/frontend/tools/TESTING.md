# Testing

## Approach

We follow a **test pyramid** strategy: many unit tests and minimal end-to-end tests. This approach ensures fast
feedback loops while maintaining confidence in our code quality. All tests follow the
[testing convention](../conventions/TESTING_CONVENTION.md).

## Unit Testing

Unit tests are the foundation of our testing strategy. They run quickly and provide immediate feedback during
development.

> **#1. Unit tests MUST be written with Vitest, React Testing Library and React Test Renderer.**

> **#2. Unit tests SHOULD cover at least 95% of the code.**
>
> We aim for high coverage to ensure that individual components and functions work correctly in isolation.

> **#3. A unit test MUST be kept next to the file it tests, with the same name and a `.test.ts` or `.test.tsx`
> extension.**

- [Vitest documentation](https://vitest.dev/)
- [Testing Library documentation](https://testing-library.com/)
- [React Testing Library best practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)

## End-to-End Testing

> **#1. End-to-end tests MUST be written with Playwright and Gherkin.**

> **#2. End-to-end tests MUST cover all happy paths.**
>
> E2E tests validate complete user workflows and ensure that the application works correctly from the user's
> perspective. We focus on testing critical happy paths rather than exhaustive edge cases, which are better covered by
> unit tests. End-to-end tests are kept in `e2e/` (see [project structure](../conventions/PROJECT_STRUCTURE.md)).

- [Playwright documentation](https://playwright.dev/)
- [Gherkin syntax guide](https://cucumber.io/docs/gherkin/)
