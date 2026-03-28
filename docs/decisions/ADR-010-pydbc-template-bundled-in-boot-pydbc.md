# ADR-010: PydbcTemplate bundled inside boot-pydbc

- **Status:** Accepted
- **Date:** 2026-03-28
- **Deciders:** Craig Parravicini

## Context

`PydbcTemplate` and `NamedParameterPydbcTemplate` are SQL template classes that
operate over any pydbc `DataSource`. They have no dependency on Spring Boot or
CDI — they are plain utility classes that wrap DBAPI-style connection handling
in a higher-level API.

Two packaging options were considered:

1. **Separate `pydbc-template` package** — mirrors the split between `jsdbc` and
   `jsdbc-template` in the JavaScript ecosystem at a library level.
2. **Bundle inside `boot-pydbc`** — ship template classes as part of the CDI
   auto-configuration starter, re-exported from `boot_pydbc`.

## Decision

Bundle `PydbcTemplate` and `NamedParameterPydbcTemplate` inside `boot-pydbc`.
They are exported from `boot_pydbc.__init__` and available as
`from boot_pydbc import PydbcTemplate`.

## Consequences

**Positive:**
- One package to install (`alt-python-boot-pydbc`) for the full SQL stack.
- No additional PyPI package to publish or version.
- Consistent with `boot-jsdbc` in the JavaScript port, which bundles
  `jsdbc-template` inside the starter.

**Negative:**
- Applications that want `PydbcTemplate` without CDI auto-configuration must
  still depend on `boot-pydbc` (and transitively on `boot`, `cdi`, `config`).

**Risks:**
- If the template classes are later needed independently of the CDI starter, a
  separate `alt-python-pydbc-template` package can be created and `boot-pydbc`
  can re-export from it. The public API surface does not change.
