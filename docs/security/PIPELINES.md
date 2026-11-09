# Pipelines

The [CI/CD standards](../backend/tools/CI_CD.md) say which actions a workflow can use and how to pin them. The rules
below say what a job can do once it runs, and what protects the branch it runs from.

## Workflows

> **#1. Every job MUST set its own `permissions`, with only what it needs.**
>
> A job without this block gets the default of the repository. If its code is compromised, the token decides how much
> damage it can do.
>
> ```yaml
> jobs:
>   build:
>     permissions:
>       contents: read
>       packages: write
> ```
>
> The permissions that our jobs usually need:
>
> | The job has to               | Permission             |
> | ---------------------------- | ---------------------- |
> | Read the code                | `contents: read`       |
> | Push a tag, create a release | `contents: write`      |
> | Push an image to ghcr.io     | `packages: write`      |
> | Comment on a pull request    | `pull-requests: write` |

> **#2. The default workflow permission of a repository MUST be read.**
>
> Set it in _Settings_ > _Actions_ > _General_ > _Workflow permissions_. Do it after every job sets its own
> `permissions`, because jobs that rely on the write default fail after the switch.

> **#3. A job that runs pull request code and holds a write token MUST check out with `persist-credentials: false`.**
>
> By default, `actions/checkout` leaves the token in `.git/config`, where the code under test can read it.
>
> ```yaml
> - uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6.1.0
>   with:
>     persist-credentials: false
> ```

> **#4. Images deployed to production MUST be built without the Docker cache, from a freshly pulled base image.**
>
> Self-hosted runners keep their Docker cache between jobs. A layer like `RUN npm ci`, cached by a pull request job,
> could otherwise end up in the production image. The build gets slower, and that is the price.
>
> ```shell
> docker build --pull --no-cache --target production -t "${IMAGE}:${VERSION}" .
> ```

## Repository settings

> **#1. The default branch MUST be protected.**
>
> A change reaches it only through a pull request with at least one approval, a review of the code owners and an
> approval of the last push. Force pushes and deleting the branch are blocked. Our organization rulesets do this, so
> check that a new repository is covered by them.

> **#2. Release tags MUST NOT be movable.**
>
> Merging to `main` creates a tag with the version, and that tag names the image that gets deployed. A ruleset on the
> `*.*.*` tags blocks updating and deleting them.

> **#3. Forking MUST be turned off in private repositories.**
>
> A fork is a copy of the code that the settings of the original repository no longer protect.

Read more about pipelines:

- [Secure use of GitHub Actions](https://docs.github.com/en/actions/reference/security/secure-use)
