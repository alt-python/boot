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

import pydbc_sqlite  # registers the SQLite driver
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

Boot loads config, creates the datasource, runs all pending Flyway migrations
during CDI startup, then starts the application. By the time any repository
bean's `init()` is called, the schema is fully applied and seeded.

## What's Included

| Class / Function | Description |
|---|---|
| `ManagedFlyway` | CDI bean that runs `migrate()` synchronously during `init()` |
| `flyway_auto_configuration(prefix, datasource_bean)` | Returns a `Singleton` list for `Context()` |
| `flyway_starter(prefix, datasource_bean)` | Alias for `flyway_auto_configuration()` |
| `DEFAULT_FLYWAY_PREFIX` | `'boot.flyway'` |

## Configuration

All properties live under `boot.flyway` by default. Override with `prefix=` to
use a different key root.

| Property | Type | Default | Description |
|---|---|---|---|
| `boot.flyway.enabled` | bool | `true` | Set to `false` to skip migration on start |
| `boot.flyway.locations` | string | `db/migration` | Comma-separated migration file paths |
| `boot.flyway.table` | string | `flyway_schema_history` | History table name |
| `boot.flyway.baseline-on-migrate` | bool | `false` | Run `baseline()` if history is empty before migrating |
| `boot.flyway.baseline-version` | string | `'1'` | Version to record in the baseline entry |
| `boot.flyway.baseline-description` | string | `'Flyway Baseline'` | Baseline entry description |
| `boot.flyway.out-of-order` | bool | `false` | Allow applying migrations older than the latest applied |
| `boot.flyway.validate-on-migrate` | bool | `true` | Validate checksums before migrating |
| `boot.flyway.installed-by` | string | `'flyway'` | User recorded in history |

## CDI Lifecycle

`ManagedFlyway` follows the standard CDI lifecycle:

1. `set_application_context(ctx)` — CDI injects the application context.
2. `init()` — reads config, creates a `Flyway` instance, calls `migrate()`.
   The schema is fully applied before `init()` returns.
3. Downstream beans start after `init()` completes — repositories and services
   can query the database immediately.

> **Python vs JavaScript difference.** The JS port (`@alt-javascript/boot-flyway`)
> stores the migration promise and exposes a `ready()` method because JS CDI
> does not await `async init()`. Python CDI is synchronous — `migrate()` completes
> inside `init()`, so no `ready()` call is needed.

## Accessing the Flyway Instance

`ManagedFlyway.get_flyway()` returns the underlying `Flyway` instance for
`info()`, `validate()`, `repair()`, and `clean()`:

```python
managed_flyway = ctx.get('managed_flyway')
flyway = managed_flyway.get_flyway()

# Check migration status
for m in flyway.info():
    print(m['version'], m['state'], m['description'])

# Validate checksums against files on disk
flyway.validate()

# Remove failed history entries
result = flyway.repair()
print(result['removed_entries'])
```

## Multiple Datasources

To run Flyway migrations against two independent datasources, use
`DataSourceBuilder` and two `flyway_starter()` calls with different prefixes and
explicit CDI bean names.

```python
# invoke.py
from boot import Boot
from cdi import Context, Singleton
from boot_pydbc import pydbc_auto_configuration, DataSourceBuilder
from boot_flyway import flyway_starter, ManagedFlyway

# Primary datasource — uses boot.datasource.* and boot.flyway.*
# Produces: data_source, pydbc_template, managed_flyway
notes_beans = pydbc_auto_configuration() + flyway_starter()

# Secondary datasource — uses boot.datasource-tags.* and boot.flyway-tags.*
# DataSourceBuilder produces beans named tags_data_source, tags_pydbc_template, etc.
tags_ds = (
    DataSourceBuilder.create()
    .prefix('boot.datasource-tags')
    .bean_names({
        'data_source': 'tags_data_source',
        'pydbc_template': 'tags_pydbc_template',
        'named_parameter_pydbc_template': 'tags_named_pydbc_template',
        'schema_initializer': 'tags_schema_initializer',
    })
    .without_schema_initializer()
    .build()
)

# flyway_starter for the tags DB — must use a unique CDI name
tags_flyway_raw = flyway_starter(
    prefix='boot.flyway-tags',
    datasource_bean='tags_data_source',
)
# Re-create with name='managed_flyway_tags' so it coexists with managed_flyway
tags_flyway = []
for comp in tags_flyway_raw:
    if comp.name == 'managed_flyway':
        tags_flyway.append(Singleton({
            'reference': comp.reference,
            'name': 'managed_flyway_tags',
            'depends_on': 'tags_data_source',
            'properties': [{'name': 'data_source', 'reference': 'tags_data_source'}],
        }))
    else:
        tags_flyway.append(comp)

Boot.boot({
    'contexts': [
        Context(notes_beans + tags_ds + tags_flyway),
        Context([Singleton(NoteRepository), Singleton(TagRepository), Singleton(Application)]),
    ]
})
```

Config:

```json
{
  "boot": {
    "datasource": {
      "url": "pydbc:sqlite::memory:",
      "pool": { "enabled": true, "max": 2 }
    },
    "datasource-tags": {
      "url": "pydbc:sqlite::memory:",
      "pool": { "enabled": true, "max": 2 }
    },
    "flyway": {
      "locations": "db/notes-migration"
    },
    "flyway-tags": {
      "locations": "db/tags-migration"
    }
  }
}
```

See [`packages/example-5-4-persistence-flyway-multidb`](../example-5-4-persistence-flyway-multidb)
for a complete runnable example.

## Running Tests

```bash
uv run pytest packages/boot-flyway -v
```

## Troubleshooting

**`KeyError: 'managed_flyway'` when two Flyway runners share a context**
Each `flyway_starter()` call produces a `managed_flyway` bean. The second one
will clash with the first. Re-create the second starter's component with a
distinct name (`managed_flyway_tags`, etc.) as shown in the multi-datasource
example above.

**Migrations run but the schema is missing when the repository queries it**
Check that `ManagedFlyway` is listed before your repository beans in the CDI
context, or add `depends_on='managed_flyway'` to the repository component. CDI
initialises beans in dependency order.

**`boot.flyway.enabled: false` does not suppress migration**
The `enabled` key must be a boolean in the config file, not a string. Use
`"enabled": false` (JSON) or `enabled: false` (YAML), not `"enabled": "false"`.

## License

MIT
