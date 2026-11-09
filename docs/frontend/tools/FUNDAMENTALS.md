# Fundamentals

## Runtime Environment

> **#1. Node.js in version 24 or newer MUST be used.**
>
> We use the latest LTS version of Node.js to ensure access to modern JavaScript features and performance
> improvements. Node.js 24 provides excellent support for ES modules, improved performance, and better security.

Read more about Node.js:

- [Node.js official documentation](https://nodejs.org/)
- [Node.js release schedule](https://github.com/nodejs/release#release-schedule)

## Package Management

> **#1. Yarn in version 1.22 or newer MUST be used.**
>
> Yarn provides reliable dependency management with lockfile consistency, better performance than npm, and excellent
> workspace support for monorepos. We use Yarn for its stability and proven track record.

> **#2. The Yarn lockfile MUST be committed, and npm or pnpm MUST NOT be used in the same project.**
>
> Two package managers in one project produce two lockfiles that disagree about the installed versions.

Read more about Yarn:

- [Yarn documentation](https://classic.yarnpkg.com/docs/)
- [Why Yarn?](https://classic.yarnpkg.com/en/docs/getting-started)

## Language

> **#1. TypeScript in version 5.9 or newer MUST be used.**
>
> TypeScript brings type safety to JavaScript, catching errors at compile-time rather than runtime. This significantly
> reduces bugs and improves developer experience with better IDE support and autocomplete.

> **#2. `strict` mode MUST be enabled in `tsconfig.json`.**

> **#3. `any` MUST NOT be used, and `@ts-ignore` MUST NOT be used without a comment that says why.**
>
> Both switch off the type checking that TypeScript is used for.

Read more about TypeScript:

- [TypeScript official documentation](https://www.typescriptlang.org/)
- [TypeScript handbook](https://www.typescriptlang.org/docs/handbook/intro.html)

## New Projects

> **#1. New projects MUST be created from the
> [Vite Project Boilerplate](https://github.com/gi-org-pl/vite-project-boilerplate).**
>
> The boilerplate already follows these standards, so a new project starts with the right stack, structure and
> tooling.

> **#2. New projects MUST declare the Node.js and Yarn versions above in the `engines` field of `package.json`.**
