# ADR-009: LoggerFactory Uses Per-Instance Category Cache

- **Status:** Accepted
- **Date:** 2026-03-26
- **Deciders:** Agent

## Context

The JavaScript `LoggerFactory` shares a single module-level `LoggerCategoryCache`
across all factory instances. This avoids redundant config lookups when the same
category is requested multiple times from the same config.

During implementation, a module-level shared cache was initially used in the
Python port. This caused test pollution: a test that created a `LoggerFactory`
with config `{logging: {level: {"/": "warn"}}}` would cache the resolved level
for `logging.level./`. A subsequent test with a different config would then read
the stale `"warn"` from the cache instead of its own config's level. Tests that
ran in isolation passed, but failed as part of the full suite.

## Decision

`LoggerFactory.__init__` creates a fresh `LoggerCategoryCache` instance by
default:

```python
self.cache = cache if cache is not None else LoggerCategoryCache()
```

Callers who want a shared cache (e.g. a singleton factory used across an entire
application) can pass an explicit `cache` argument.

## Consequences

**Positive:**
- Tests are isolated — no cross-test cache pollution.
- Each factory instance is independently configurable.

**Negative:**
- The per-instance cache provides no benefit for the common pattern of one factory
  per process, since the cache is not shared. Level lookups are re-resolved on
  every `get_logger()` call for new categories. Performance impact is negligible
  for typical applications (dozens to hundreds of categories).

**Risks:**
- An application that creates many short-lived `LoggerFactory` instances will not
  benefit from category-level caching. The recommended pattern is one long-lived
  factory per application, optionally sharing a cache via the constructor argument.
