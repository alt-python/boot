# Configuration

The `config` package provides hierarchical, profile-aware configuration with
multiple source types. Two approaches are available:

1. **`EphemeralConfig`** — in-memory config backed by a plain dict. Best for
   tests and simple cases.
2. **`ProfileConfigLoader`** — file-based config with Spring Boot-aligned
   precedence: profile overlays, environment variable binding, and
   `${placeholder}` resolution.

Both expose the same interface: `has(path)` and `get(path, default)`.

## EphemeralConfig

For tests or bootstrapping in code:

```python
from config import EphemeralConfig

cfg = EphemeralConfig({
    "db": {"host": "localhost", "port": 5432},
    "logging": {"level": {"/": "info"}},
})

cfg.get("db.host")         # "localhost"
cfg.get("db.port")         # 5432
cfg.get("missing", "def")  # "def"
cfg.has("db.host")         # True
```

## ProfileConfigLoader

Load config from files with profile overrides and environment variable
injection:

```python
from config import ProfileConfigLoader

chain = ProfileConfigLoader.load(profiles="dev,local")
chain.get("server.port")  # from application-local.yaml, application-dev.json, or application.yaml
chain.get("db.host")      # from DB_HOST environment variable via relaxed binding
```

The module-level singleton `from config import config` calls
`ConfigFactory.get_config()` which builds a fully-configured
`ValueResolvingConfig` (placeholders + `ENC(...)` decryption) backed by
`ProfileConfigLoader`.

## Property Source Precedence

Sources are queried in this order (highest priority first):

| Priority | Source |
|---|---|
| 1 | Programmatic overrides |
| 2 | Environment variables (`os.environ`) with relaxed binding |
| 3 | Profile `.env` files (`application-{profile}.env`) |
| 4 | Default `.env` file (`application.env`) |
| 5 | Profile structured files (`application-{profile}.{yaml,json,properties}`) |
| 6 | Default structured files (`application.{yaml,json,properties}`) |
| 7 | Fallback (explicit dict) |

Real environment variables always win over `.env` file values — `.env` files
never override what the shell or container already sets.

## File Discovery

The loader searches `config/` first, then the current working directory, for
files named `application.{yaml,yml,json,properties,env}` and
`application-{profile}.{yaml,yml,json,properties,env}`.

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

```properties
# application.properties
app.name=My App
server.port=8080
security.roles[0]=USER
security.roles[1]=ADMIN
```

Supports `key=value`, `key:value`, and `key value` separators; `#`/`!` comment
lines; `\` line continuation; `\uXXXX` Unicode; and array notation
(`key[0]=value` → Python list).

### `.env`

```bash
# application.env
DB_HOST=localhost
DB_PORT=5432
export API_KEY=abc123           # export prefix stripped
SECRET="contains spaces"        # double-quoted: escapes processed
NOTE='literal \n value'         # single-quoted: no escape processing
INLINE=value # this is a comment
```

## Profiles

Activate profiles with `PY_ACTIVE_PROFILES` (comma-separated):

```bash
PY_ACTIVE_PROFILES=dev,local python main.py
```

Or pass `profiles=` directly:

```python
chain = ProfileConfigLoader.load(profiles="dev,local")
```

Profile files override defaults for the same path. Later profiles in the list
override earlier ones.

## Environment Variable Binding

Environment variables are available via relaxed binding — underscores become
dots and keys are lowercased:

| Environment variable | Config path |
|---|---|
| `SERVER_PORT` | `server.port` |
| `DB_HOST` | `db.host` |
| `APP__NAME` | `app.name` (double underscore → dot) |

The original uppercase key is also accessible directly:
`config.get("SERVER_PORT")`.

## Placeholder Resolution

Reference other config values using `${path}` or `${path:default}`:

```yaml
base_url: http://localhost:8080
api_url: "${base_url}/api"
```

```python
config.get("api_url")  # "http://localhost:8080/api"
```

Unresolvable placeholders are returned as-is. CDI property placeholders in bean
constructors use the same syntax — see [Dependency Injection](dependency-injection.md).

## Encrypted Values

Store secrets as `ENC(...)` or `enc.<b64>` and set `PY_CONFIG_PASSPHRASE` in
the environment. Decryption is transparent on `get()`:

```bash
python -c "from pysypt import Jasypt; print(Jasypt().encrypt('mysecret', 'mypassphrase'))"
# ENC(nsbC5r0ymz740/aURtuRWw==)
```

```yaml
# application.yaml
db:
  password: ENC(nsbC5r0ymz740/aURtuRWw==)
```

```bash
PY_CONFIG_PASSPHRASE=mypassphrase python main.py
```

```python
config.get("db.password")  # "mysecret"
```

See [pysypt README](../packages/pysypt/README.md) for all supported encryption
algorithms. `PBEWITHHMACSHA256ANDAES_256` is recommended for new deployments.

## Framework Config Keys

These keys are read by the framework at runtime:

| Key | Values | Default | Description |
|---|---|---|---|
| `boot.banner-mode` | `console`, `off` | `console` | `console` prints the startup banner to stdout. `off` suppresses it. |
| `logging.level./` | level string | `info` | Root log level — applies to all loggers unless overridden. |
| `logging.level.<dot.path>` | level string | inherits root | Per-category level. Use nested dicts (see [ADR-008](decisions/ADR-008-config-level-keys.md)). |
| `logging.format` | `json`, `text` | `json` | Log output format. |
| `boot.datasource.url` | pydbc URL | — | Activates `ConfiguredDataSource` and `SchemaInitializer`. |
| `boot.nosql.url` | pynosqlc URL | — | Activates `ConfiguredClientDataSource` and `ManagedNosqlClient`. |
| `boot.flyway.locations` | path string | `db/migration` | Migration file directory for `ManagedFlyway`. |

### Example: suppress banner and set log levels

```python
from config import EphemeralConfig

cfg = EphemeralConfig({
    "boot": {"banner-mode": "off"},
    "logging": {
        "level": {
            "/": "warn",
            "com": {"example": "debug"},
        }
    },
})
```

Log level keys must use nested dicts — flat dotted keys like
`"com.example": "debug"` are not recognised by the segment walker. See
[ADR-008](decisions/ADR-008-config-level-keys.md).
