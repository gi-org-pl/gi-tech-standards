# Naming

Our naming convention comes from the approach we already use in our code.

## Convention

> **#1. Functions and variables MUST be named in camelCase, and React components in PascalCase.**
>
> This follows the standard of JavaScript and React.

> **#2. Files and directories MUST be named as in the table below. Anything the table does not list MUST be named in
> kebab-case.**

| Entity              | Pattern               | Example                                            |
|---------------------|-----------------------|----------------------------------------------------|
| Domain directory    | `kebab-case`          | `user-profile/`                                    |
| Component directory | `PascalCase`          | `UserProfileCard/`                                 |
| Any other directory | `kebab-case`          | `utils/`, `schemas/`                               |
| Component file      | `PascalCase.type.ext` | `UserProfileCard.tsx`, `UserProfileCard.types.ts`  |
| Asset               | `kebab-case.ext`      | `arrow-right.svg`, `hero-banner.jpg`               |
| Util or hook        | `camelCase.ext`       | `formatCurrency.ts`, `useDebounce.ts`              |
