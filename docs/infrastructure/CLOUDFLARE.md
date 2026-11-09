# Infrastructure: Cloudflare

*All our domains and the rest of our Cloudflare account are managed as code. Only admins change them.*

## What is managed this way

Everything in our Cloudflare account, including:

* domains and their DNS records (a new subdomain for your app is a DNS record too),
* redirects, cache rules, configuration rules and the SSL settings of each domain,
* Zero Trust: Access applications and policies (who can sign in to a protected app) and service tokens,
* tunnels and their public hostnames,
* R2 buckets, Turnstile widgets and Web Analytics,
* members of the account.

## How to request a change

1. Ask one of the admins (the `@gi-org-pl/admins` team) and tell them what should change and why. For a DNS record,
   give its name, type and value, and say whether it should go through the Cloudflare proxy.
2. The admin makes the change in a dedicated private repository and opens a pull request there. The pull request
   shows exactly what will change in Cloudflare.
3. Once the pull request is reviewed and merged, the change is applied automatically.

**Do not change anything by hand in the Cloudflare dashboard**, even if your access lets you. A nightly check reports
every manual change and everything created outside the repository, and the next applied change reverts changes to the
managed settings.

## Exceptions

* **Workers** are deployed with Wrangler from the repository of the project they belong to, together with their
  routes, triggers and secrets. The buckets and Access applications they use are still in the dedicated repository.
* **Tunnel tokens** stay in the secrets of the project that runs the tunnel.
* **Bot protection** (Bot Fight Mode, AI bot blocking) cannot be managed this way. Only admins change it, in the
  dashboard.
* **Page Rules** are not used. Ask for a redirect, cache rule or configuration rule instead.
