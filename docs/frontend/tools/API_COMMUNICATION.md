# API Communication

## HTTP Client

> **#1. HTTP requests MUST be made with Axios, not with `fetch`.**
>
> Axios provides a clean, promise-based API for making HTTP requests. It includes built-in request/response
> interceptors, automatic JSON transformation, and better error handling compared to the native fetch API.

> **#2. Authentication and error handling SHOULD be done in Axios interceptors.**
>
> This way every request gets them without repeating the code. Interceptors are kept in `utils/` of the API client
> (see [project structure](../conventions/PROJECT_STRUCTURE.md)).

- [Axios documentation](https://axios-http.com/)
- [Axios GitHub repository](https://github.com/axios/axios)

## Data Validation

> **#1. Every API response MUST be validated with a Zod schema.**
>
> Zod is a TypeScript-first schema validation library. It allows us to validate API responses at runtime, ensuring
> type safety and catching data inconsistencies early.

> **#2. TypeScript types of API data SHOULD be derived from the Zod schemas with `z.infer`.**
>
> This way the type and the validation cannot drift apart.

- [Zod documentation](https://zod.dev/)
- [Zod GitHub repository](https://github.com/colinhacks/zod)
