## HyperCode Deployment Guide

### Security Prerequisites

- JWT secret:
  - A 256-bit secret must be supplied via `JWT_SECRET` (or `HYPERCODE_JWT_SECRET`).
  - Generate a compliant secret on Unix-like shells:

    ```bash
    openssl rand -hex 32
    ```

  - On PowerShell:

    ```powershell
    [Convert]::ToBase64String((New-Object byte[] 32 | %{ (New-Object System.Security.Cryptography.RNGCryptoServiceProvider).GetBytes($_) ; $_ }))
    ```

  - Never commit secrets to version control. Use environment stores or secret managers.

- Redis-backed rate limiting:
  - Required environment variable: `REDIS_URL` (or `HYPERCODE_REDIS_URL`).
  - Expected format: `rediss://user:password@host:6379/0` for TLS-enabled Redis.
  - Minimum Redis version: `6.2`.

  - Example `docker-compose` snippet with TLS and AUTH:

    ```yaml
    services:
      redis:
        image: redis:7-alpine
        command: [
          "redis-server",
          "--requirepass", "${REDIS_PASSWORD}",
          "--tls-port", "6379",
          "--port", "0",
          "--tls-cert-file", "/certs/redis.crt",
          "--tls-key-file", "/certs/redis.key",
          "--tls-ca-cert-file", "/certs/ca.crt"
        ]
        volumes:
          - ./certs/redis:/certs:ro
    ```

### Deployment Flows

All flows must verify that both `JWT_SECRET` and `REDIS_URL` (or their `HYPERCODE_*` equivalents) are present before starting services.

#### Docker / docker-compose

- Ensure `docker-compose.yml` sets the required environment variables for `hypercode-core`.
- Add a simple entrypoint script that exits if variables are missing:

  ```bash
  #!/usr/bin/env bash
  set -e
  : "${JWT_SECRET:?JWT_SECRET is required}"
  : "${REDIS_URL:?REDIS_URL is required}"
  exec "$@"
  ```

#### Kubernetes

- Inject secrets via sealed-secret or external-secret.

  - Example with External Secrets Operator:

    ```yaml
    apiVersion: external-secrets.io/v1beta1
    kind: ExternalSecret
    metadata:
      name: hypercode-core-secrets
    spec:
      refreshInterval: 1h
      secretStoreRef:
        kind: ClusterSecretStore
        name: global-secrets
      target:
        name: hypercode-core-env
      data:
        - secretKey: JWT_SECRET
          remoteRef:
            key: hypercode/jwt-secret
        - secretKey: REDIS_URL
          remoteRef:
            key: hypercode/redis-url
    ```

  - Pod environment snippet:

    ```yaml
    envFrom:
      - secretRef:
          name: hypercode-core-env
    ```

#### Bare-metal

- Use an `.env` file loaded by your process manager and ensure both variables are set before starting `hypercode-core`.

### Verification

After deployment:

- Run the security smoke test:

  ```bash
  npm run security:smoke
  ```

- Verify:
  - Responses from the API include an `x-ratelimit-limit` header.
  - JWT authentication handshake succeeds and protected endpoints return `201` on success.

