# alt-python-boot-pydbc

[![Language](https://img.shields.io/badge/language-Python-3776ab.svg)](https://www.python.org/)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Spring Boot-style CDI auto-configuration for relational databases via
[pydbc](https://github.com/alt-python/pydbc). Provides `PydbcTemplate`,
`NamedParameterPydbcTemplate`, and a CDI auto-configuration factory that wires
a `DataSource`, SQL template, and `SchemaInitializer` into a Boot application
from a single config property.

Part of the [`alt-python/boot`](https://github.com/alt-python/boot) monorepo.

## Quick Start

```bash
uv add alt-python-boot-pydbc pydbc-sqlite
```

```python
# invoke.py
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))  # resolve config/ relative to this file

from boot import Boot
from cdi import Context, Singleton
from boot_pydbc import pydbc_auto_configuration

from services import NoteRepository, Application

Boot.boot({
    'contexts': [
        Context(pydbc_auto_configuration()),
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
      "pool": { "enabled": true, "max": 1 }
    }
  }
}
```

Boot reads `config/application.json`, creates a `PooledDataSource`, runs
`config/schema.sql` and `config/data.sql`, then starts the application.

## What's Included

| Class / Function | Description |
|---|---|
| `PydbcTemplate` | Execute SQL with positional `?` parameters |
| `NamedParameterPydbcTemplate` | Execute SQL with named `:param` parameters |
| `ConfiguredDataSource` | CDI bean that reads `boot.datasource.*` config |
| `SchemaInitializer` | CDI bean that runs `config/schema.sql` + `config/data.sql` at startup |
| `DataSourceBuilder` | Fluent builder for secondary datasources |
| `pydbc_auto_configuration()` | Returns 4 CDI Singletons ready for `Context()` |
| `pydbc_template_starter()` | One-call `Boot.boot()` entry point |
| `DEFAULT_PREFIX` | `'boot.datasource'` |

## Configuration

All properties are under `boot.datasource` by default (override with a custom prefix).

| Property | Type | Default | Description |
|---|---|---|---|
| `boot.datasource.url` | string | — | pydbc JDBC-style URL, e.g. `pydbc:sqlite::memory:` |
| `boot.datasource.username` | string | — | Username (optional) |
| `boot.datasource.password` | string | — | Password (optional) |
| `boot.datasource.pool.enabled` | bool | `false` | Use `PooledDataSource` instead of `DataSource` |
| `boot.datasource.pool.min` | int | — | Pool minimum size |
| `boot.datasource.pool.max` | int | — | Pool maximum size |
| `boot.datasource.initialize` | bool | `true` | Set to `false` to skip schema initialisation |
| `boot.datasource.schema` | string | `config/schema.sql` | Path to DDL file |
| `boot.datasource.data` | string | `config/data.sql` | Path to seed data file |

If `boot.datasource.url` is absent, the `ConfiguredDataSource` bean is still
registered but its `_delegate` is `None`. Calling `get_connection()` will raise
`RuntimeError`. This lets you deploy with an optional datasource without
breaking the CDI wiring.

## PydbcTemplate

`PydbcTemplate` wraps a `DataSource` and provides four methods:

```python
from boot_pydbc import PydbcTemplate

template = PydbcTemplate(data_source)

# DDL
template.execute('CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT)')

# DML — returns affected row count
count = template.update('INSERT INTO notes VALUES (?, ?)', (1, 'hello'))

# Query — returns list of row dicts
rows = template.query_for_list('SELECT * FROM notes')

# Query — returns exactly one row or raises RuntimeError
row = template.query_for_object('SELECT * FROM notes WHERE id = ?', (1,))
```

Column names are returned by the underlying driver. With `pydbc-sqlite`, column
names are uppercase (`ID`, `BODY`). Normalise in a row mapper:

```python
def row_mapper(row, _index):
    return {k.lower(): v for k, v in row.items()}

notes = template.query_for_list('SELECT * FROM notes', row_mapper=row_mapper)
```

## NamedParameterPydbcTemplate

`NamedParameterPydbcTemplate` wraps `PydbcTemplate` and converts `:param_name`
placeholders to positional `?` via `ParamstyleNormalizer`:

```python
from boot_pydbc import NamedParameterPydbcTemplate

template = NamedParameterPydbcTemplate(data_source)

template.update(
    'INSERT INTO notes VALUES (:id, :body)',
    {'id': 1, 'body': 'hello'},
)

rows = template.query_for_list(
    'SELECT * FROM notes WHERE id = :id',
    {'id': 1},
)
```

## SchemaInitializer

When `boot.datasource.url` is configured, `SchemaInitializer.init()` runs
`config/schema.sql` followed by `config/data.sql` before any application bean
is used. Both files are optional — if either is absent, it is silently skipped.

```sql
-- config/schema.sql
CREATE TABLE IF NOT EXISTS notes (
    id    INTEGER PRIMARY KEY,
    title TEXT    NOT NULL,
    body  TEXT,
    done  INTEGER NOT NULL DEFAULT 0
);

-- config/data.sql
INSERT INTO notes (id, title, body) VALUES (1, 'First note', '');
INSERT INTO notes (id, title, body) VALUES (2, 'Second note', '');
```

Set `boot.datasource.initialize: false` in config to skip initialisation
entirely (useful for production environments where schema is managed separately).

## Secondary Datasources

`DataSourceBuilder` creates a second set of CDI beans with a custom config
prefix and custom bean names:

```python
from boot_pydbc import DataSourceBuilder
from cdi import Context

reporting_beans = (
    DataSourceBuilder.create()
    .prefix('myapp.reporting')
    .bean_names({
        'data_source': 'reporting_ds',
        'pydbc_template': 'reporting_template',
        'named_parameter_pydbc_template': 'reporting_named_template',
        'schema_initializer': 'reporting_schema_initializer',
    })
    .build()
)

# Or skip the schema initializer entirely:
read_only_beans = (
    DataSourceBuilder.create()
    .prefix('myapp.readonly')
    .without_schema_initializer()
    .build()
)

ctx = Context([*pydbc_auto_configuration(), *reporting_beans, ...])
```

Config for the secondary datasource lives under `myapp.reporting.*`:

```json
{
  "myapp": {
    "reporting": {
      "url": "pydbc:sqlite:reporting.db"
    }
  }
}
```

## Using with Boot

### `pydbc_auto_configuration()`

Returns a flat list of 4 `Singleton` beans. Concatenate with your application
beans and pass to `Context()`:

```python
from boot import Boot
from cdi import Context, Singleton
from boot_pydbc import pydbc_auto_configuration

Boot.boot({
    'contexts': [
        Context(pydbc_auto_configuration()),
        Context([Singleton(MyService), Singleton(MyApp)]),
    ]
})
```

### `pydbc_template_starter()`

One-call entry point for applications that need only a single datasource:

```python
from boot_pydbc import pydbc_template_starter
from cdi import Context, Singleton

pydbc_template_starter({
    'contexts': [Context([Singleton(MyService), Singleton(MyApp)])],
})
```

## SQLite In-Memory Databases

When using an in-memory SQLite URL (`pydbc:sqlite::memory:`), you **must** use a
connection pool to prevent `PydbcTemplate` from destroying the database on
`conn.close()`:

```json
{
  "boot": {
    "datasource": {
      "url": "pydbc:sqlite::memory:",
      "pool": { "enabled": true, "max": 1 }
    }
  }
}
```

Without the pool, the `finally: conn.close()` block in `PydbcTemplate` closes
the DBAPI connection, which destroys the in-memory database. With
`PooledDataSource(max=1)`, `conn.close()` returns the connection to the pool
instead.

## Running Tests

```bash
uv run pytest packages/boot-pydbc -v
```

## License

MIT
