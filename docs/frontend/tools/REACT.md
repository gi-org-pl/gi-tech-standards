# React-related Packages

## UI Library

> **#1. React in version 19 or newer MUST be used.**
>
> React is the industry standard for building user interfaces. Its large ecosystem and community make it an ideal
> choice for maintainable projects.

- [React official documentation](https://react.dev/)

## Build Tool

> **#1. Vite in version 7 or newer MUST be used.**
>
> Vite provides lightning-fast development server startup and hot module replacement (HMR). It uses native ES modules
> in development and Rollup for production builds, resulting in optimal performance and developer experience.

- [Vite official documentation](https://vite.dev/)
- [Why Vite?](https://vite.dev/guide/why.html)

## Design System Documentation

> **#1. Every component in `src/components/shared/` MUST have a Storybook story.**
>
> Storybook allows us to develop and document UI components in isolation. It serves as a living style guide and helps
> ensure component consistency across the application. This is especially valuable in projects with multiple
> developers.

- [Storybook documentation](https://storybook.js.org/)
- [Storybook tutorials](https://storybook.js.org/tutorials/)

## Routing

> **#1. React Router in version 7.9 or newer MUST be used in Framework Mode.**
>
> React Router 7 introduces framework mode, which provides a more integrated routing experience similar to Next.js or
> Remix. This mode offers better data loading, error handling, and overall developer experience while maintaining the
> flexibility of React Router.

- [React Router documentation](https://reactrouter.com/)
- [React Router framework mode guide](https://reactrouter.com/en/main/start/overview#framework-mode)

## Styling

> **#1. Tailwind CSS in version 4 or newer MUST be used.**
>
> Tailwind CSS brings a modern utility-first approach to styling with improved performance, better developer
> experience, and a more intuitive API. It allows for rapid UI development while maintaining consistency and reducing
> CSS bundle size through intelligent purging.

> **#2. Custom CSS SHOULD NOT be written. When it cannot be avoided, the pull request MUST say why.**
>
> Tailwind utilities cover almost every case, and every custom CSS file is one more place to look for styles.

- [Tailwind CSS documentation](https://tailwindcss.com/)
