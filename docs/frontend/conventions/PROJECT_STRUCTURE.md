# Project structure

## Convention

> **#1. Projects MUST follow the structure below.**
>
> New top-level directories MUST NOT be added without the approval of the Technical Leader.

> **#2. Domain code MUST be kept apart from global code.**
>
> A component used by one domain lives in `src/components/[domain-name]/`. It moves to `src/components/shared/` once
> two or more domains use it.

> **#3. Code reused across domains MUST be easy to find.**
>
> Utils, types and constants used by more than one domain belong in `src/utils/`, `src/types/` and `src/constants/`,
> not next to a single component.

> **#4. API clients MUST be encapsulated in `src/services/[api-name]/`.**
>
> Pages and components MUST NOT create Axios instances or call Axios directly. They use the client from
> `src/services/[api-name]/client/`.

## Structure

```txt
|- public                               # Non-functional static assets (thumbnail, favicon etc.)
|- e2e
    |- [domain-name]                    # E2E domain
        |- path-name.spec.ts            # Path E2E test
|- src
    |- pages                            # Pages components directory
    |- components                       # React components
        |- shared                       # Components shared/reusable across domains
            |- [ComponentName]          # Individual shared component
        |- [domain-name]                # Domain-specific components (eg. home, admin)
            |- [ComponentName]          # Individual domain component
            |- [OtherComponent]         # Individual domain component
    |- services                         # API clients
        |- [api-name]                   # Individual API client directory (eg.: api, cms)
            |- [schemas]                # Data entries schema models
            |- [client]                 # Client's config
            |- [utils]                  # Client's utils (eg.: interceptors)
    |- constants                        # Constants domains
        |- domain-name.ts               # Individual constants domains (eg.: common, user, config, quiz)
    |- types                            # Global types
        |- domain-name.ts               # Individual types domains (eg.: common, user, config, quiz)
    |- utils                            # Global utils domains
        |- [domain-name]                # Single utils domain (eg.: number, text, object)
            |- transformNumber.ts
            |- transformNumber.test.ts
    |- assets                           # Static assets
        |- icons                        # Vector/icons files (SVG)
        |- images                       # Image files (JPG, PNG, etc.)
```
