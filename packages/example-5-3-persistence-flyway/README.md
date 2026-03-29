# example-5-3-persistence-flyway

Step 5.3 — Single-datasource Flyway migration example using alt-python/boot.

Demonstrates `ManagedFlyway` running versioned SQL migrations at startup, then
querying and mutating notes via a `NoteRepository` CDI service.

## What it demonstrates

- `pydbc_auto_configuration() + flyway_starter()` wires the datasource, SQL
  template, and Flyway runner in one call
- Three versioned migrations applied in order: create table → add column → seed data
- `managed_flyway.get_flyway().info()` to inspect migration history at runtime
- `NoteRepository` using `PydbcTemplate` for CRUD operations after migration
- Config-driven datasource and migration paths via `config/application.json`

## Run locally

```bash
cd packages/example-5-3-persistence-flyway
uv run python invoke.py
```

Expected output:

```
── Migration history ──────────────────────────────
  V1 create notes table                       [SUCCESS]
  V2 add priority column                      [SUCCESS]
  V3 seed notes                               [SUCCESS]

── Notes (seeded by V3 migration) ────────────────
  [2] P0 Second note
  [1] P0 First note

── After update ───────────────────────────────────
  [1] ✓ First note
  [2] ○ Second note
  [3] ○ Runtime note

── After remove ───────────────────────────────────
  [1] ✓ First note
  [2] ○ Second note
```

## Run tests

```bash
uv run pytest packages/example-5-3-persistence-flyway -v
```

## Key files

| File | Description |
|---|---|
| `invoke.py` | Entry point — boots CDI and runs `Application.run()` |
| `services.py` | `NoteRepository` (CRUD via `PydbcTemplate`) and `Application` |
| `config/application.json` | Datasource URL, Flyway locations, log level |
| `db/migration/V1__create_notes_table.sql` | DDL — creates `notes` table |
| `db/migration/V2__add_priority_column.sql` | DDL — adds `priority` column |
| `db/migration/V3__seed_notes.sql` | DML — inserts two seed rows |

## How it works

```python
Boot.boot({
    'contexts': [
        Context(pydbc_auto_configuration() + flyway_starter()),
        Context([Singleton(NoteRepository), Singleton(Application)]),
    ]
})
```

CDI initialises the datasource and `ManagedFlyway` before any other bean.
`ManagedFlyway.init()` calls `flyway.migrate()` synchronously — by the time
`NoteRepository.init()` runs, the schema exists and the seed rows are present.

`Application.run()` calls `managed_flyway.get_flyway().info()` to print the
migration history, then exercises `NoteRepository` with `find_all()`,
`save()`, `mark_done()`, and `remove()`.

Part of the [`alt-python/boot`](https://github.com/alt-python/boot) monorepo.
