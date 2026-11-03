# Naming

There are two things hard in programming: cache invalidation and naming things. Organization follows certain rule on
 naming to prevent confusion.

## TypeScript & Nest.js

> **#1. All TypeScript files MUST be named with the `.ts` extension.**

> **#2. File names SHOULD be in lowercase kebab-case.**
>
> Projects should follow the Nest.js convention for file naming, which is widely adopted in the TypeScript community.
>
> In this approach template is defined: `<name>.<type>.ts`, where `<name>` is the name of the resource, and
> `<type>` is the NestJS type suffix. Examples:
>
> - `user.module.ts`
> - `organization.service.ts`
> - `offer.controller.ts`
> - `create-role.request.ts`
> - `survey.model.ts`
>
> Simple files containing only functions MAY be named without the `<type>`, examples:
>
> - `errors.ts`
> - `constants.ts`
> - `utils.ts`
> - `main.ts`

> **#3. Named export MUST be used, default export MUST NOT be used.**
>
> Config files are the exception, when their tool requires a default export, such as `eslint.config.mjs`,
> `prisma.config.ts` or `cucumber.js`.

> **#4. All TypeScript classes, enums, interfaces and types MUST follow the PascalCase naming convention.**
>
> Element name must reflect both the resource and the type, examples:
>
> - `UserModule`
> - `OrganizationService`
> - `OfferController`
> - `CreateRoleRequest`
>
> Model classes are the exception, and they are named after the bare entity, such as `Survey` or `Project`.

> **#5. All TypeScript consts and functions MUST follow the camelCase naming convention.**
>
> Element name must reflect both the resource and the type, for example:
>
> - `createUser()`
> - `configKey`
> - `token`
>
> Provider arrays, dependency injection tokens and module-level constants MAY follow the UPPER_SNAKE_CASE naming
> convention instead, for example:
>
> - `COMMAND_HANDLERS`
> - `RESULT_WRITER`
> - `TOO_MANY_REQUESTS_MESSAGE`

> **#6. Directories that group related NestJS artifacts SHOULD use the resource name in kebab-case.**
>
> Directories that group related artifacts with the same type SHOULD be named after the type they represent, in
> lowercase kebab-case and in singular form. Examples:
>
> - `user/`
> - `order/`
> - `modules/user-role/infra/http/request`

> **#7. Function SHOULD be written with `function` keyword, arrow functions SHOULD be used only as callbacks.**
>
> ```ts
> // Good
> function createUser(id: string) {}
> 
> // Bad
> const createUser = (id: string) => {}
> 
> // Good
> array.map(item => item.id);
> array.map((item, index) => `${item.id} ${index}`);
> ```

## Cucumber.js

> **#1. Gherkin file MUST be named with the `.feature` extension.**

> **#2. Gherkin file name MUST be in lowercase kebab-case.**
>
> Projects should also follow the Nest.js convention for file naming for gherkin files.
>
> In this approach template is defined: `<domain>.<action>.feature` template for the name, where `<domain>` is the
> application domain, and `<action>` is the action name. Examples:
>
> - `user.create.feature`
> - `organization.revoke-license.feature`
> - `user-role.copy.feature`

> **#3. Scenario names MUST be a sentence, and MUST follow the user story approach.**
>
> User stories are a way to describe the behavior of a system. They are written in plain English and are used to define
> the requirements. They are a way to communicate the intent of the system to the users.
>
> User stories are written in the form of a sentence, examples:
>
> - `As an admin I can remove a user from the organization`
> - `As a user I can create a new organization`
> - `As an admin I cannot update user role for non-existing user`

> **#4. Scenario names MUST NOT be repeated in one test file.**
