# logger

[![Language](https://img.shields.io/badge/language-Python-3776ab.svg)](https://www.python.org/)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Config-driven, category-based structured logging for Python. Log levels are set
in config under `logging.level` using a dot-hierarchy that mirrors Python's
`logging` namespace. The library wraps Python's stdlib `logging` as the emit
backend, so all existing stdlib handlers (file, rotating, socket, syslog) work
without any extra configuration.

Port of [`@alt-javascript/logger`](https://github.com/alt-javascript/boot/tree/main/packages/logger)
to Python.

## Install

```bash
uv add alt-python-logger        # or: pip install alt-python-logger
```

Requires Python 3.12+ and the `config` package (workspace dependency).

## Quick Start

```python
from logger import logger_factory

log = logger_factory.get_logger("com.example.MyService")

log.fatal("Service crashed")
log.error("Request failed", {"status": 500, "path": "/api/users"})
log.warn("Retry attempt 3")
log.info("Application started")
log.verbose("Processing record 42 of 1000")
log.debug("SQL: SELECT * FROM users WHERE id = ?")
```

Zero setup — `logger_factory` reads from the default `config` singleton, which
discovers `application.yaml` (or `.json`, `.properties`, `.env`) from the
current working directory.

## Log Levels

From least to most verbose, with the internal severity integer used for
`is_*_enabled()` comparisons:

| Level | Severity | Python stdlib int | Method |
|---|---|---|---|
| `fatal` | 0 (most severe) | 50 (CRITICAL) | `log.fatal(msg, meta=None)` |
| `error` | 1 | 40 (ERROR) | `log.error(msg, meta=None)` |
| `warn` | 2 | 30 (WARNING) | `log.warn(msg, meta=None)` |
| `info` | 3 | 20 (INFO) | `log.info(msg, meta=None)` |
| `verbose` | 4 | 15 (custom) | `log.verbose(msg, meta=None)` |
| `debug` | 5 (least severe) | 10 (DEBUG) | `log.debug(msg, meta=None)` |

A logger set to level `info` enables `fatal`, `error`, `warn`, and `info`. It
suppresses `verbose` and `debug`. See
[ADR-007](../../docs/decisions/ADR-007-logger-level-ordering.md) for why the
ordering is preserved from the JS source.

## Config-Driven Levels

Set levels in config under `logging.level`. The hierarchy uses nested dicts —
each node corresponds to a dot segment of the category name.

```yaml
# application.yaml
logging:
  level:
    /:           warn       # root level — applies to all loggers
    com:
      example:   debug      # com.example.* → debug
      noisy:
        handler: warn       # com.example.noisy.handler → warn
  format: text              # text or json (default: json)
```

The lookup walks the category's dot segments from left to right, applying the
most-specific match found:

```python
logger_factory.get_logger("com.example.MyService")   # → debug (from com.example)
logger_factory.get_logger("com.example.noisy.handler") # → warn (from com.example.noisy.handler)
logger_factory.get_logger("other.pkg.Handler")        # → warn (from root /)
```

**Config key format:** Level keys must be **nested dicts** — flat dotted keys
like `"com.example": debug` are not recognised by the segment walker. See
[ADR-008](../../docs/decisions/ADR-008-config-level-keys.md).

## Level Guards

Use guards before constructing expensive log arguments:

```python
if log.is_debug_enabled():
    log.debug(f"Query plan: {explain_query(sql)}")
```

| Method | Returns `True` when... |
|---|---|
| `is_fatal_enabled()` | level is `fatal` |
| `is_error_enabled()` | level is `fatal` or `error` |
| `is_warn_enabled()` | level is `fatal`, `error`, or `warn` |
| `is_info_enabled()` | level is `fatal` through `info` |
| `is_verbose_enabled()` | level is `fatal` through `verbose` |
| `is_debug_enabled()` | any level (level is `debug`) |

## Log Formats

### JSON (default)

```python
{"level": "info", "message": "Started", "timestamp": "2026-01-15T12:00:00+00:00", "category": "com.example.MyService"}
```

Pass a plain dict as `meta` to merge fields into the JSON object:

```python
log.info("Request complete", {"status": 200, "duration_ms": 42})
# => {"level":"info","message":"Request complete","timestamp":"...","category":"...","status":200,"duration_ms":42}
```

Pass any other value as `meta` to include it under a `"meta"` key:

```python
log.error("Unexpected value", "some_string")
# => {"level":"error","message":"Unexpected value","timestamp":"...","category":"...","meta":"some_string"}
```

### Plain text

```
2026-01-15T12:00:00+00:00:com.example.MyService:info:Application started
```

Set `logging.format: text` in config to enable plain text output.

## API Reference

### `LoggerFactory`

Main factory class. Creates `ConfigurableLogger` instances wired to a config
source.

#### Constructor

```python
LoggerFactory(config=None, cache=None, config_path=None)
```

| Parameter | Type | Description |
|---|---|---|
| `config` | config-like | Config source. Default: module-level `config` singleton. |
| `cache` | `LoggerCategoryCache \| None` | Level cache. Default: fresh per-instance cache (see [ADR-009](../../docs/decisions/ADR-009-per-instance-logger-cache.md)). |
| `config_path` | `str` | Root path for level lookup. Default: `"logging.level"`. |

#### `factory.get_logger(category)`

Returns a `ConfigurableLogger` for the given category.

`category` may be:
- A string: `"com.example.MyService"`
- A class instance with a `qualifier` attribute
- A class instance (uses `type(instance).__name__`)
- `None` (uses `"ROOT"`)

```python
log = factory.get_logger("com.example.MyService")
log = factory.get_logger(my_service_instance)
```

#### `LoggerFactory.get_logger_static(category, config, config_path, cache)`

Static convenience method equivalent to constructing a factory and calling
`get_logger()`.

---

### `ConfigurableLogger`

A `DelegatingLogger` whose level is set from config at construction time.

#### `ConfigurableLogger.get_logger_level(category, config_path, config, cache)`

Static method. Walks the category's dot segments and returns the most-specific
level found in config. Falls back to `"info"` if nothing is found.

The root level is read from `{config_path}./` (e.g. `logging.level./`).
Category segment levels are read from `{config_path}.{segment}` (e.g.
`logging.level.com`, `logging.level.com.example`).

---

### `Logger`

Base class. Stores the severity level and provides `is_*_enabled()` guards.

#### `Logger(category=None, level=None)`

| Parameter | Default | Description |
|---|---|---|
| `category` | `"ROOT"` | Logger category name |
| `level` | `"info"` | Initial log level |

#### `logger.set_level(level)`

Change the level at runtime. Accepts any key from `LoggerLevel.ENUMS`.

---

### `ConsoleLogger`

Logger that emits via a stdlib `logging.Logger`. Extends `Logger`.

```python
ConsoleLogger(category=None, level=None, formatter=None, stdlib_logger=None)
```

| Parameter | Description |
|---|---|
| `category` | Logger category name |
| `level` | Initial level |
| `formatter` | `JSONFormatter` (default) or `PlainTextFormatter` |
| `stdlib_logger` | stdlib `logging.Logger` instance, or `CachingConsole` for tests |

---

### `DelegatingLogger`

Wraps a `provider` logger and forwards all calls to it.

```python
DelegatingLogger(provider)
```

Raises `ValueError` if `provider` is `None`.

---

### `MultiLogger`

Fans out log calls to multiple child loggers.

```python
MultiLogger(loggers=None, category=None, level=None)
```

`set_level()` propagates to all child loggers.

```python
from logger import MultiLogger, ConsoleLogger

ml = MultiLogger([console_logger, file_logger], level="info")
ml.info("Written to both")
```

---

### `JSONFormatter`

```python
formatter.format(timestamp, category, level, message, meta=None)
```

Returns a JSON string. Dict `meta` is merged into the top-level object; other
types are stored under `"meta"`.

---

### `PlainTextFormatter`

```python
formatter.format(timestamp, category, level, message, meta=None)
```

Returns `"{timestamp}:{category}:{level}:{message}{meta}"`.

---

### `LoggerCategoryCache`

Simple dict cache for resolved level strings.

| Method | Description |
|---|---|
| `get(key)` | Returns the cached level string or `None`. |
| `put(key, level)` | Stores a level string. |

---

### `LoggerLevel`

Level constants and mappings.

```python
from logger import LoggerLevel

LoggerLevel.FATAL    # "fatal"
LoggerLevel.ERROR    # "error"
LoggerLevel.WARN     # "warn"
LoggerLevel.INFO     # "info"
LoggerLevel.VERBOSE  # "verbose"
LoggerLevel.DEBUG    # "debug"

LoggerLevel.ENUMS    # {"fatal": 0, ..., "debug": 5}
LoggerLevel.STDLIB   # {"fatal": 50, ..., "debug": 10}
```

---

### `CachingConsole`

In-memory log sink for test fixtures. Pass as `stdlib_logger` to
`ConsoleLogger`.

```python
from logger import ConsoleLogger, CachingConsole, PlainTextFormatter

sink = CachingConsole()
log  = ConsoleLogger(
    category="test",
    level="debug",
    formatter=PlainTextFormatter(),
    stdlib_logger=sink,
)

log.info("captured")
assert "captured" in sink.messages[0][1]

sink.clear()
```

`sink.messages` is a list of `(level_int, formatted_string)` tuples.

---

## All Exports

```python
from logger import (
    LoggerLevel,
    Logger,
    ConsoleLogger,
    DelegatingLogger,
    ConfigurableLogger,
    LoggerCategoryCache,
    LoggerFactory,
    JSONFormatter,
    PlainTextFormatter,
    CachingConsole,
    MultiLogger,
    logger_factory,   # module-level singleton
)
```

## Testing

Use `CachingConsole` to capture log output in tests without writing to stdout:

```python
from config import EphemeralConfig
from logger import (
    LoggerFactory, ConsoleLogger, CachingConsole, PlainTextFormatter
)

def test_logs_at_correct_level():
    cfg  = EphemeralConfig({"logging": {"level": {"/": "debug"}}})
    sink = CachingConsole()
    provider = ConsoleLogger(
        category="test",
        formatter=PlainTextFormatter(),
        stdlib_logger=sink,
    )
    from logger import ConfigurableLogger, LoggerCategoryCache
    log = ConfigurableLogger(
        config=cfg,
        provider=provider,
        category="test",
        cache=LoggerCategoryCache(),
    )

    log.info("hello")
    assert any("hello" in msg for _, msg in sink.messages)
```

Alternatively, create a `LoggerFactory` with an `EphemeralConfig` and call
`get_logger()` — the factory wires `CachingConsole` is not needed for level
assertions:

```python
def test_level_from_config():
    cfg     = EphemeralConfig({"logging": {"level": {"/": "warn"}}})
    factory = LoggerFactory(config=cfg)
    log     = factory.get_logger("my.service")

    assert log.is_warn_enabled() is True
    assert log.is_info_enabled() is False
```

## Troubleshooting

**All log messages appear regardless of configured level**
Check that `logging.level` in your config file uses nested dicts, not flat
dotted keys. `{"com.example": "debug"}` is not recognised — use
`{"com": {"example": "debug"}}`. See
[ADR-008](../../docs/decisions/ADR-008-config-level-keys.md).

**`is_debug_enabled()` returns `True` at `info` level**
This should not happen with the current implementation. If you observe this,
check whether a stale `LoggerCategoryCache` from a previous factory is being
passed explicitly. The default per-instance cache is always fresh.

**Logger emits to the wrong stdlib handler**
`ConsoleLogger` creates a stdlib logger named after the category
(`logging.getLogger(category)`). If your application calls
`logging.basicConfig()` or attaches handlers to the root logger, those handlers
will also receive these messages via propagation. Use
`logging.getLogger("com.example").propagate = False` to suppress if needed.

**`logger_factory.get_logger()` always returns `info` level**
The module-level `logger_factory` uses the module-level `config` singleton, which
reads from the current working directory. If no `application.yaml` is present and
`PY_ACTIVE_PROFILES` is not set, the level defaults to `info` (the fallback when
no `logging.level./` key is found). Create a config file or pass an explicit
`config` to `LoggerFactory`.
