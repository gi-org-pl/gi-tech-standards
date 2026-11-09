# Application

These rules cover the code of a service. The examples come from **Nest.js** services, but the rules apply to any
framework.

## Requests

> **#1. All input MUST go through a global validation pipe that rejects unknown properties.**
>
> ```ts
> app.useGlobalPipes(
>   new ValidationPipe({
>     whitelist: true,
>     forbidNonWhitelisted: true,
>     transform: true,
>   }),
> );
> ```

> **#2. A service MUST parse only JSON bodies, with a limit on their size.**
>
> By default, Nest also parses forms. A form on another website can then send a request with the cookies of the visitor,
> and for example sign them into the account of an attacker. Turn the default parser off and add only the JSON one:
>
> ```ts
> const app = await NestFactory.create<NestExpressApplication>(AppModule, {
>   bodyParser: false,
> });
>
> app.use(json({ limit: '1mb' }));
> ```

> **#3. CORS MUST allow an explicit list of origins for each environment.**
>
> Never use `*` or reflect the origin of the request, especially with `credentials: true`.

> **#4. `trust proxy` MUST trust only the proxy we run.**
>
> With `cloudflared` in the same task, the correct value is `loopback`. With `true`, anyone can fake their address with
> the `X-Forwarded-For` header and get around every limit based on the client address.

## Passwords

> **#1. Passwords MUST be hashed with Argon2id.**
>
> Use `argon2` from `node:crypto`, so no additional library is needed, with at least these parameters:
>
> | Parameter   | Value     |
> | ----------- | --------- |
> | Memory      | 19456 KiB |
> | Passes      | 2         |
> | Parallelism | 1         |
> | Tag length  | 32 bytes  |
> | Salt length | 16 bytes  |
>
> Store the hash in the PHC string format, which keeps the parameters next to the hash, so they can be raised later.
> When the parameters of a stored hash are out of date, hash the password again after a successful sign-in. Compare
> hashes with `timingSafeEqual`, not with `===`.

> **#2. Sign-in MUST NOT reveal whether an account exists.**
>
> An unknown e-mail and a wrong password return the same error. An unknown e-mail MUST also take just as long, so check
> the password against a dummy hash. Check things like a verified e-mail or the account status only after the password
> matches.

## Sessions

> **#1. Session tokens MUST be random, and only their hash MUST be stored.**
>
> Generate them with `randomBytes(32)` and keep the SHA-256 hash in the database. Someone who reads the database does
> not get a working session. Every session has an expiry date.

> **#2. Session cookies MUST use the `__Host-` prefix, `Secure`, `HttpOnly` and `SameSite=Lax`.**
>
> Browsers accept the `__Host-` prefix only with `Secure`, `Path=/` and no `Domain`, so no other subdomain can set the
> cookie. `HttpOnly` keeps it away from scripts. Local development has no HTTPS, so it uses a name without the prefix
> and no `Secure`.
>
> ```text
> __Host-my_service_session=<token>; Max-Age=<seconds>; Path=/; HttpOnly; SameSite=Lax; Secure
> ```

> **#3. Endpoints protected by a cookie MUST accept `POST`, `PUT` and `PATCH` only with `application/json`.**
>
> Anything else gets `415`. A form on another website cannot send this content type without a CORS check first.

> **#4. A session MUST be checked against the account on every request.**
>
> When the account is no longer active, end the session, clear the cookie and return `401`.

## Rate limiting

> **#1. Endpoints that check a password or send an e-mail MUST be rate limited.**
>
> Otherwise they can be used to guess passwords, or to send mail to anyone in our name.

> **#2. Limits MUST be kept in one table, keyed by endpoint.**
>
> An action only opts in with a decorator and holds no numbers. The application refuses to start if a decorated endpoint
> has no row in the table, so a limit cannot be forgotten silently.

> **#3. Requests SHOULD be counted separately per client address, per account and per e-mail.**
>
> Address limits alone do not protect one account from many addresses. An IPv6 address counts by its `/64` network,
> because a single client usually controls all of it. The limit runs before validation, so a `400` also counts.

> **#4. A rejected request MUST get `429` with `Retry-After`, and it MUST NOT log an address or an e-mail.**
>
> One `warn` line with the route and the name of the limit is enough.

> **#5. A service with counters in memory MUST move them to a shared store before it runs more than one instance.**
>
> Every instance has its own counters, so each new instance raises the real limit.

Read more about the application:

- [Password storage cheat sheet (OWASP)](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [Session management cheat sheet (OWASP)](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
