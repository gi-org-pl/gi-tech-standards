# Component structure

## Convention

> **#1. Encapsulation: types, utils, constants and subcomponents used by only one component MUST be kept in its
> directory.**
>
> Once another component uses them, they are treated as globals and move to the global directories (see
> [project structure](PROJECT_STRUCTURE.md)).

> **#2. Minimization: files and directories from the structure below MUST be created only when they are needed.**
>
> A component without its own types does not get an empty `ComponentName.types.ts`.

> **#3. Mirroring: component directories MUST mirror the real structure of the components.**
>
> The directory of a subcomponent is kept inside the directory of its parent.

## Structure

```txt
|- [ComponentName]
    |- ComponentName.tsx               # View file
    |- ComponentName.test.ts           # Unit tests
    |- ComponentName.types.ts          # Component-related types
    |- ComponentName.constants.ts      # Component-related constants
    |- [utils]                         # Component-related utils/hooks
        |- getSomeData.ts
        |- getSomeData.test.ts
    |- [SubComponent]                  # Subcomponent directory
    |- [OtherSubComponent]             # Subcomponent directory
```
