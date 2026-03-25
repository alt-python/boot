# ADR-004: Wrap stdlib logging as the Logger Backend

- **Status:** Accepted
- **Date:** 2026-03-26
- **Deciders:** Craig Parravicini, Agent

## Context

The JavaScript `ConsoleLogger` writes directly to `process.stdout` and
`process.stderr` (or a `console` object). This is self-contained and avoids any
dependency on an external logging framework.

Python's `logging` stdlib module is more capable than its pre-`winston` Node.js
equivalent: it has a hierarchical logger registry, handlers (console, file,
rotating file, socket, syslog), formatters, and filters — all without third-party
dependencies. Bypassing it would mean reimplementing routing, handler
configuration, and sink management that Python developers already know how to
configure via `logging.config.dictConfig`.

## Decision

`ConsoleLogger` wraps a `logging.Logger` instance as its actual emitter. Each
`ConsoleLogger` calls `stdlib_logger.log(level_int, formatted_message)` to emit.
This means:

- Any stdlib handler (FileHandler, RotatingFileHandler, SocketHandler, etc.) attached to the logger or its parents is automatically used.
- `logging.config.dictConfig` configuration applies to loggers created by this library.
- Callers can replace `stdlib_logger` with any object that implements `isEnabledFor(level)` and `log(level, message)` — including `CachingConsole` for tests.

The custom `VERBOSE` level (integer 15, between `DEBUG`=10 and `INFO`=20) is
registered once at import time via `logging.addLevelName(15, "VERBOSE")`.

Level mapping:

| alt-python level | Severity int (internal) | Python stdlib int |
|---|---|---|
| `fatal` | 0 | 50 (CRITICAL) |
| `error` | 1 | 40 (ERROR) |
| `warn` | 2 | 30 (WARNING) |
| `info` | 3 | 20 (INFO) |
| `verbose` | 4 | 15 (custom) |
| `debug` | 5 | 10 (DEBUG) |

## Consequences

**Positive:**
- Zero extra dependencies for log routing — stdlib handles it.
- Python developers can use familiar `logging.config.dictConfig` to configure handlers and formatters independently of category level configuration.
- `CachingConsole` test fixture works without patching stdlib.

**Negative:**
- Log level is controlled at two points: the `ConfigurableLogger` severity int (guards `is_*_enabled()`) and the stdlib logger level (guards actual emission). Both must agree. By default the stdlib logger is set to `NOTSET` (inherits from root), so the `ConfigurableLogger` guard is the effective gate.
- `ConsoleLogger`'s formatted message string is passed as the `msg` argument to `stdlib_logger.log()` — stdlib will not apply its own formatters to it. This is intentional: the alt-python formatter runs first.

**Risks:**
- If a caller configures a stdlib logger level above the `ConfigurableLogger` level, some messages will be silently dropped at the stdlib layer. Documented in the logger README.
