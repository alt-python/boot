# ADR-008: Config Level Keys Use Nested Dicts

- **Status:** Accepted
- **Date:** 2026-03-26
- **Deciders:** Agent

## Context

In the JavaScript logger, config level keys use the slash path convention:

```json
{
  "logging": {
    "level": {
      "/": "warn",
      "/com/example": "debug"
    }
  }
}
```

The Python port uses dot-separated category names (ADR-003). The `ConfigurableLogger`
level lookup walks dot-split segments of the category string, building paths like
`logging.level.com`, `logging.level.com.example`, etc., and calls
`config.has(path)` at each step.

`EphemeralConfig._resolve()` traverses nested dicts using dot-split. When a
config file contains:

```yaml
logging:
  level:
    com:
      example: debug
```

`config.has("logging.level.com.example")` traverses `logging → level → com →
example` and correctly finds `"debug"`. When the config file instead uses a flat
dotted key:

```yaml
logging:
  level:
    "com.example": debug   # flat key with literal dot
```

`EphemeralConfig` would find this via the flat key fast-path, but the segment
walker would only reach `logging.level.com.example` after traversing through
`com` first — finding a string `"debug"` only if `com` does not exist as a
separate dict key. Mixing flat and nested keys leads to unpredictable lookup
order.

## Decision

The canonical format for multi-segment level keys is **nested dicts**, not flat
dotted keys:

```yaml
logging:
  level:
    /:      warn
    com:
      example: debug
```

`ConfigurableLogger.get_logger_level()` only applies a value retrieved from
config if it is a string present in `LoggerLevel.ENUMS`. Dict values (which
indicate an intermediate prefix node) are skipped — the walk continues to deeper
segments.

## Consequences

**Positive:**
- Unambiguous lookup — dot-traversal always finds the most-specific match.
- Prevents accidental assignment of a dict (intermediate node) as a level string.
- Consistent with YAML's native nested structure.

**Negative:**
- Config files must use nested YAML/JSON — flat key style (`"com.example": debug`)
  is not supported for level configuration. This differs from `.properties` files
  where dotted keys are the natural notation.
- Documentation must clearly state this constraint.

**Risks:**
- A user migrating from the JS config format (where slash paths are flat keys) may
  write flat dotted keys and see no level match. The fallback is `info`, so the
  consequence is unexpected log verbosity rather than an error.
