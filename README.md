# alt-python/boot

[![Language](https://img.shields.io/badge/language-Python-3776ab.svg)](https://www.python.org/)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

A Spring-inspired configuration and logging library for Python. Hierarchical
property sources, profile-aware config file discovery, jasypt-compatible PBE
encryption, and config-driven structured logging — all in pure Python with no
framework dependencies.

Port of the [`@alt-javascript/boot`](https://github.com/alt-javascript/boot)
monorepo (config and logger packages) to Python, with
[`@alt-javascript/jasypt`](https://github.com/alt-javascript/jasypt) ported as
`pysypt`.

## Why

Python has `logging` (stdlib), `configparser` (stdlib), `python-dotenv`, and a
dozen opinionated config frameworks — none of which gives you Spring Boot's
clean combination of: profile-based file overlays, relaxed environment variable
binding, transparent encrypted-value decryption, placeholder substitution, and
a config-driven logger hierarchy that wires all of it together. This library
fills that gap.

## Quick Start

```bash
uv add pysypt config logger   # or: pip install pysypt config logger
```

```python
from config import config
from logger import logger_factory

# Read config (discovers application.yaml / .properties / .json / .env)
port = config.get("server.port", 8080)
name = config.get("app.name")

# Encrypted values are decrypted transparently
secret = config.get("app.secret")   # ENC(...) → plaintext

# Structured logging driven by config levels
log = logger_factory.get_logger("com.example.MyService")
log.info("Application started", {"port": port})
log.debug("This is suppressed unless logging.level.com.example is debug")
```

## Packages

| Package | Purpose |
|---|---|
| [`pysypt`](packages/pysypt) | Jasypt-compatible PBE encryption and iterated-hash digest |
| [`config`](packages/config) | Profile-aware layered configuration with env binding and value resolution |
| [`logger`](packages/logger) | Config-driven structured logger with dot-hierarchy category levels |
| [`common`](packages/common) | Shared utilities: `is_empty`, `is_plain_object` |

## Monorepo Layout

```
packages/
  common/         # Shared utilities
  pysypt/         # PBE encryption + digest
  config/         # Config stack
  logger/         # Logger stack
docs/
  decisions/      # Architecture Decision Records (ADRs)
pyproject.toml    # uv workspace root
.python-version   # Python 3.12
```

## Configuration

Place config files in your project root or a `config/` subdirectory:

```
application.yaml          # base config
application-dev.yaml      # dev profile overlay
application.env           # base .env variables
application-dev.env       # dev .env overlay
application.properties    # Java .properties format also supported
```

Activate profiles via the `PY_ACTIVE_PROFILES` environment variable:

```bash
PY_ACTIVE_PROFILES=dev python main.py
```

Config values follow a strict precedence chain (highest to lowest):

1. Programmatic overrides
2. Process environment variables (relaxed binding: `SERVER_PORT` → `server.port`)
3. Profile `.env` files
4. Default `.env` file (`application.env`)
5. Profile structured files
6. Default structured files
7. Fallback

## Encrypted Values

Encrypt config values with `pysypt` and store them as `ENC(...)` or `enc.<b64>`:

```bash
python -c "from pysypt import Jasypt; print(Jasypt().encrypt('mysecret', 'mypassphrase'))"
```

```yaml
# application.yaml
db:
  password: ENC(Ho8XdYf6/r+FdJ/ZC55BBA==)
```

Set `PY_CONFIG_PASSPHRASE` in the environment and call `config.get("db.password")` — the decryption is transparent.

## Logging

Log levels are driven by config under `logging.level`. The hierarchy uses
dot-separated category names:

```yaml
logging:
  level:
    /:           warn       # root level
    com:
      example:   debug      # com.example.* → debug
  format: json              # json (default) or text
```

```python
from logger import logger_factory

svc = logger_factory.get_logger("com.example.MyService")  # → debug
web = logger_factory.get_logger("other.pkg.Handler")       # → warn
```

## Documentation

- **[pysypt README](packages/pysypt/README.md)** — PBE encryption API and algorithm reference
- **[config README](packages/config/README.md)** — Config sources, profiles, formats, and value resolution
- **[logger README](packages/logger/README.md)** — Logger hierarchy, levels, formatters, and test utilities

### Architecture Decision Records

| ADR | Title |
|---|---|
| [ADR-001](docs/decisions/ADR-001-python-toolchain.md) | Python 3.12 + uv via Homebrew |
| [ADR-002](docs/decisions/ADR-002-env-var-naming.md) | Python-native environment variable names |
| [ADR-003](docs/decisions/ADR-003-logger-category-separator.md) | Dot-separated logger category hierarchy |
| [ADR-004](docs/decisions/ADR-004-logger-backend.md) | Wrap stdlib logging as the logger backend |
| [ADR-005](docs/decisions/ADR-005-pbe1-des-emulation.md) | Single DES emulated via TripleDES-EDE |
| [ADR-006](docs/decisions/ADR-006-rc2-rc4-omitted.md) | RC2 and RC4 algorithms not ported |
| [ADR-007](docs/decisions/ADR-007-logger-level-ordering.md) | Preserve JS level ordering for internal comparisons |
| [ADR-008](docs/decisions/ADR-008-config-level-keys.md) | Config level keys use nested dicts |
| [ADR-009](docs/decisions/ADR-009-per-instance-logger-cache.md) | LoggerFactory uses per-instance category cache |

## Running Tests

```bash
uv run pytest packages/ -v
```

## License

MIT
