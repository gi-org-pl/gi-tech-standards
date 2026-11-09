# Dependencies

Every package, action and base image is code written by someone else that runs on our machines. Most of it can be
trusted, but all of it has to be kept up to date and watched.

> **#1. Dependabot MUST be configured for every package ecosystem used in the repository.**
>
> That usually means `npm`, `github-actions` and `docker`. Dependabot alerts MUST be turned on in the repository
> settings as well. A daily schedule with one group keeps it to a single pull request:
>
> ```yaml
> version: 2
>
> multi-ecosystem-groups:
>   dependencies:
>     schedule:
>       interval: daily
>
> updates:
>   - package-ecosystem: npm
>     directory: /
>     patterns: ['*']
>     multi-ecosystem-group: dependencies
>   - package-ecosystem: github-actions
>     directory: /
>     patterns: ['*']
>     multi-ecosystem-group: dependencies
>   - package-ecosystem: docker
>     directory: /
>     patterns: ['*']
>     multi-ecosystem-group: dependencies
> ```

> **#2. Images MUST be built with `npm ci`.**
>
> `npm ci` installs exactly what `package-lock.json` says and fails if the lock file does not match `package.json`.
> `npm install` can resolve to a newer version than the one that was reviewed.

> **#3. A vulnerable package that cannot be updated directly SHOULD be fixed with `overrides`.**
>
> When the vulnerable version comes from a dependency of a dependency, `overrides` in `package.json` selects a fixed
> version for it. Keep an override only as long as it is needed, because it also stops that package from being updated
> with its parent:
>
> ```json
> {
>   "overrides": {
>     "multer": "^2.5.0"
>   }
> }
> ```

> **#4. Packages that run install scripts MUST be reviewed and listed in `allowScripts`.**
>
> An install script runs with the permissions of whoever installs the package, on a laptop or on a runner, so a
> malicious package can use one to steal tokens. List an approved package with its exact version, so an update has to be
> approved again, and deny the scripts that are not needed:
>
> ```json
> {
>   "allowScripts": {
>     "@prisma/engines@7.10.1": true,
>     "unrs-resolver": false
>   }
> }
> ```
>
> Run `npm install-scripts ls` to review new entries. By default, npm only warns about a package that is not listed, and
> still runs its script. Treat that warning as a failure. `strict-allow-scripts=true` in `.npmrc` SHOULD be used to make
> npm stop the installation instead.

Read more about dependencies:

- [Dependabot options reference](https://docs.github.com/en/code-security/dependabot/working-with-dependabot/dependabot-options-reference)
- [npm config](https://docs.npmjs.com/cli/v11/using-npm/config)
