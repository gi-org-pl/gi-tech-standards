# Structure

Keeping the project structure in a one, standardized manner is important. Developers in an organization often switch
between different projects, and a similar structure keeps things organized.

## Project types

Backend projects come in four types, and each type has its own structure:

| Type             | What it is                                                     | Example                        |
|------------------|----------------------------------------------------------------|--------------------------------|
| Service          | A Nest.js application that keeps running and serves an API     | mypolitics-survey-producer-api |
| Lambda function  | Code that AWS Lambda runs on an event, such as a queue message | mypolitics-survey-consumer     |
| CLI tool         | A program that people run in their own terminal                | mypolitics-data-exporter       |
| Scheduled script | A script that a GitHub Actions workflow runs on a schedule     | mypolitics-daily-report-bot    |

> **#1: Each project SHOULD follow the structure of its type.**

## Services

### Top-level structure

For repository structure for services developer SHOULD follow the standard, recommended by Nest.js structure.

On the top level, these directories are present in any running project:

```shell
.
├── .github/
├── dist/
├── docker/
├── infra/
├── node_modules/
├── prisma/
├── src/
└── test/
```

In the structure as above, each directory serves its own purpose:

- `.github` directory contains the GitHub workflows and other configuration files,
- `dist` contains the compiled application,
- `docker` contains the docker-related environment configuration and scripts,
- `infra` contains the OpenTofu configuration of the cloud resources the project runs on,
- `node_modules` contains the installed dependencies,
- `prisma` directory contains the database schema, database test data and generated database client.
- `src` directory contains the source code of the application,
- `test` contains the automated tests and the code required to run them.

> **#2: Other top-level directories MAY be added, if `README.md` or `AGENTS.md` describes what they hold.**

> **#3: The `dist` and `node_modules` directory MUST NOT be present in the repository.**

### Tests

Each test suite has its own directory in `test/`, for example `features` for functional tests, `optimization` for cache
tests and `performance` for performance tests. Feature files are grouped by module:

```shell
.
└── test/
    ├── _context/
    │   ├── features/
    │   └── optimization/
    ├── _helper/
    ├── features/
    │   ├── project/
    │   │   └── project.create.feature
    │   └── survey/
    │       └── survey.get.feature
    ├── optimization/
    └── performance/
```

- `_context` contains the step definitions, one directory per suite,
- `_helper` contains the code shared by the steps, such as matchers and fixtures.

> **#4: Tests MUST be kept in `test/<suite>/` directories.**
>
> Older projects with only one suite of functional tests MAY keep it in a top-level `features/` directory.

### Source code

Application source code is divided:

```shell
.
└── src/
    ├── core/
    ├── modules/
    ├── app.module.ts
    └── main.ts
```

Source code is divided into the following directories:

- `core` contains the core app features, that are not related to any specific module (domain),
- `modules` contains the application modules — the domain-specific features.

> **#5: Only `core/` and `modules/` directories SHOULD be present in the `./src/` directory.**

> **#6: No files SHOULD be present in the `./src/` directory directly, except for the `app.module.ts` and `main.ts` file.**

> **#7: Application entrypoint SHOULD be present in the `./src/` directory, and it SHOULD be named `main.ts`.**

> **#8: The `app.module.ts` file SHOULD be present in the `src` directory.**

#### Core

Core features are the features that are not related to any specific module.

#### Modules

Modules are the domain-specific features of the application. Each module should have its own directory and should be
responsible for a specific domain of the application.

An example directory structure looks like that:

```shell
.
└── src/
    ├── core/
    └── modules/
        ├── project/
        ├── result/
        └── survey/
```

> **#9: Directories under the `./src/modules` directory SHOULD be named after the domain they represent.**
>
> It is RECOMMENDED to use the singular form of the domain name, and it is also RECOMMENDED to use single-word names.

##### Minimal module structure

The simplest module should contain only the `<domain>.module.ts` file. All other directories and files are up for developer
consideration.

##### Recommended module structure (CQRS)

Once the module begins to be bigger and more complex, it is recommended to split it into DDD-like structure. Defining
`application`, `infra`, `model` layers is a good practice.

```shell
.
└── src/
    ├── core/
    └── modules/
        ├── project/
        ├── result/
        └── survey/
            ├── application/
            ├── infra/
            ├── model/
            ├── survey.module.ts
            └── survey.providers.ts
```

In this structure layers are defined as follows:

- `application` layer is responsible for commands and queries (CQRS), and for the handlers of domain events.
- `infra` layer is responsible for the close-to-metal actions: database read/write, cache, handling HTTP requests and so
  on.
- `model` layer is responsible for keeping the business decisions and data structures as a model, together with the
  domain errors.

The `<domain>.module.ts` file wires the module, and `<domain>.providers.ts` groups its actions, command handlers, query
handlers, repositories and event handlers into arrays that the module registers.

Request comes to an action in the `infra` layer (usually an HTTP request). The action sends a command or a query, which
is processed by the `application` layer that uses `model` to understand the logic of the domain. Database changes are
made by repositories in the `infra` layer, and then the action sends the response back to the client.

Fully operating domain may look like that:

```shell
.
└── src/
    ├── core/
    └── modules/
        ├── project/
        ├── result/
        └── survey/
            ├── application/
            │   ├── command/
            │   │   ├── create-survey.command.ts
            │   │   └── update-survey.command.ts
            │   ├── event/
            │   │   └── handler/
            │   │       └── survey-modified.handler.ts
            │   └── query/
            │       ├── get-survey-by-id.query.ts
            │       └── list-surveys.query.ts
            ├── infra/
            │   ├── cache/
            │   │   └── question.cache.ts
            │   ├── database/
            │   │   ├── question.repository.ts
            │   │   └── survey.repository.ts
            │   └── http/
            │       ├── action/
            │       │   ├── question/
            │       │   │   └── create-question.action.ts
            │       │   └── survey/
            │       │       ├── create-survey.action.ts
            │       │       └── get-survey.action.ts
            │       ├── request/
            │       │   └── survey.request.ts
            │       └── response/
            │           └── survey.response.ts
            ├── model/
            │   ├── error/
            │   │   └── survey.error.ts
            │   ├── question.model.ts
            │   └── survey.model.ts
            ├── survey.module.ts
            └── survey.providers.ts
```

Each HTTP endpoint has its own action class in `infra/http/action/<resource>/<verb>-<noun>.action.ts`. Older modules
still keep their endpoints in controllers in `infra/http/controller/`.

## Lambda functions

```shell
.
├── .github/
├── infra/
├── src/
│   ├── handler/
│   ├── infra/
│   ├── service/
│   └── types/
├── compose.yaml
├── Dockerfile
└── zip.sh
```

In the structure as above, each directory and file serves its own purpose:

- `.github` directory contains the GitHub workflows and other configuration files,
- `infra` contains the OpenTofu configuration of the function and the cloud resources it uses,
- `src/handler` contains the entry points that AWS Lambda calls, one file per function,
- `src/infra` contains the clients of other systems, such as the database or the logs,
- `src/service` contains the logic of the function, with its unit tests next to it in `*.spec.ts` files,
- `src/types` contains the shapes of the messages and records that the function works with,
- `Dockerfile` builds the code and exports it with the production dependencies,
- `zip.sh` packs the exported code into the zip package that AWS Lambda runs.

## CLI tools

```shell
.
├── .github/
├── bin/
├── src/
│   ├── application/
│   │   └── port/
│   ├── core/
│   ├── infra/
│   ├── model/
│   └── main.ts
├── test/
│   └── _helper/
└── compose.yaml
```

In the structure as above, each directory serves its own purpose:

- `.github` directory contains the GitHub workflows and other configuration files,
- `bin` contains the command that people run, registered in the `bin` field of `package.json`,
- `src/model` contains the business decisions and data structures, with the errors in `model/error/`,
- `src/application` contains the use cases (`*.use-case.ts`), and `port/` the interfaces they need from the outside
  world (`*.port.ts`),
- `src/infra` implements those interfaces: API clients, the terminal interface, files on disk and so on,
- `src/core` contains small helpers used by all layers,
- `src/main.ts` is the entry point that the command in `bin` starts,
- `test` mirrors the `src` directory with one `*.test.ts` file per source file, and `_helper` contains the code shared by
  the tests.

## Scheduled scripts

```shell
.
├── .github/
│   └── workflows/
│       └── daily_report.yaml
├── dashboard.js
├── index.js
└── package.json
```

A scheduled script is small, so its files are kept in the root directory:

- `.github/workflows` contains the workflow that runs the script on a schedule and passes the secrets to it,
- `index.js` is the entry point that the workflow runs,
- other files in the root directory, such as `dashboard.js`, contain the rest of the script.

Trees in this document were generated using [this tool](https://tree.nathanfriend.com).
