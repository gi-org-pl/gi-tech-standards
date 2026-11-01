# Backend standards

Welcome to organization backend standards.

## Learning

The learning curve for backend developers is steep. There are plenty of things a modern backend developer should be
 aware of to develop safe, scalable and reliable server-side applications.

> Set of materials is provided to help developers learn the basics of backend development. Check them and get back here
> often to refresh knowledge.
>
> [Read more about the learning curve](/docs/backend/LEARNING.md)

## Tools

Basic languages, libraries, frameworks and tools that are used in the projects, organized by the category:

> **Runtime** refers to the software layer that makes execution possible — the infrastructure sitting between the code
> and the operating system.
>
> [Read more about runtime tools](/docs/backend/tools/RUNTIME.md)

> **Code quality** is a set of practices that help keep the code maintainable and readable. Organization should strictly
> follow common practices to ensure standarization of the code.
>
> [Read more about code quality tools](/docs/backend/tools/CODE_QUALITY.md)

> **Testing** is a crucial part of developing stable, regression-free server apps. Organization should maintain highest
> standards of testing to ensure that the code is working properly for all the edge cases.
>
> [Read more about testing tools](/docs/backend/tools/TESTING.md)

> **CI/CD** _(Continuous Integration, Continuous Delivery)_ refers to the software layer that checks if the code is
> working properly and if it can be deployed to production.
>
> [Read more about CI/CD tools](/docs/backend/tools/CI_CD.md)

## Security

Rules that protect our services and the data they hold apply to every backend project.

> **Security** covers secrets, pipelines, dependencies, containers, infrastructure, application code and personal data.
>
> [Read more about security standards](/docs/security/INDEX.md)

## Conventions

Set of practices that are used to ensure that the code, but also all processes around it are consistent and
maintainable.

> **RFC** tells how certain keywords should be understood when used in other technical documents.
>
> [Read more about RFC](/docs/backend/conventions/RFC.md)

> **Code owners**
>
> Setting code owners for directories and files is a good practice to automatically summon reviewers and catch the
> attention of other developers when pull requests are created.
>
> [Read more about code owners convention](/docs/backend/conventions/CODE_OWNERS.md)

> **Naming**
>
> [Read more about naming convention](/docs/backend/conventions/NAMING.md)

> **Structure**
>
> Keeping the project structure in a one, standardized manner is important. Developers in an organization often switch
> between different projects, and a similar structure keeps things organized.
>
> [Read more about structure convention](/docs/backend/conventions/STRUCTURE.md)

## Decision log

Organization is using a set of tools to make conscious decisions about the technology stack chosen for the project.
Organization put a lot of effort into documenting those decisions and making them available for everyone to read. Below
is a list of organization-wide cases.

- [001: Use TypeScript as a primary language](/docs/backend/decisions/001-use-typescript-as-primary-language.md)
