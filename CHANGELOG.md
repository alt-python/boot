# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] — 2026-03-26

> Initial public release.

### Added

- **`pysypt`** — Jasypt-compatible PBE encryption/decryption for Python.
  `Encryptor` and `Digester` implement PBEWITHMD5ANDDES (the Jasypt default).
  `ENC(...)` and bare `enc.<base64>` ciphertext formats both supported.
  Enables transparent decryption of secrets stored in config files.

- **`config`** — Spring Boot-inspired profile-aware configuration for Python.
  - `ProfileConfigLoader` discovers `application.{properties,yaml,yml,json}` and
    `application-{profile}.*` overlays from `config/` and the working directory.
    Active profiles selected via `PY_ACTIVE_PROFILES` environment variable.
  - `EphemeralConfig` — lightweight dict-backed config with dot-notation path traversal.
  - `PropertySourceChain` — ordered list of config sources with first-match precedence.
  - `EnvPropertySource` — environment variables with relaxed binding
    (`APP_SERVER_PORT` → `app.server.port`).
  - `DotEnvParser` — parses `.env` files (bare, `export`-prefixed, quoted values,
    inline `#` comments).
  - `PropertiesParser` — parses Java-style `.properties` files.
  - `PlaceholderResolver` — `${path}` substitution across sources.
  - `JasyptDecryptor` — transparent decryption of `ENC(...)` and `enc.<base64>` values
    via `pysypt`.
  - `ValueResolvingConfig` — wraps any config source with placeholder + decryption
    resolution.
  - `ConfigFactory.get_config()` — zero-setup entry point; returns a fully-wired
    `ValueResolvingConfig` backed by `ProfileConfigLoader`.
  - Module-level `config` singleton — `from config import config` is all that's needed.

- **`logger`** — Spring Boot-inspired config-driven logger for Python.
  - `LoggerFactory` — creates `ConfigurableLogger` instances wired to a config source.
    Module-level `logger_factory` singleton available with no setup.
  - `ConfigurableLogger` — resolves log level from config at construction time.
    Config key `logging.level./` sets root level; `logging.level.<dot.path>` sets
    category-specific levels using nested dict traversal.
  - `ConsoleLogger` — emits via Python's `logging` stdlib. Syncs the stdlib logger's
    level to match the configured level so records are never silently swallowed by the
    stdlib root handler default (WARNING).
  - `DelegatingLogger` — forwards all calls to a provider; level control propagates.
  - `MultiLogger` — fans log calls out to multiple provider loggers.
  - `LoggerLevel` — level constants (`fatal`, `error`, `warn`, `info`, `verbose`,
    `debug`) with severity ordering and stdlib mapping.
  - `JSONFormatter` — structured JSON log lines.
  - `PlainTextFormatter` — human-readable `timestamp:category:level:message` lines.
  - `CachingConsole` — in-memory log sink for testing.
  - Log format selected via `logging.format` config key (`text` or `json`).

- **`common`** — shared package placeholder; workspace anchor for cross-package utilities.

- **`example-1-1-intro-config`** — standalone introduction to `config`.
  Demonstrates `config.get()`, `config.has()`, default values, `.properties` format,
  YAML profile overlays, and transparent `ENC(...)` decryption.
  Run with `PY_ACTIVE_PROFILES=dev` to activate the dev overlay.

- **`example-1-2-intro-logger`** — introduction to `logger` alongside `config`.
  Demonstrates qualified category names, root vs category-specific log levels,
  and switching between text and JSON output via profile.
  Three profiles: default (text, debug for this category), `dev` (warn at root),
  `json-log` (JSON format).

- **`uv` workspace** — monorepo managed with `uv`. All packages are workspace members;
  inter-package dependencies declared via `tool.uv.sources`.

[Unreleased]: https://github.com/alt-python/boot/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/alt-python/boot/releases/tag/v1.0.0
