# Secrets

A secret is anything that gives access to something: a token, a password, a private key or a database URL. The rules
below cover the three moments that matter: when a secret is stored, when someone could see it, and when it has to be
replaced.

## Storing secrets

> **#1. Secrets MUST NOT be committed to a repository.**
>
> `.env` files, `*.tfvars` files, and OpenTofu state and plan files MUST be listed in `.gitignore`. The committed
> `.env.dist` file holds only values that work locally, like `local-env-admin-token`.

> **#2. Files that hold secrets MUST be listed in `.dockerignore`.**
>
> `COPY . .` puts everything that is not excluded into the image, and anyone who can pull the image can read it. Exclude
> at least `.env`, `.git/` and `infra/`. Local containers still see these files through the bind mount.

> **#3. Local images MUST NOT use the name of the production image.**
>
> With the production name, one mistaken `docker compose push` publishes a local image, with whatever it contains, and
> overwrites `latest`. A name without a registry, like `my-service:dev`, cannot be pushed there.

> **#4. Application secrets MUST be kept in Parameter Store as `SecureString`. Secrets Manager SHOULD be used only for
> secrets that AWS services read themselves.**
>
> Examples of the second kind are the database credentials read by RDS Proxy and the registry credentials read by ECS
> to pull a private image. Everything else fits in Parameter Store, which costs less.

> **#5. Containers MUST receive secrets through `secrets` in the task definition, not through `environment`.**
>
> Values in `environment` can be read by anyone who can describe the task definition. With `secrets`, the task
> definition holds only a reference:
>
> ```hcl
> secrets = [
>   { name = "ADMIN_TOKEN", valueFrom = aws_ssm_parameter.admin_token.arn },
> ]
> ```

> **#6. A role that reads secrets MUST list each of them by ARN.**
>
> A wildcard gives the service every secret in the account, including those of other services.

> **#7. Organization secrets MUST be limited to the repositories that use them.**
>
> Set the repository access of the secret to _Selected repositories_. Otherwise every repository in the organization
> can read it, including those that accept code from volunteers.

## Keeping secrets out of sight

> **#1. Secrets MUST NOT be shared with AI tools, or put in a chat, an issue or a pull request.**
>
> An AI tool sends what it reads to an external service and keeps it in a transcript. This includes letting an agent
> open `.env` or `*.tfvars` files, or run a command that prints a secret. Read more about
> [using AI](../ai/REFLECTIVE_AI_USAGE.md).

> **#2. A secret seen anywhere it should not be MUST be rotated.**
>
> That means a log, an AI session, a chat, a commit or an image. Deleting the message or the commit does not help,
> because nobody knows who read it or where it was copied. Do not wait for a sign that someone used it.

## Rotating secrets

> **#1. Changing a secret MUST replace the running tasks.**
>
> ECS reads secrets once, when a container starts. The task definition holds only a reference, which stays the same when
> the value changes, so OpenTofu sees nothing to deploy and the running tasks keep the old value.
>
> Add every secret to `triggers` on the service, as a hash of its variable:
>
> ```hcl
> resource "aws_ecs_service" "app" {
>   # ...
>
>   force_new_deployment = true
>   triggers = {
>     admin_token = sha256(var.admin_token)
>   }
> }
> ```
>
> A trigger MUST be known at plan time. An attribute like `aws_ssm_parameter.admin_token.version` is known only after
> the apply, and the apply fails with `Provider produced inconsistent final plan` after it has already changed the
> secret. The hash of a sensitive variable stays sensitive, so it does not show up in plans posted on pull requests.
>
> A secret that the task definition does not reference, like the registry credentials, also goes to `depends_on` of the
> service. This way the new value is written before the service is updated.

> **#2. A deploy workflow SHOULD be able to apply changed secrets without a release.**
>
> Rotation should not use up a version or wait for a build. Let the workflow be started by hand, and skip the release
> and the image build in that case:
>
> ```yaml
> on:
>   push:
>     branches: ['main']
>   workflow_dispatch:
>
> jobs:
>   tag:
>     if: github.event_name == 'push'
>     # ...
>   build:
>     needs: 'tag'
>     # ...
>   deploy:
>     needs: 'build'
>     if: github.ref == 'refs/heads/main' && !failure() && !cancelled()
>     # ...
> ```
>
> The `github.ref` check protects from a mistake, not from an attacker, because a branch can change its own workflow.
>
> Set the secret without `--body`, so the value stays out of the shell history, and then start the workflow:
>
> ```shell
> gh secret set MY_SECRET
> gh workflow run deploy.yaml --ref main
> ```

> **#3. The old credential MUST be revoked only after the new one works, and the result MUST be checked where the
> credential is used.**
>
> The order is: create the new credential, set the secret, deploy, confirm that the service works, and revoke the old
> credential. A successful deploy is not always enough. For example, refreshing a Cloudflare Tunnel token stops new
> connections with the old token, but connectors that are already connected stay connected. After the rotation, the
> tunnel MUST show only our own connectors. If there is any other,
> [delete all connections](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/configure-tunnels/remote-tunnel-permissions/)
> and treat the token as stolen.

Read more about secrets:

- [Using secrets in GitHub Actions](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)
- [Passing secrets to ECS containers from Parameter Store](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/secrets-envvar-ssm-paramstore.html)
