# CI/CD

A pipeline has access to everything: the code, the secrets and the production servers. That is why the code that runs
in it has to be chosen as carefully as the code of the application itself.

Organization uses [GitHub Actions](https://github.com/features/actions) for all CI/CD pipelines. Workflows are kept in
the `.github/workflows/` directory of each repository.

## Using actions

An action is a ready-made step that a workflow can use, like `actions/checkout` that checks out the repository.

> **#1. Workflows MUST use only official actions published by GitHub or big, well-known companies, or our own
> actions.**
>
> An action is someone else's code, and it runs on our computer. Our jobs run on self-hosted runners, on machines owned
> by the organization, like the GI Mac mini. Every action in a job can read the code, the secrets passed to the job and
> the GitHub token, and it can reach everything the runner can reach.
>
> Actions that can be used:
>
> - actions published by GitHub: `actions/*`, such as `actions/checkout` or `actions/setup-node`,
> - actions published by the company behind the tool, such as `docker/*`, `aws-actions/*` or `opentofu/*`,
> - our own actions: `gi-org-pl/*`.

> **#2. Actions published by individual developers or small vendors MUST NOT be used.**
>
> Even a popular action with thousands of stars is often maintained by one person, and one bad release is enough to
> run anything on our machines. In March 2025 the `tj-actions/changed-files` action, used in over 23,000
> repositories, was taken over and printed the secrets of its users into the job logs.
>
> If there is no official action for the job, create our own. Most of them are a few lines of shell anyway.

> **#3. Before using an action of a company that is not listed above, a developer MUST have approval from the
> _Engineering_ team.**
>
> Do not feel anxious to ask. Usually it takes one message to get the answer.

## Creating actions

When the same steps are copied between repositories, or there is no official action for the job, organization creates
its own action. Take a look at the existing ones before creating a new one:

- [check-crlf-action](https://github.com/gi-org-pl/check-crlf-action)
- [check-file-permissions-action](https://github.com/gi-org-pl/check-file-permissions-action)
- [check-version-action](https://github.com/gi-org-pl/check-version-action)
- [report-tofu-plan-action](https://github.com/gi-org-pl/report-tofu-plan-action)

Each action repository is structured in the same way:

```shell
.
├── .github/
│   ├── workflows/
│   │   └── test.yaml
│   └── CODEOWNERS
├── .gitignore
├── action.yaml
├── check-version.sh
├── LICENSE
└── README.md
```

In the structure as above, each file serves its own purpose:

- `.github/workflows/test.yaml` runs the tests of the action on every pull request,
- `.github/CODEOWNERS` assigns all files to the `@gi-org-pl/admins` team,
- `action.yaml` defines the action: its name, description, inputs and steps,
- `check-version.sh` is the script with the logic, named after the action,
- `LICENSE` contains the MIT license,
- `README.md` describes how to use the action.

> **#1. Each action MUST be kept in a separate, public repository in the `gi-org-pl` organization.**
>
> One repository, one action. This way each action has its own versions, README and issues. Public actions can be used
> by all our projects, also the private ones, without any additional access settings.

> **#2. Action repository name MUST be in lowercase kebab-case and MUST end with `-action`.**
>
> Name should tell what the action does, examples:
>
> - `check-version-action`
> - `report-tofu-plan-action`

> **#3. Actions MUST NOT contain any secrets or configuration of our infrastructure.**
>
> Remember that the repository is public. Tokens, URLs and other values are passed by the workflow as inputs.

> **#4. Composite actions SHOULD be used.**
>
> Steps are defined in `action.yaml` with `using: composite`, and the logic is kept in one shell script next to it.
> If shell is not enough, for example to call the GitHub API, write the script in JavaScript and run it with
> `actions/github-script`. This way there is no build step, and no `node_modules` or `dist` directory in the repository.
>
> - [Shell script example (check-version-action)](https://github.com/gi-org-pl/check-version-action/blob/main/action.yaml)
> - [JavaScript example (report-tofu-plan-action)](https://github.com/gi-org-pl/report-tofu-plan-action/blob/main/action.yaml)

> **#5. Action MUST be defined in `action.yaml` file, not in `action.yml`.**
>
> Definition MUST contain `name`, `description`, `author: gi-org-pl` and a description of each input. If a description
> contains a colon, put it in quotes, otherwise GitHub fails to load the whole action.

> **#6. README MUST describe the requirements, usage, inputs and an example workflow.**
>
> [See README of check-version-action](https://github.com/gi-org-pl/check-version-action/blob/main/README.md).

> **#7. Action SHOULD be tested in its own repository.**
>
> The best test is to run the action for real. Test workflow in the action repository uses the action with
> `uses: ./`, so every pull request is checked before anything is released.
>
> [See test workflow of report-tofu-plan-action](https://github.com/gi-org-pl/report-tofu-plan-action/blob/main/.github/workflows/test.yaml).

> **#8. Action MUST be released with two tags: full version `v1.2.3` and major version `v1`.**
>
> Projects use the major tag, for example `gi-org-pl/check-version-action@v1`, so they get fixes without changing
> their workflows. Each full version gets its own GitHub release. After the release, move the major tag to the new
> version:
>
> ```shell
> git tag v1.2.3 && git push origin v1.2.3
> git tag -f v1 v1.2.3 && git push -f origin v1
> ```
>
> A breaking change, like a removed or renamed input, MUST be released as a new major version (`v2`).

> **#9. Action MUST be licensed under the MIT license.**
>
> `LICENSE` file MUST contain the full license text, with `Fundacja Generacja Innowacja` as the copyright holder.

Read more about GitHub Actions:

- [GitHub Actions (official docs)](https://docs.github.com/en/actions)
- [Creating a composite action](https://docs.github.com/en/actions/tutorials/create-actions/create-a-composite-action)
- [Metadata syntax for actions](https://docs.github.com/en/actions/reference/workflows-and-actions/metadata-syntax)
- [Secure use of GitHub Actions](https://docs.github.com/en/actions/reference/security/secure-use)
