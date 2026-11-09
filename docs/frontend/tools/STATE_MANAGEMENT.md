# State Management

## Primary Strategy: React Context + useState

> **#1. State SHOULD be kept with React's `useState` and shared with `useContext`.**
>
> This approach is simple, requires no additional dependencies, and is sufficient for most applications. We prefer
> this for:
>
> - global application state (theme, user preferences),
> - shared state between closely related components,
> - simple state that doesn't require complex logic.

## Secondary Strategy: Zustand

Zustand is a lightweight state management solution that provides:

- minimal boilerplate,
- better performance than Context for frequently updated state,
- simple API that's easy to learn and use,
- TypeScript support out of the box.

> **#1. Zustand SHOULD be used only when Context is not enough, in one of these cases:**
>
> - state is updated so often that Context re-renders hurt performance,
> - complex global state with multiple actions,
> - state that needs to persist across sessions,
> - state that requires middleware (logging, persistence, devtools).

> **#2. A pull request that adds a Zustand store SHOULD say in its description which of these cases applies.**

## Resources

- [Zustand documentation](https://zustand-demo.pmnd.rs/)
- [Zustand GitHub repository](https://github.com/pmndrs/zustand)
- [React Context API documentation](https://react.dev/reference/react/useContext)
