# Infrastructure

These rules cover the parts of our AWS setup that protect data and limit what each service can reach. Everything is
defined in OpenTofu, in the `infra/` directory of each repository.

## OpenTofu state

> **#1. OpenTofu state and plans MUST be encrypted with a KMS key, and unencrypted ones MUST be refused.**
>
> State and plan files hold every value given to a resource in plain text, including all secrets. Encryption of the S3
> bucket does not help against anyone who can read the bucket. With `enforced = true`, OpenTofu refuses to read or write
> an unencrypted file.
>
> ```hcl
> terraform {
>   encryption {
>     key_provider "aws_kms" "state" {
>       kms_key_id = "alias/my-service-state-key"
>       region     = var.aws_region
>       key_spec   = "AES_256"
>     }
>
>     method "aes_gcm" "state" {
>       keys = key_provider.aws_kms.state
>     }
>
>     state {
>       method   = method.aes_gcm.state
>       enforced = true
>     }
>
>     plan {
>       method   = method.aes_gcm.state
>       enforced = true
>     }
>   }
> }
> ```
>
> The KMS key SHOULD have `enable_key_rotation = true` and `prevent_destroy`, because losing it means losing the state.

> **#2. After turning encryption on, the old state versions MUST be deleted.**
>
> A versioned bucket keeps the earlier state files, and they still hold the secrets in plain text.

> **#3. Variables that hold secrets MUST be marked as `sensitive`.**
>
> Plans are posted on pull requests, and a value of a sensitive variable shows up there as `(sensitive value)`.

## Network

> **#1. A service MUST NOT accept inbound connections from the internet.**
>
> Its security group has no `ingress` rules. Traffic reaches the service through a tunnel that it opens itself, with
> `cloudflared` running as a sidecar in the same task. There is no public load balancer and no open port to attack.

> **#2. Outbound traffic MUST be limited to the ports that the service uses.**
>
> If someone breaks into a service, open egress lets them send the data anywhere and download any tool. Each rule says
> why it exists:
>
> ```hcl
> egress {
>   description = "HTTPS to AWS APIs, image registries and Cloudflare"
>   from_port   = 443
>   to_port     = 443
>   protocol    = "tcp"
>   cidr_blocks = ["0.0.0.0/0"]
> }
> ```

## Database

> **#1. A database MUST be private, encrypted and protected from deletion.**
>
> ```hcl
> publicly_accessible     = false
> storage_encrypted       = true
> kms_key_id              = aws_kms_key.rds.arn
> deletion_protection     = true
> skip_final_snapshot     = false
> backup_retention_period = 7
> ```

> **#2. Connections to the database MUST use TLS and verify the certificate.**
>
> `sslmode=no-verify` encrypts the connection, but it accepts any certificate, so a host that intercepts the connection
> goes unnoticed. RDS Proxy gets `require_tls = true`, and the database URL ends with both parameters below. `pg`, used
> for queries, reads `sslmode` and checks the chain and the hostname. The Prisma schema engine, used for migrations,
> reads `sslaccept`.
>
> ```text
> postgresql://<user>:<password>@<host>:5432/<database>?schema=public&sslmode=verify-full&sslaccept=strict
> ```

## Permissions

> **#1. A service MUST have only the permissions it uses, on the resources it uses.**
>
> Keep the execution role, which ECS uses to start the task, apart from the task role, which the application uses. Name
> each action and each resource:
>
> ```hcl
> policy = jsonencode({
>   Version = "2012-10-17"
>   Statement = [{
>     Effect   = "Allow"
>     Action   = ["sqs:SendMessage", "sqs:GetQueueUrl", "sqs:GetQueueAttributes"]
>     Resource = aws_sqs_queue.main.arn
>   }]
> })
> ```

## Logs

> **#1. Every log group MUST have a retention period.**
>
> By default, CloudWatch keeps logs forever, and logs that nobody needs any more are only a risk. Set
> `retention_in_days`, which is `7` in our services.

Read more about infrastructure:

- [State and plan encryption in OpenTofu](https://opentofu.org/docs/language/state/encryption/)
- [Using SSL/TLS with Amazon RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.SSL.html)
