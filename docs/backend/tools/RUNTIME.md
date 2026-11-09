# Runtime

The following tools are selected for server-side apps:

- [Docker](https://www.docker.com/)
- [Node.js](https://nodejs.org/)
- [Nest.js](https://nestjs.com/)
- [PostgreSQL](https://www.postgresql.org/)

> **#0. Before starting a new project using different language or frameworks, a developer MUST have prior approval from
> the _Engineering_ team.**
>
> Do not feel anxious to ask for the approval. They are here to help, and they want to make sure that the best tools for
> the job are used.

## Docker

> **#1. Docker-based runtime environments MUST be used.**
>
> _“It works on my end”_ is a known joke and phrase that everyone in the IT industry heard at least once. To prevent
> this, **Docker** should be used to create development and production environments.
>
> Docker is a tool designed to make it easier to create, deploy, and run applications in different environments by using
> containers. Containers allow a developer to package up an application with all the parts it needs, such as libraries
> and other dependencies, and ship it all out as one package.

> **#2. How Docker is used depends on the [project type](../conventions/STRUCTURE.md#project-types).**
>
> - **Services** MUST run in Docker containers in development and production. By using virtualization, the code will
>   work in the same way on every machine: no matter if it is a developer's laptop or a production server.
> - **Lambda functions** and **CLI tools** MUST use Docker for development, and for the build if they have one. In
>   production, they run as the artifact their platform needs, such as a zip package for AWS Lambda.
> - **Scheduled scripts** MAY run without Docker, because the GitHub Actions workflow that runs them sets up Node.js
>   itself.

> **#3. Alpine Linux MUST be used as a base image for Docker containers.**

> **#4. Use standardized Dockerfile across different services.**
>
> Aim to maintain backend services almost identical when it comes to system configuration. One Dockerfile should be used
> as a standard across all the services. Take a look at these repositories to see how it is implemented:
>
> - [dzialaj-org-api](https://github.com/gi-org-pl/dzialaj-org-api/blob/main/Dockerfile)
> - [mypolitics-survey-producer-api](https://github.com/gi-org-pl/mypolitics-survey-producer-api/blob/main/Dockerfile)

> **#5. Use multi-stage builds to keep our images as small as possible.**
>
> This way we can reduce the time needed to build and push images to the registry. In a production environment we are
> using only production dependencies, without any development tools, test libraries, and other development-related
> packages.

> **#6. Framework default port MUST be exposed in the container.**
>
> For **Nest.js**, it is port `3000`. Do not change it, do not configure a custom port.

> **#7. Docker Compose MUST be used for local development of services, Lambda functions and CLI tools.**
>
> For services, Compose also ties the application together with the database and other services it needs.

Read more about Docker:

- [Docker (official docs)](https://docs.docker.com/)
- [Docker Compose (official docs)](https://docs.docker.com/compose/)

## Node.js & TypeScript

> **#1. A supported LTS version of Node.js MUST be used.**
>
> Use an LTS line that is still in active or maintenance support, today Node.js 24 or 26. New projects SHOULD start on
> the newest LTS line. LTS versions give access to modern JavaScript features, performance improvements and security
> fixes, and the [release schedule](https://github.com/nodejs/release#release-schedule) shows when each line stops
> getting them.

> **#2. For Node,`npm` package manager MUST be used.**

> **#3. TypeScript in version 6 or newer MUST be used.**
>
> Projects SHOULD use the newest TypeScript release.
>
> TypeScript brings type safety to JavaScript, catching errors at compile-time rather than runtime. This significantly
> reduces bugs and improves the developer experience with better IDE support and autocomplete.

> **#4. New projects SHOULD enable `strict` in `tsconfig.json`.**
>
> There is no shared `tsconfig.json`. Each project keeps its own, because a service, a Lambda function and a CLI tool
> need different compiler options. Strict mode catches the most errors at compile time, so new projects turn it on from
> the start. Existing projects MAY keep their current settings.

Read more about Node.js:

- [Node.js official documentation](https://nodejs.org/)
- [Node.js release schedule](https://github.com/nodejs/release#release-schedule)

Read more about TypeScript:

- [TypeScript official documentation](https://www.typescriptlang.org/)
- [TypeScript handbook](https://www.typescriptlang.org/docs/handbook/intro.html)

## Nest.js

> **#1. Services MUST use Nest.js in version 12.**

Read more about Nest.js:

- [Nest.js official documentation](https://docs.nestjs.com/)

## Databases

> **#1. For storing relational data, PostgreSQL in version 16 MUST be used.**
>
> **PostgreSQL** a powerful, open-source object-relational database system that uses and extends the SQL language
> combined with many features that safely store and scale the most complicated data workloads, while still keeping
> reasonable performance and cost-effectiveness.

> **#2. Ask for advice before using any other database engine.**
>
> To avoid unnecessary costs and additional complexity, do not use any other database engine than PostgreSQL.
>
> Feel free to ask for advice about what database engine to use for a new project. **Organization is open to using any
> other database engines if they fit the project requirements better than PostgreSQL**, but each decision must be
> consulted by the **_Engineering_** team before proceeding.

> **#3. Services MUST use Prisma ORM for the database access layer.**
>
> Lambda functions MAY use the [`pg`](https://node-postgres.com/) client directly.

> **#4. Projects that use Prisma MUST install Prisma in version 7.**

> **#5. Prisma client MUST be kept in `prisma/client/` directory.**

> **#6. Prisma config MUST be kept in `prisma.config.ts` file in root project directory.**
>
> [See standardized prisma.config.ts file](https://github.com/oskarbarcz/flight-tracker-api/blob/main/prisma.config.ts).

Read more about Prisma:

- [Prisma (official docs)](https://www.prisma.io/docs)
