# alt-python-flyway

[![Language](https://img.shields.io/badge/language-Python-3776ab.svg)](https://www.python.org/)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Flyway-inspired versioned SQL migration engine for Python. Discovers
`V{version}__{description}.sql` files, tracks applied migrations in a
`flyway_schema_history` table, and provides the full Flyway OSS operation set:
`migrate()`, `info()`, `validate()`, `baseline()`, `repair()`, and `clean()`.

Port of [`@alt-javascript/flyway`](https://github.com/alt-javascript/boot/tree/main/packages/flyway).
Inspired by [Flyway](https://flywaydb.org) (Apache 2.0) by Redgate Software Ltd.

Part of the [`alt-python/boot`](https://github.com/alt-python/boot) monorepo.

## Install

```bash
uv add alt-python-flyway pydbc-sqlite   # or: pip install alt-python-flyway pydbc-sqlite
```

Requires Python 3.12+ and `alt-python-boot-pydbc`.

## Quick Start

```python
import pydbc_sqlite  # registers the SQLite driver
from pydbc_core import PooledDataSource
from flyway import Flyway

ds = PooledDataSource('pydbc:sqlite::memory:', pool={'max': 2})
flyway = Flyway(data_source=ds, locations=['db/migration'])

result = flyway.migrate()
print(result['migrations_executed'])  # 3
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

Apply all pending versioned migrations in version order. Safe to call repeatedly
— a second call applies nothing when all migrations are already applied.

```python
result = flyway.migrate()
# {'migrations_executed': 3, 'applied_migrations': [...]}
```

Each entry in `applied_migrations`: `version`, `description`, `script`,
`execution_time`, `state` (`SUCCESS`).

Raises `FlywayMigrationError` if a migration SQL fails. Raises
`FlywayValidationError` if `validate_on_migrate=True` and a checksum drift is
detected before migration starts.

### `info()`

Return a status report for all known migrations (applied and pending).

```python
for m in flyway.info():
    print(m['version'], m['state'], m['description'])
    # 1  SUCCESS  create notes table
    # 2  PENDING  add priority column
```

Each entry: `version`, `description`, `script`, `checksum`, `state`
(`PENDING`, `SUCCESS`, or `FAILED`), `installed_on`, `execution_time`.

### `validate()`

Verify that applied migration checksums match the files on disk. Raises
`FlywayValidationError` if any applied migration's file has been modified since
it was applied. Use in CI before deploying to catch accidental file edits.

```python
flyway.validate()  # raises FlywayValidationError on mismatch
```

### `baseline()`

Mark the current database state as a known baseline. Records a `BASELINE` entry
in the history table so that `migrate()` starts from `baseline_version + 1`.
Raises `FlywayError` if the history table already has entries.

```python
flyway = Flyway(data_source=ds, locations=['db/migration'], baseline_version='3')
flyway.baseline()
# History now contains a BASELINE entry for version '3'
# Next migrate() will only apply V4 and later
```

### `repair()`

Remove failed migration entries from the history table. Safe to call at any
time — does not touch application tables.

```python
result = flyway.repair()
print(result['removed_entries'])  # 1
```

### `clean()`

Drop the schema history table. **Destructive** — does not drop application
tables. Use only in development and test environments.

```python
flyway.clean()
```

## Constructor

```python
Flyway(
    data_source,                            # required — pydbc DataSource
    locations=['db/migration'],             # migration file paths
    table='flyway_schema_history',          # history table name
    baseline_version='1',                   # version for baseline()
    baseline_description='Flyway Baseline', # baseline history entry description
    out_of_order=False,                     # allow out-of-order migrations
    validate_on_migrate=True,               # validate checksums before migrating
    installed_by='flyway',                  # user recorded in history
)
```

| Parameter | Default | Description |
|---|---|---|
| `data_source` | required | pydbc `DataSource` or `PooledDataSource` |
| `locations` | `['db/migration']` | Filesystem paths to scan for migration files |
| `table` | `'flyway_schema_history'` | History table name |
| `baseline_version` | `'1'` | Version string for `baseline()` |
| `baseline_description` | `'Flyway Baseline'` | Description written to baseline entry |
| `out_of_order` | `False` | Allow applying migrations older than the latest applied |
| `validate_on_migrate` | `True` | Check checksums before each `migrate()` call |
| `installed_by` | `'flyway'` | User name written to `installed_by` column |

## Migration File Format

File names must follow the pattern `V{version}__{description}.sql`:

- `V` prefix (case-insensitive)
- Version: dot-separated numeric segments — `1`, `1.1`, `2`, `10` sort as
  `1 < 1.1 < 2 < 10`
- Double underscore (`__`) separates version from description
- Underscores in the description are replaced with spaces in the history table

```sql
-- V1__create_notes_table.sql
CREATE TABLE IF NOT EXISTS notes (
    id       INTEGER PRIMARY KEY,
    title    TEXT    NOT NULL,
    body     TEXT,
    priority INTEGER NOT NULL DEFAULT 0,
    done     INTEGER NOT NULL DEFAULT 0
);

-- V3__seed_notes.sql
INSERT INTO notes (id, title, body) VALUES (1, 'First note', '');
INSERT INTO notes (id, title, body) VALUES (2, 'Second note', '');
```

Each file may contain multiple statements separated by `;`. Line comments
(`-- ...`) are stripped before execution.

## Multiple Locations

```python
flyway = Flyway(
    data_source=ds,
    locations=['db/notes-migration', 'db/tags-migration'],
)
```

Migrations from all locations are merged and sorted by version before applying.
Version numbers must be unique across all locations.

## SQLite In-Memory Databases

Use `PooledDataSource` with `max=2` or higher. The schema history table and
migration executor each need a connection. With an in-memory SQLite database,
closing the last connection destroys the database — the pool keeps it alive
across calls.

```python
from pydbc_core import PooledDataSource

ds = PooledDataSource('pydbc:sqlite::memory:', pool={'max': 2})
```

## Schema History Table

The `flyway_schema_history` table tracks every applied migration:

| Column | Type | Description |
|---|---|---|
| `installed_rank` | INTEGER | Auto-incrementing primary key |
| `version` | TEXT | Migration version string |
| `description` | TEXT | Human-readable description from filename |
| `type` | TEXT | `SQL` or `BASELINE` |
| `script` | TEXT | Migration filename |
| `checksum` | INTEGER | Signed 32-bit CRC32 of the file content |
| `installed_by` | TEXT | User (configurable via `installed_by=`) |
| `installed_on` | TEXT | ISO-8601 timestamp |
| `execution_time` | INTEGER | Execution time in milliseconds |
| `success` | INTEGER | `1` = success, `0` = failed |

## API Reference

### `MigrationVersion`

Parsed version wrapper with segment-aware numeric comparison.

```python
from flyway import MigrationVersion

v = MigrationVersion.parse('1.1')
v.compare_to(MigrationVersion.parse('2'))  # -1 (less than)
v < MigrationVersion.parse('2')            # True
v == MigrationVersion.parse('1.1')         # True
str(v)                                     # '1.1'
```

`MigrationVersion` supports `<` and `==`, which means Python's `sorted()` and
`list.sort()` work correctly on lists of versions.

### `MigrationState`

```python
from flyway import MigrationState

MigrationState.PENDING   # 'PENDING'
MigrationState.SUCCESS   # 'SUCCESS'
MigrationState.FAILED    # 'FAILED'
MigrationState.BASELINE  # 'BASELINE'
```

### `checksum(sql: str) -> int`

Returns a signed 32-bit CRC32 checksum matching Flyway OSS format. Used
internally for drift detection; also available if you need to compute checksums
independently.

```python
from flyway import checksum

print(checksum('SELECT 1'))  # e.g. 1153854338
```

## Error Types

| Exception | Raised when |
|---|---|
| `FlywayError` | Base class; also raised by `baseline()` on non-empty history |
| `FlywayValidationError` | Checksum mismatch in `validate()` or `validate_on_migrate` |
| `FlywayMigrationError` | Migration SQL fails in `migrate()`. Attributes: `.migration`, `.cause` |

```python
from flyway import FlywayError, FlywayValidationError, FlywayMigrationError

try:
    flyway.migrate()
except FlywayMigrationError as e:
    print(e.migration['script'])  # which file failed
    print(e.cause)                # the underlying exception
```

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

## Troubleshooting

**`FlywayError: Flyway requires a data_source`**
Pass `data_source=` explicitly. `Flyway()` with no arguments raises immediately.

**`FlywayValidationError: Migration checksum mismatch`**
A migration file was edited after it was applied. Either restore the original
file or call `repair()` to remove the failed history entry, then re-apply with
the corrected SQL.

**`FlywayError: Cannot baseline a non-empty schema history`**
`baseline()` only works on a fresh (empty) history table. If migrations have
already been applied, use `repair()` to clean up failed entries, or `clean()`
to reset the history table entirely (destructive).

**Migrations not found — `migrations_executed: 0`**
Check that `locations=` points to the directory containing the `.sql` files,
not a parent directory. Check that filenames exactly match
`V{version}__{description}.sql` (capital `V`, double underscore).

**In-memory SQLite: `RuntimeError` or empty results after `migrate()`**
Use `PooledDataSource` with `max=2`. A plain `DataSource` or
`SingleConnectionDataSource` closes the underlying connection after each
`PydbcTemplate` call, which destroys an in-memory database.

## Flyway Attribution

> This project is inspired by [Flyway](https://flywaydb.org) (Apache License 2.0)
> by Redgate Software Ltd. It implements the open-source feature set only.
> Flyway is a registered trademark of Boxfuse GmbH, which is owned by Red Gate
> Software. This project is independent and not affiliated with Boxfuse GmbH,
> Red Gate Software, or the Flyway team.

## License

MIT
