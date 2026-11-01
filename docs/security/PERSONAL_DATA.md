# Personal data

Personal data is anything that can be connected to a person: an e-mail address, a name, an IP address, and answers
linked to any of them. The answers given in myPolitics reveal political opinions, so they are a
[special category of personal data](https://gdpr-info.eu/art-9-gdpr/) under GDPR and need the most care.

## Logs

> **#1. Logs MUST contain IDs only, never personal data or secrets.**
>
> Never log an e-mail address, a name, an IP address, a password or a token. For e-mails, that also means the recipient,
> the subject and the body. Logs are read by more people and tools than the database, and they are the easiest place for
> data to leak from.

> **#2. An event MUST NOT be logged if its time could connect a person to sensitive data.**
>
> For example, sign-in in myPolitics writes no log line, because an account ID with an exact time could be matched with
> quiz results submitted at that moment.

> **#3. Logs MUST be kept for as short a time as they are useful.**
>
> Our services keep them for 7 days, see [Infrastructure](/docs/security/INFRASTRUCTURE.md#logs).

## Exports

> **#1. Exports MUST be protected by their own credential.**
>
> The token of the export endpoint is separate from the admin token, so the people who analyze the data do not get admin
> access, and the other way around.

> **#2. Exported rows MUST NOT contain internal IDs.**
>
> A row gets a new random ID in every export. If the real ID were exported, and results can be opened by their ID, an
> export and one shared link would be enough to find the answers and demographics of that person.

> **#3. An export MUST select the fields it returns by name.**
>
> Never export a whole row or relation, because a column added later would leave the database without anyone deciding
> that it should. Leave out exact times as well. A test MUST compare the exact body of the export, so a new field fails
> the test.
>
> ```ts
> demographic: {
>   select: {
>     gender: true,
>     age: true,
>     region: true,
>   },
> },
> ```

> **#4. Production data and exports MUST NOT be shared with AI tools.**
>
> The same goes for pasting them into a chat, an issue or a pull request. Use the seed data for examples and debugging.
