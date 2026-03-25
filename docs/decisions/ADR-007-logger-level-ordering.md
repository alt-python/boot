# ADR-007: Preserve JS Level Ordering for Internal Comparisons

- **Status:** Accepted
- **Date:** 2026-03-26
- **Deciders:** Agent

## Context

The JavaScript `LoggerLevel` module defines severity as: `fatal=0, error=1,
warn=2, info=3, verbose=4, debug=5`. Lower integer = more severe. A logger set
to level `info` (3) enables any method whose severity integer is ≤ 3.

Python's `logging` module uses the inverse convention: `DEBUG=10, INFO=20,
WARNING=30, ERROR=40, CRITICAL=50`. Higher integer = more severe.

If the JS `is_*_enabled()` logic (`levels[level] <= self.level`) were ported
literally using Python stdlib integers, `is_debug_enabled()` at `info` level
would return `True` because `DEBUG(10) <= INFO(20)` — the opposite of the
intended behaviour.

## Decision

Maintain two separate mappings in `LoggerLevel`:

- `ENUMS`: `{fatal: 0, error: 1, warn: 2, info: 3, verbose: 4, debug: 5}` — used exclusively for `is_*_enabled()` comparisons. Ported directly from the JS source.
- `STDLIB`: `{fatal: 50, error: 40, warn: 30, info: 20, verbose: 15, debug: 10}` — used only when calling `stdlib_logger.log(level_int, ...)`.

`Logger.is_level_enabled(level)` compares `ENUMS[level] <= self._severity`, where `_severity` is from `ENUMS`. This matches JS semantics exactly.

`ConsoleLogger._emit()` converts the level name to a stdlib int via `STDLIB` before calling `stdlib_logger.log()`.

The custom `VERBOSE` level is registered at `15` (between `DEBUG=10` and `INFO=20`) via `logging.addLevelName(15, "VERBOSE")`.

## Consequences

**Positive:**
- `is_debug_enabled()`, `is_info_enabled()`, etc. behave identically to the JS version.
- Tests ported from the JS test suite pass without semantic changes.
- Stdlib emit uses correct level integers for handler filtering.

**Negative:**
- Two level systems must be kept in sync. Adding a new level requires updating both `ENUMS` and `STDLIB`.

**Risks:**
- A caller who reads `logger._severity` directly (instead of `is_*_enabled()`) will see the ENUMS integer, not a stdlib integer. Internal use only — not part of the public API.
