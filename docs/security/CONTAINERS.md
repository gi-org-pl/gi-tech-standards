# Containers

Assume that one day someone finds a way to run code in the application. These rules decide what they can do next.

## Building images

> **#1. The production image MUST run as an unprivileged user, from its own working directory.**
>
> Set both in the `production` stage. A `USER` set in the `build` stage does not reach a `production` stage that starts
> from the base image, so that image still runs as root, from `/`.
>
> ```dockerfile
> FROM alpine-node-base AS production
> WORKDIR /app
> COPY --chown=node:node --from=build /app/node_modules ./node_modules
> COPY --chown=node:node --from=build /app/dist ./dist
> USER node
> ENTRYPOINT ["./docker/prod/entrypoint"]
> ```

> **#2. The production image MUST NOT contain tools that it does not need.**
>
> Every tool in the image is also a tool for an attacker. Install things like `curl` only in the `development` stage.
> A health check can use `wget` from BusyBox, which is already in Alpine.

> **#3. Base images and images of third parties MUST be pinned by digest.**
>
> A tag can be pushed again, while a digest always points to the same content. Dependabot updates the digest.
>
> ```dockerfile
> FROM node:26.12-alpine@sha256:40cd011b55415bc894e45b02fdd5a5dfde056921b7d23a64c74f80497af48797 AS alpine-node-base
> ```
>
> Pin the digest of the multi-arch index, so the image exists for the platform we run on. The ECS documentation lists
> `image:tag` and `image@digest`, so keep the version in the description of the variable:
>
> ```hcl
> variable "cloudflared_image" {
>   description = "cloudflare/cloudflared 2026.10.7, pinned by the digest of its multi-arch image index"
>   type        = string
>   default     = "cloudflare/cloudflared@sha256:4955524aeaa379e154023d5a027c250f7b35041a2e7e950cf13f144bc9b9c5ba"
> }
> ```

## Running containers

> **#1. Every container MUST run with a read-only file system and without Linux capabilities.**
>
> This applies to sidecars too. An attacker cannot then change the application on disk, or use capabilities that a web
> service never needs.
>
> ```hcl
> readonlyRootFilesystem = true
> linuxParameters = {
>   capabilities = { drop = ["ALL"] }
> }
> ```

> **#2. The production image SHOULD be tested under the same restrictions.**
>
> A job that runs the production image with the same settings fails as soon as the application starts writing somewhere
> new, instead of finding out during the deploy:
>
> ```yaml
> app-perf:
>   read_only: true
>   cap_drop: ['ALL']
>   tmpfs: ['/app/output']
> ```

> **#3. A failed start-up step MUST stop the container.**
>
> Start the entrypoint with `set -e`. Otherwise a failed migration, or a database certificate that cannot be verified,
> is only logged and the application starts anyway. The health check passes, and every query fails. When the container
> stops, the deployment gets rolled back instead.
>
> ```shell
> #!/usr/bin/env sh
> set -e
>
> npm run database:migrate
> npm run start:prod
> ```

Read more about containers:

- [Docker security cheat sheet (OWASP)](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
