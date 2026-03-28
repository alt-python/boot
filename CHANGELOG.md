# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] — 2026-03-28

### Added

- **`boot-pydbc`** — Spring Boot-style CDI auto-configuration for relational
  databases via pydbc.
  - `PydbcTemplate` — execute DDL, DML, and SELECT statements with positional
    `?` parameters. Methods: `execute()`, `update()`, `query_for_list()`,
    `query_for_object()`. Accepts an optional `row_mapper` callable.
  - `NamedParameterPydbcTemplate` — wraps `PydbcTemplate` with `:param_name`
    named-parameter support via `ParamstyleNormalizer`.
  - `ConfiguredDataSource` — CDI bean that reads `boot.datasource.*` config
    properties and creates a `DataSource`, `SingleConnectionDataSource`, or
    `PooledDataSource` as appropriate. Silently no-ops when URL is absent.
  - `SchemaInitializer` — CDI bean that runs `config/schema.sql` followed by
    `config/data.sql` at startup. Skips when `boot.datasource.initialize: false`
    or when the SQL files are absent.
  - `DataSourceBuilder` — fluent builder for secondary datasources with custom
    config prefix and custom CDI bean names.
  - `pydbc_auto_configuration(prefix)` — returns 4 CDI `Singleton` beans
    (`data_source`, `pydbc_template`, `named_parameter_pydbc_template`,
    `schema_initializer`) ready for use in a `Context()`.
  - `pydbc_template_starter()` — one-call `Boot.boot()` entry point.

- **`boot-pynosqlc`** — Spring Boot-style CDI auto-configuration for document
  stores via pynosqlc.
  - `ConfiguredClientDataSource` — CDI bean that reads `boot.nosql.*` config
    properties and creates a `ClientDataSource`. Silently no-ops when URL is
    absent.
  - `ManagedNosqlClient` — CDI bean that wraps a pynosqlc async client with a
    synchronous CDI lifecycle (`init()` / `destroy()` bridge via `asyncio.run()`).
    Provides `get_collection(name)` for synchronous collection access.
  - `NoSqlClientBuilder` — fluent builder for secondary NoSQL clients with
    custom config prefix and custom CDI bean names.
  - `pynosqlc_auto_configuration(prefix)` — returns 2 CDI `Singleton` beans
    (`nosql_client_data_source`, `nosql_client`) ready for use in a `Context()`.
  - `pynosqlc_boot()` — one-call `Boot.boot()` entry point.

- **`example-5-2-persistence-pydbc`** — runnable persistence example using
  `PydbcTemplate` and `SchemaInitializer` over SQLite in-memory. Demonstrates
  `find_all()`, `find_by_id()`, and `mark_done()` via a `NoteRepository` CDI
  service. `SchemaInitializer` seeds the database from `config/schema.sql` and
  `config/data.sql` before the application runs.

- **`example-5-5-persistence-nosql`** — runnable document-store example using
  `ManagedNosqlClient` and the pynosqlc memory driver. Demonstrates `store()`,
  `find_all()`, and document retrieval via a `NoteRepository` CDI service with
  an `asyncio.run()` bridge inside the synchronous `Application.run()` method.

### Fixed

- **`boot-pydbc` — `SchemaInitializer` pool connection leak.** `init()` now
  calls `conn.close()` after executing schema and data files, returning the
  connection to the pool. Without this fix, a `PooledDataSource(max=1)` was
  exhausted before application code could acquire a connection.

### Documentation

- **ADR-010** — PydbcTemplate bundled inside boot-pydbc (not a separate package).
- **ADR-011** — CDI beans access the config bean via `ctx.get('config')`, not
  `ctx.config` (which does not exist as a public property).
- **ADR-012** — CDI lifecycle methods (`init()`, `destroy()`) must be declared
  as regular `def`; use `asyncio.run()` to bridge async backends.

## [1.0.1] — 2026-03-26

### Added

- **PyPI long description.** Added `readme = "README.md"` to all four publishable
  packages (`alt-python-common`, `alt-python-pysypt`, `alt-python-config`,
  `alt-python-logger`) so the README is rendered as the project page on PyPI.
  Added `README.md` to `alt-python-common` (previously missing).

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

[Unreleased]: https://github.com/alt-python/boot/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/alt-python/boot/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/alt-python/boot/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/alt-python/boot/releases/tag/v1.0.0
