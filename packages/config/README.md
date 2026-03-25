# config

[![Language](https://img.shields.io/badge/language-Python-3776ab.svg)](https://www.python.org/)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Hierarchical, profile-aware configuration for Python. Supports YAML, JSON, Java
`.properties`, and `.env` files, environment variable binding with relaxed naming,
placeholder resolution, and transparent jasypt-compatible decryption — with
Spring Boot-aligned precedence.

Port of [`@alt-javascript/config`](https://github.com/alt-javascript/boot/tree/main/packages/config)
to Python.

## Install

```bash
uv add config        # or: pip install config
```

Requires Python 3.12+, `PyYAML` >= 6 (for YAML files), and `pysypt` (for
`ENC(...)` decryption).

## Quick Start

### In-memory config

```python
from config import EphemeralConfig, ConfigFactory

# Simple lookup
cfg = EphemeralConfig({
    "db": {"host": "localhost", "port": 5432},
    "logging": {"level": {"/": "info"}},
})

cfg.get("db.host")         # "localhost"
cfg.get("db.port")         # 5432
cfg.get("missing", "def")  # "def"
cfg.has("db.host")         # True

# Wrap for placeholder resolution and ENC() decryption
extended = ConfigFactory.get_config(config=cfg)
```

### Profile-based config (Spring-aligned)

```python
from config import config   # module-level singleton

port = config.get("server.port")
name = config.get("app.name", "unnamed")
```

The singleton discovers config files from `config/` and the current working
directory. Set `PY_ACTIVE_PROFILES` to activate profile overlays.

## Property Source Precedence

When using `ProfileConfigLoader`, sources are queried in this order (highest
priority first):

| Priority | Source |
|---|---|
| 1 | Programmatic overrides |
| 2 | Environment variables (`os.environ`) with relaxed binding |
| 3 | Profile `.env` files (`application-{profile}.env`) |
| 4 | Default `.env` file (`application.env`) |
| 5 | Profile structured files (`application-{profile}.{yaml,json,properties}`) |
| 6 | Default structured files (`application.{yaml,json,properties}`) |
| 7 | Fallback (explicit dict or config-like object) |

Real environment variables (priority 2) always win over `.env` file values
(priority 3–4) — `.env` files never override what the shell or container already
provides.

## File Formats

Files are discovered in `config/` first, then the current working directory.
All matching files at each level are loaded and merged.

### YAML

```yaml
# application.yaml
app:
  name: My App
  secret: ENC(Ho8XdYf6/r+FdJ/ZC55BBA==)
server:
  port: 8080
```

### JSON

```json
{
  "app": { "name": "My App" },
  "server": { "port": 8080 }
}
```

### `.properties`

Full Java `.properties` support:

```properties
# application.properties
app.name=My App
server.port=8080
security.roles[0]=USER
security.roles[1]=ADMIN
servers[0].host=web1.example.com
```

Supports `key=value`, `key:value`, and `key value` separators; `#`/`!` comment
lines; `\` line continuation; standard escape sequences; and `\uXXXX` Unicode.
Dotted keys produce nested dicts. Array notation (`key[0]=value`) produces
Python lists.

### `.env`

```bash
# application.env
DB_HOST=localhost
DB_PORT=5432
export API_KEY=abc123           # export prefix stripped
SECRET="contains spaces"        # double-quoted: escapes processed
NOTE='literal \n value'         # single-quoted: no escape processing
INLINE=value # this is a comment   # inline comment (must follow whitespace)
```

`.env` values pass through `EnvPropertySource`, so relaxed binding applies:

| `.env` key | Config path |
|---|---|
| `DB_HOST` | `db.host` |
| `MY_APP_PORT` | `my.app.port` |
| `APP__NAME` | `app.name` (double underscore → dot) |

## Profiles

Activate profiles with `PY_ACTIVE_PROFILES` (comma-separated):

```bash
PY_ACTIVE_PROFILES=dev,local python main.py
```

Or pass `profiles=` directly:

```python
from config import ProfileConfigLoader

chain = ProfileConfigLoader.load(
    base_path="/etc/myapp",
    profiles="dev,local",
)
```

Profile files override defaults at the same path. Later profiles in the list
override earlier ones.

## Environment Variable Binding

Environment variables are available with relaxed binding:

| Environment variable | Config path |
|---|---|
| `SERVER_PORT` | `server.port` |
| `DB_HOST` | `db.host` |
| `APP__NAME` | `app.name` |

The original uppercase key is also accessible directly (`config.get("SERVER_PORT")`).

## Placeholder Resolution

Reference other config values using `${path}` or `${path:default}`:

```yaml
base_url: http://localhost:8080
api_url: "${base_url}/api"
```

```python
config.get("api_url")  # "http://localhost:8080/api"
```

Unresolvable placeholders are returned as-is without error.

## Encrypted Values

Set `PY_CONFIG_PASSPHRASE` in the environment, then store encrypted values as
`ENC(...)` or `enc.<b64>`:

```bash
python -c "
from pysypt import Jasypt
print(Jasypt().encrypt('mysecret', 'mypassphrase'))
"
```

```yaml
# application.yaml
db:
  password: ENC(Ho8XdYf6/r+FdJ/ZC55BBA==)
```

```bash
PY_CONFIG_PASSPHRASE=mypassphrase python main.py
```

```python
config.get("db.password")   # "mysecret"
```

Both `ENC(...)` (parenthesis notation) and `enc.<b64>` (prefix notation) are
decrypted transparently on `get()`.

## API Reference

### `EphemeralConfig(obj)`

Lightweight config backed by a plain dict.

| Method | Description |
|---|---|
| `get(path, default=MISSING)` | Get a value by dot-notation path. Raises `KeyError` if missing and no default given. |
| `has(path)` | Return `True` if the path exists, including paths with falsy values (`0`, `False`, `""`). |

`path` uses dot notation: `"server.port"` traverses `obj["server"]["port"]`.
A flat key with a literal dot (e.g. `obj["a.b"]`) is also accessible.

### `PropertySourceChain(sources)`

Ordered list of config sources. Queries them in index order; first source that
has the path wins.

| Method | Description |
|---|---|
| `has(path)` | Return `True` if any source has the path. |
| `get(path, default=MISSING)` | Return the first value found. Raises `KeyError` if no source has it and no default given. |
| `add_source(source, priority=None)` | Add a source. Lower index = higher priority. Appends to end if `priority` is omitted. |

### `EnvPropertySource(env=None)`

Wraps an environment variable dict with relaxed binding.

| Method | Description |
|---|---|
| `has(path)` | Check by exact key or relaxed dotted form. |
| `get(path, default=None)` | Return value or default. |

### `PropertiesParser`

| Method | Description |
|---|---|
| `PropertiesParser.parse(text)` | Parse a `.properties` string into a nested dict. |

### `DotEnvParser`

| Method | Description |
|---|---|
| `DotEnvParser.parse(text)` | Parse a `.env` string into a flat `{KEY: value}` dict. |

### `ProfileConfigLoader`

| Method | Description |
|---|---|
| `ProfileConfigLoader.load(overrides=None, fallback=None, base_path=None, profiles=None, env=None, name="application")` | Build a `PropertySourceChain` with full Spring-aligned precedence. |

Parameters:

| Parameter | Type | Description |
|---|---|---|
| `overrides` | `dict` | Programmatic overrides (highest priority) |
| `fallback` | `dict` or config-like | Fallback source (lowest priority) |
| `base_path` | `str` | Base directory for file discovery (default: `cwd`) |
| `profiles` | `str` | Comma-separated profile names (default: `PY_ACTIVE_PROFILES` env var) |
| `env` | `dict` | Environment variables (default: `os.environ`) |
| `name` | `str` | Config file base name (default: `"application"`) |

### `ConfigFactory`

| Method | Description |
|---|---|
| `ConfigFactory.get_config(config=None, resolver=None, password=None)` | Build a `ValueResolvingConfig` with the full resolver chain (placeholders, ENC() decryption). |
| `ConfigFactory.load_config(**kwargs)` | Convenience alias for `ProfileConfigLoader.load()`. |

### `ValueResolvingConfig(config, resolver, path=None)`

Config wrapper that applies the resolver chain at `get()` time.

| Method | Description |
|---|---|
| `has(path)` | Delegates to the backing config. |
| `get(path, default=MISSING)` | Resolves and returns the value at `path` after applying all resolvers. |

### Selectors

| Class | Matches | `resolve_value()` |
|---|---|---|
| `PrefixSelector(prefix)` | Values starting with `prefix` | Strips prefix |
| `ParenthesisSelector(prefix)` | `PREFIX(value)` notation | Returns the inner value |
| `PlaceholderSelector()` | Values containing `${...}` | n/a (used by PlaceholderResolver) |

### Resolvers

| Class | Description |
|---|---|
| `Resolver` | Abstract base. Provides `map_values_deep(values, callback)`. |
| `SelectiveResolver(selector)` | Base for resolvers that only process matching values. |
| `DelegatingResolver(resolvers)` | Chains multiple resolvers in sequence. |
| `PlaceholderResolver(selector, reference)` | Resolves `${path}` and `${path:default}` placeholders. |
| `JasyptDecryptor(selector, password)` | Decrypts `enc.<b64>` and `ENC(<b64>)` values via `pysypt`. |

## All Exports

```python
from config import (
    EphemeralConfig,
    PropertySourceChain,
    EnvPropertySource,
    PropertiesParser,
    DotEnvParser,
    ProfileConfigLoader,
    Selector,
    PrefixSelector,
    ParenthesisSelector,
    PlaceholderSelector,
    Resolver,
    SelectiveResolver,
    DelegatingResolver,
    PlaceholderResolver,
    JasyptDecryptor,
    ValueResolvingConfig,
    ConfigFactory,
    config,        # module-level singleton
)
```

## Troubleshooting

**`KeyError: Config path 'x.y' not found`**
The path does not exist in any source and no default was given. Use `has("x.y")`
first, or pass a default: `config.get("x.y", None)`.

**`ENC(...)` value is returned as-is, not decrypted**
Either `PY_CONFIG_PASSPHRASE` is not set, or the value was encrypted with a
different password. Set the env var, or pass `password=` to `ConfigFactory.get_config()`.

**Profile overlay not applied**
Check that `PY_ACTIVE_PROFILES=dev` is set in the environment, or pass
`profiles="dev"` to `ProfileConfigLoader.load()`. Verify the profile file exists
at `application-dev.yaml` (or `.json`, `.properties`, `.env`).

**YAML file not loaded**
`PyYAML` must be installed: `pip install PyYAML`. The loader raises `ImportError`
with a clear message if it encounters a `.yaml` file without the parser available.

**`.env` file values not accessible via dot path**
`.env` files are loaded via `EnvPropertySource`, which applies relaxed binding.
`DB_HOST` is accessible as `db.host` or `DB_HOST`. The exact dotted path
`"db.host"` only works if the variable name is `DB_HOST` — not `db.host`.
