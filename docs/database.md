# Database Access

CDI-managed relational database access via `alt-python-boot-pydbc`. Provides
`PydbcTemplate` and `NamedParameterPydbcTemplate` backed by the
[pydbc](https://github.com/alt-python/pydbc) driver layer, with optional
Flyway-inspired migration management via `alt-python-boot-flyway`.

## Install

```bash
uv add alt-python-boot-pydbc pydbc-sqlite
# or: uv add alt-python-boot-pydbc pydbc-postgresql
```

Available pydbc drivers:

| Package | Database |
|---|---|
| `pydbc-sqlite` | SQLite |
| `pydbc-postgresql` | PostgreSQL |

## PydbcTemplate

```python
import pydbc_sqlite  # registers the SQLite driver
from pydbc_core import PooledDataSource
from boot_pydbc import PydbcTemplate

ds = PooledDataSource('pydbc:sqlite::memory:', pool={'max': 1})
template = PydbcTemplate(ds)

# DDL
template.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)')

# Insert — returns affected row count
template.update('INSERT INTO users (name) VALUES (?)', ('Craig',))

# Query — returns list of row dicts
users = template.query_for_list('SELECT * FROM users')
# [{'ID': 1, 'NAME': 'Craig'}]

# Query with row mapper
users = template.query_for_list(
    'SELECT * FROM users',
    row_mapper=lambda row, i: {k.lower(): v for k, v in row.items()},
)
# [{'id': 1, 'name': 'Craig'}]

# Single row
user = template.query_for_object('SELECT * FROM users WHERE id = ?', (1,))

# Single row as dict (raises RuntimeError if 0 or >1 rows)
row = template.query_for_map('SELECT COUNT(*) AS cnt FROM users')
print(row['cnt'])  # 1

# Bulk insert
template.batch_update(
    'INSERT INTO users (name) VALUES (?)',
    [('Alice',), ('Bob',)],
)

# Transaction
def transfer(tx):
    tx.update('UPDATE accounts SET balance = balance - ? WHERE id = ?', (100, 1))
    tx.update('UPDATE accounts SET balance = balance + ? WHERE id = ?', (100, 2))

template.execute_in_transaction(transfer)
```

> Column names are returned in the case produced by the driver. SQLite returns
> uppercase (`ID`, `NAME`). Use a `row_mapper` to normalise to lowercase.

## NamedParameterPydbcTemplate

Use `:param` named parameters instead of positional `?`:

```python
from boot_pydbc import NamedParameterPydbcTemplate

named = NamedParameterPydbcTemplate(ds)

named.update(
    'INSERT INTO users (name) VALUES (:name)',
    {'name': 'Craig'},
)

users = named.query_for_list(
    'SELECT * FROM users WHERE name = :name',
    {'name': 'Craig'},
)
```

## CDI Auto-Configuration

Wire a datasource, `PydbcTemplate`, `NamedParameterPydbcTemplate`, and
`SchemaInitializer` with a single function call:

```python
# invoke.py
import os, pydbc_sqlite
os.chdir(os.path.dirname(os.path.abspath(__file__)))

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

### Configuration keys

| Key | Default | Description |
|---|---|---|
| `boot.datasource.url` | — | pydbc URL (required to activate) |
| `boot.datasource.username` | — | Username (optional) |
| `boot.datasource.password` | — | Password (optional) |
| `boot.datasource.pool.enabled` | `false` | Use `PooledDataSource` |
| `boot.datasource.pool.max` | — | Pool maximum size |
| `boot.datasource.initialize` | `true` | Run schema/data SQL files at startup |
| `boot.datasource.schema` | `config/schema.sql` | DDL file path |
| `boot.datasource.data` | `config/data.sql` | Seed data file path |

### Beans registered

| Bean name | Type | Description |
|---|---|---|
| `data_source` | `ConfiguredDataSource` | pydbc `DataSource` or `PooledDataSource` |
| `pydbc_template` | `PydbcTemplate` | SQL template over `data_source` |
| `named_parameter_pydbc_template` | `NamedParameterPydbcTemplate` | Named parameter wrapper |
| `schema_initializer` | `SchemaInitializer` | Runs `schema.sql` + `data.sql` at startup |

```python
class NoteRepository:
    def __init__(self):
        self.pydbc_template = None  # CDI-autowired
```

## Flyway Migrations

For versioned schema migrations, add `boot-flyway`:

```bash
uv add alt-python-boot-flyway
```

```python
from boot_pydbc import pydbc_auto_configuration
from boot_flyway import flyway_starter

Boot.boot({
    'contexts': [
        Context(pydbc_auto_configuration() + flyway_starter()),
        Context([Singleton(NoteRepository), Singleton(Application)]),
    ]
})
```

```json
{
  "boot": {
    "datasource": { "url": "pydbc:sqlite::memory:", "pool": { "enabled": true, "max": 2 } },
    "flyway": { "locations": "db/migration" }
  }
}
```

Migration files follow Flyway naming convention:

```
db/migration/
  V1__create_notes_table.sql
  V2__add_priority_column.sql
  V3__seed_notes.sql
```

CDI initialises `ManagedFlyway` before any other bean that `depends_on` it.
`migrate()` completes synchronously inside `init()` — no `ready()` call is
needed (see [ADR-013](decisions/ADR-013-managed-flyway-synchronous-init.md)).

### Flyway configuration keys

| Key | Default | Description |
|---|---|---|
| `boot.flyway.enabled` | `true` | Set to `false` to skip migrations |
| `boot.flyway.locations` | `db/migration` | Comma-separated migration paths |
| `boot.flyway.table` | `flyway_schema_history` | History table name |
| `boot.flyway.validate-on-migrate` | `true` | Validate checksums before migrating |
| `boot.flyway.out-of-order` | `false` | Allow out-of-order migrations |

## Secondary Datasources

Use `DataSourceBuilder` to register additional datasources with custom bean
names:

```python
from boot_pydbc import pydbc_auto_configuration, DataSourceBuilder

primary = pydbc_auto_configuration()  # boot.datasource.*

reporting = (
    DataSourceBuilder.create()
    .prefix('myapp.reporting')
    .bean_names({
        'data_source': 'reporting_ds',
        'pydbc_template': 'reporting_template',
        'named_parameter_pydbc_template': 'reporting_named_template',
        'schema_initializer': 'reporting_schema_init',
    })
    .build()
)
```

```json
{
  "myapp": {
    "reporting": {
      "url": "pydbc:sqlite:reporting.db"
    }
  }
}
```

```python
class ReportRepository:
    def __init__(self):
        self.reporting_template = None  # CDI-autowired by name
```

## SQLite In-Memory Databases

Always use `PooledDataSource` with `max >= 1` for in-memory SQLite. Without a
pool, `PydbcTemplate` closes the DBAPI connection after each call, which
destroys the in-memory database:

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

Use `max: 2` when `ManagedFlyway` and `PydbcTemplate` run concurrently (Flyway
needs its own connection for the history table).
