# alt-python-boot-flyway

[![Language](https://img.shields.io/badge/language-Python-3776ab.svg)](https://www.python.org/)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Spring Boot-style CDI auto-configuration for Flyway-inspired database
migrations. Registers a `ManagedFlyway` CDI bean that runs `migrate()`
synchronously during `init()`, reading all configuration from `boot.flyway.*`.

Port of [`@alt-javascript/boot-flyway`](https://github.com/alt-javascript/boot/tree/main/packages/boot-flyway).

Part of the [`alt-python/boot`](https://github.com/alt-python/boot) monorepo.

## Install

```bash
uv add alt-python-boot-flyway pydbc-sqlite
```

Requires Python 3.12+, `alt-python-boot-pydbc`, and `alt-python-flyway`.

## Quick Start

```python
# invoke.py
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import pydbc_sqlite
from boot import Boot
from cdi import Context, Singleton
from boot_pydbc import pydbc_auto_configuration
from boot_flyway import flyway_starter
from services import NoteRepository, Application

Boot.boot({
    'contexts': [
        Context(pydbc_auto_configuration() + flyway_starter()),
        Context([Singleton(NoteRepository), Singleton(Application)]),
    ]
})
```

```json
// config/application.json
{
  "boot": {
    "datasource": {
      "url": "pydbc:sqlite::memory:",
      "pool": { "enabled": true, "max": 2 }
    },
    "flyway": {
      "locations": "db/migration"
    }
  }
}
```

Boot reads config, creates the datasource, runs all pending Flyway migrations,
then starts the application. By the time `NoteRepository.init()` is called, the
schema is fully applied.

## What's Included

| Class / Function | Description |
|---|---|
| `ManagedFlyway` | CDI bean that runs `migrate()` synchronously during `init()` |
| `flyway_auto_configuration(prefix, datasource_bean)` | Returns CDI `Singleton` list |
| `flyway_starter(prefix, datasource_bean)` | Alias for `flyway_auto_configuration()` |
| `DEFAULT_FLYWAY_PREFIX` | `'boot.flyway'` |

## Configuration

All properties are under `boot.flyway` by default (override with `prefix=`).

| Property | Type | Default | Description |
|---|---|---|---|
| `boot.flyway.enabled` | bool | `true` | Set to `false` to skip migration entirely |
| `boot.flyway.locations` | string | `db/migration` | Comma-separated migration file paths |
| `boot.flyway.table` | string | `flyway_schema_history` | History table name |
| `boot.flyway.baseline-on-migrate` | bool | `false` | Run `baseline()` if history is empty |
| `boot.flyway.baseline-version` | string | `1` | Version to use for baseline |
| `boot.flyway.baseline-description` | string | `Flyway Baseline` | Baseline description |
| `boot.flyway.out-of-order` | bool | `false` | Allow out-of-order migrations |
| `boot.flyway.validate-on-migrate` | bool | `true` | Validate checksums before migrating |
| `boot.flyway.installed-by` | string | `flyway` | User recorded in history |

## CDI Lifecycle

`ManagedFlyway` uses the standard CDI lifecycle:

1. `set_application_context(ctx)` — CDI injects the application context
2. `init()` — reads config, creates `Flyway` instance, calls `migrate()`
3. Downstream beans (repositories, services) start *after* `init()` returns —
   the schema is fully applied before any bean that uses the datasource starts

This differs from the JS port (`@alt-javascript/boot-flyway`) where CDI does
not await async `init()`, requiring a `managed_flyway.ready()` call. The Python
CDI runtime is synchronous — no `ready()` needed.

## Multi-Datasource Example

Use `DataSourceBuilder` and `flyway_auto_configuration()` with custom prefixes
for multiple independent datasources each with their own migrations:

```python
from boot import Boot
from cdi import Context, Singleton
from boot_pydbc import pydbc_auto_configuration, DataSourceBuilder
from boot_flyway import flyway_auto_configuration

notes_ds = (
    DataSourceBuilder.create()
    .prefix('myapp.notes')
    .bean_names({'data_source': 'notes_ds', 'pydbc_template': 'notes_template',
                 'named_parameter_pydbc_template': 'notes_named_template',
                 'schema_initializer': 'notes_schema_init'})
    .without_schema_initializer()
    .build()
)

tags_ds = (
    DataSourceBuilder.create()
    .prefix('myapp.tags')
    .bean_names({'data_source': 'tags_ds', 'pydbc_template': 'tags_template',
                 'named_parameter_pydbc_template': 'tags_named_template',
                 'schema_initializer': 'tags_schema_init'})
    .without_schema_initializer()
    .build()
)

notes_flyway = flyway_auto_configuration(
    prefix='myapp.notes.flyway',
    datasource_bean='notes_ds',
)
notes_flyway[0].__class__.__name__ = 'notesManagedFlyway'  # unique CDI name

tags_flyway = flyway_auto_configuration(
    prefix='myapp.tags.flyway',
    datasource_bean='tags_ds',
)
tags_flyway[0].__class__.__name__ = 'tagsManagedFlyway'

Boot.boot({
    'contexts': [
        Context(notes_ds + tags_ds + notes_flyway + tags_flyway),
        Context([Singleton(NoteRepository), Singleton(Application)]),
    ]
})
```

Config:

```json
{
  "myapp": {
    "notes": {
      "url": "pydbc:sqlite::memory:",
      "pool": { "enabled": true, "max": 2 },
      "flyway": { "locations": "db/notes-migration" }
    },
    "tags": {
      "url": "pydbc:sqlite::memory:",
      "pool": { "enabled": true, "max": 2 },
      "flyway": { "locations": "db/tags-migration" }
    }
  }
}
```

See `packages/example-5-4-persistence-flyway-multidb` for a complete
runnable example.

## Accessing the Flyway Instance

`ManagedFlyway` exposes the underlying `Flyway` instance for `info()`,
`validate()`, `repair()`, etc.:

```python
managed_flyway = ctx.get('managed_flyway')
flyway = managed_flyway.get_flyway()

for m in flyway.info():
    print(m['version'], m['state'])

flyway.validate()    # raises FlywayValidationError on checksum drift
result = flyway.repair()
```

## Running Tests

```bash
uv run pytest packages/boot-flyway -v
```

## License

MIT
