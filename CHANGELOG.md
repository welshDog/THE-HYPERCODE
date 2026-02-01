# Changelog

All notable changes to the HyperCode monorepo will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Docs**: Comprehensive `DEPLOYMENT.md` covering security prerequisites (JWT, Redis TLS) and deployment flows (Docker, K8s).
- **Docs**: `hyperflow-editor` README now includes Auth & Backend Integration section (OAuth2 scopes, endpoints).
- **Docs**: `broski-terminal` README now includes Backend Integration Quickstart.
- **CI**: Added `deploy-validate.yml` for temporary namespace deployment validation.
- **CI**: Added `docs-lint.yml` for markdown linting and link checking.

### Changed
- **Core**: `hypercode-core` server now supports dual environment variables (`HYPERCODE_JWT_SECRET` / `JWT_SECRET` and `HYPERCODE_REDIS_URL` / `REDIS_URL`).
- **Core**: Added `RateLimitHeaderMiddleware` to `hypercode-core` to inject `x-ratelimit-limit` headers.
