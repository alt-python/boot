# alt-python-flyway

[![Language](https://img.shields.io/badge/language-Python-3776ab.svg)](https://www.python.org/)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Flyway-inspired versioned SQL migration engine for Python. Discovers
`V{version}__{description}.sql` files, tracks applied migrations in a schema
history table, and provides the full Flyway OSS operation set: `migrate()`,
`info()`, `validate()`, `baseline()`, `repair()`, and `clean()`.

Port of [`@alt-javascript/flyway`](https://github.com/alt-javascript/boot/tree/main/packages/flyway).
Inspired by [Flyway](https://flywaydb.org) (Apache 2.0) by Redgate Software Ltd.

Part of the [`alt-python/boot`](https://github.com/alt-python/boot) monorepo.

## Install

```bash
uv add alt-python-flyway pydbc-sqlite   # or: pip install alt-python-flyway pydbc-sqlite
```

Requires Python 3.12+ and `alt-python-boot-pydbc` (for `PydbcTemplate`).

## Quick Start

```python
import pydbc_sqlite  # register the SQLite driver
from pydbc_core import PooledDataSource
from flyway import Flyway

ds = PooledDataSource('pydbc:sqlite::memory:', pool={'max': 2})
flyway = Flyway(data_source=ds, locations=['db/migration'])

result = flyway.migrate()
print(result['migrations_executed'])   # 3
print(result['applied_migrations'])    # [{version, description, state, ...}, ...]
```

Migration files follow Flyway naming convention:

```
db/migration/
  V1__create_notes_table.sql
  V2__add_priority_column.sql
  V3__seed_notes.sql
```

## Operations

### `migrate()`

Apply all pending versioned migrations in version order. Idempotent — running
twice applies nothing on the second call.

```python
result = flyway.migrate()
# {'migrations_executed': 3, 'applied_migrations': [...]}
```

Raises `FlywayMigrationError` if a migration SQL fails. Raises
`FlywayValidationError` if `validate_on_migrate=True` and a checksum drift is
detected before migration.

### `info()`

Return a status report for all migrations (applied + pending).

```python
for m in flyway.info():
    print(m['version'], m['state'], m['description'])
    # 1  SUCCESS  create notes table
    # 2  PENDING  add priority column
```

Each entry: `version`, `description`, `script`, `checksum`, `state`
(`PENDING`, `SUCCESS`, `FAILED`), `installed_on`, `execution_time`.

### `validate()`

Verify that applied migration checksums match the files on disk. Raises
`FlywayValidationError` on mismatch. Useful for CI checks.

```python
flyway.validate()  # raises if any file was modified after being applied
```

### `baseline()`

Mark the current database state as a known baseline. Records a `BASELINE` entry
in the history table so that `migrate()` starts from `baseline_version` + 1.
Raises `FlywayError` if the history table is not empty.

```python
flyway = Flyway(data_source=ds, locations=['db/migration'], baseline_version='3')
flyway.baseline()
```

### `repair()`

Remove failed migration entries from the history table. Safe to call at any
time — does not touch application tables.

```python
result = flyway.repair()
print(result['removed_entries'])  # 1
```

### `clean()`

Drop the schema history table. **Destructive** — intended for development and
test environments only. Does not drop application tables.

```python
flyway.clean()
```

## Constructor Options

```python
Flyway(
    data_source,                       # required — pydbc DataSource
    locations=['db/migration'],        # migration file paths
    table='flyway_schema_history',     # history table name
    baseline_version='1',             # version for baseline()
    baseline_description='Flyway Baseline',
    out_of_order=False,               # allow out-of-order migrations
    validate_on_migrate=True,         # validate checksums before migrating
    installed_by='flyway',            # user recorded in history
)
```

## Migration File Format

```
V{version}__{description}.sql
```

- `V` prefix (case-insensitive)
- Version: numeric, segment-aware — `1`, `1.1`, `2`, `10` sort as `1 < 1.1 < 2 < 10`
- Double underscore separates version from description
- Underscores in description are replaced with spaces in the history table
- Multiple locations are merged and sorted by version

```sql
-- V1__create_notes_table.sql
CREATE TABLE IF NOT EXISTS notes (
    id       INTEGER PRIMARY KEY,
    title    TEXT    NOT NULL,
    body     TEXT,
    priority INTEGER NOT NULL DEFAULT 0,
    done     INTEGER NOT NULL DEFAULT 0
);

-- V2__seed_notes.sql
INSERT INTO notes (id, title, body) VALUES (1, 'First note', '');
INSERT INTO notes (id, title, body) VALUES (2, 'Second note', '');
```

Each `.sql` file may contain multiple statements separated by `;`. Line
comments (`-- ...`) are stripped before execution.

## Multiple Locations

```python
flyway = Flyway(
    data_source=ds,
    locations=['db/notes-migration', 'db/tags-migration'],
)
```

Migrations from all locations are merged and sorted by version before applying.
Version numbers must be globally unique across locations.

## SQLite In-Memory Databases

Use `PooledDataSource` with `max=2` or higher — `SchemaHistoryTable` and
`MigrationExecutor` each need a connection, and in-memory SQLite destroys the
database when the last connection closes.

```python
ds = PooledDataSource('pydbc:sqlite::memory:', pool={'max': 2})
```

## Schema History Table

The `flyway_schema_history` table (configurable via `table=`) tracks every
applied migration:

| Column | Type | Description |
|---|---|---|
| `installed_rank` | INTEGER | Auto-incrementing primary key |
| `version` | TEXT | Migration version string |
| `description` | TEXT | Human-readable description |
| `type` | TEXT | `SQL` or `BASELINE` |
| `script` | TEXT | Filename |
| `checksum` | INTEGER | CRC32-style signed 32-bit checksum |
| `installed_by` | TEXT | User (configurable) |
| `installed_on` | TEXT | ISO-8601 timestamp |
| `execution_time` | INTEGER | Milliseconds |
| `success` | INTEGER | `1` = success, `0` = failed |

## API Reference

### `Flyway`

| Parameter | Default | Description |
|---|---|---|
| `data_source` | required | pydbc `DataSource` or `PooledDataSource` |
| `locations` | `['db/migration']` | Filesystem paths to scan |
| `table` | `'flyway_schema_history'` | History table name |
| `baseline_version` | `'1'` | Version for `baseline()` |
| `baseline_description` | `'Flyway Baseline'` | Description for baseline entry |
| `out_of_order` | `False` | Allow applying migrations older than the latest applied |
| `validate_on_migrate` | `True` | Check checksums before `migrate()` |
| `installed_by` | `'flyway'` | User recorded in history table |

### `MigrationVersion`

```python
from flyway import MigrationVersion

v = MigrationVersion.parse('1.1')
v.compare_to(MigrationVersion.parse('2'))  # -1
str(v)                                      # '1.1'
```

Supports `<`, `==`, `>` operators and `sort()`.

### `checksum(sql: str) -> int`

Returns a signed 32-bit CRC32 checksum. Matches Flyway OSS checksum format for
cross-tool consistency.

### `MigrationState`

```python
from flyway import MigrationState

MigrationState.PENDING   # 'PENDING'
MigrationState.SUCCESS   # 'SUCCESS'
MigrationState.FAILED    # 'FAILED'
MigrationState.BASELINE  # 'BASELINE'
```

## Error Types

| Exception | When raised |
|---|---|
| `FlywayError` | Base class for all Flyway errors |
| `FlywayValidationError` | Checksum mismatch detected by `validate()` or `validate_on_migrate` |
| `FlywayMigrationError` | Migration SQL fails during `migrate()`. Has `.migration` and `.cause` attributes. |

## All Exports

```python
from flyway import (
    Flyway,
    FlywayError,
    FlywayValidationError,
    FlywayMigrationError,
    MigrationState,
    MigrationVersion,
    MigrationLoader,
    MigrationExecutor,
    SchemaHistoryTable,
    checksum,
)
```

## Running Tests

```bash
uv run pytest packages/flyway -v
```

## Flyway Attribution

> This project is inspired by [Flyway](https://flywaydb.org) (Apache License 2.0)
> by Redgate Software Ltd. It implements the open-source feature set only.
> Flyway is a registered trademark of Boxfuse GmbH, which is owned by Red Gate
> Software. This project is independent and not affiliated with Boxfuse GmbH,
> Red Gate Software, or the Flyway team.

## License

MIT
