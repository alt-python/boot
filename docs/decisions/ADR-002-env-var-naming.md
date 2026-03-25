# ADR-002: Python-Native Environment Variable Names

- **Status:** Accepted
- **Date:** 2026-03-26
- **Deciders:** Craig Parravicini

## Context

The JavaScript monorepo uses `NODE_ACTIVE_PROFILES` and `NODE_CONFIG_PASSPHRASE`
as environment variable names. These names carry the `NODE_` prefix, which is
meaningful in JavaScript tooling (Node.js reads `NODE_*` variables for its own
runtime configuration) but misleading and potentially confusing in a Python
environment where Node.js is not present.

## Decision

Use Python-specific environment variable names:

| Purpose | JS name | Python name |
|---|---|---|
| Active profiles | `NODE_ACTIVE_PROFILES` | `PY_ACTIVE_PROFILES` |
| Jasypt passphrase | `NODE_CONFIG_PASSPHRASE` | `PY_CONFIG_PASSPHRASE` |

These names are used throughout `ProfileConfigLoader` and `JasyptDecryptor`.

## Consequences

**Positive:**
- No ambiguity in polyglot environments where both Node.js and Python processes run.
- `PY_*` prefix is recognisable as Python-specific, consistent with other Python ecosystem conventions (e.g. `PYTHONPATH`, `PY_COLORS`).

**Negative:**
- Config files and deployment scripts cannot share a single env var name across both JS and Python deployments. Each runtime must set its own variable.

**Risks:**
- None significant. The variable names are only read at startup and are documented in each package README.
