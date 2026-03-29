# example-5-4-persistence-flyway-multidb

Step 5.4 — Multi-datasource Flyway migration example using alt-python/boot.

Demonstrates two independent pydbc datasources, each managed by its own
`ManagedFlyway` CDI bean with separate migration locations and config prefixes,
wired into a single CDI context.

## What it demonstrates

- `DataSourceBuilder` creating a secondary datasource with custom bean names
- Two `flyway_starter()` calls with different `prefix=` and `datasource_bean=`
  values coexisting in one context
- Renaming the secondary `managed_flyway` Singleton to `managed_flyway_tags` to
  avoid CDI name collision
- `NoteRepository` autowired to `pydbc_template` (primary datasource)
- `TagRepository` autowired to `tags_pydbc_template` (secondary datasource)
- Migration history printed for both databases at runtime

## Run locally

```bash
cd packages/example-5-4-persistence-flyway-multidb
uv run python invoke.py
```

## Run tests

```bash
uv run pytest packages/example-5-4-persistence-flyway-multidb -v
```

## Key files

| File | Description |
|---|---|
| `invoke.py` | Entry point — wires primary + secondary datasources and both Flyway runners |
| `services.py` | `NoteRepository`, `TagRepository`, `Application` |
| `config/application.json` | Two datasource configs and two Flyway locations |
| `db/notes-migration/` | DDL and seed data for the `notes` table |
| `db/tags-migration/` | DDL and seed data for `tags` and `note_tags` tables |

## How it works

The primary datasource and Flyway runner use default config keys:

```json
"boot": {
  "datasource": { "url": "pydbc:sqlite::memory:", "pool": { "max": 2 } },
  "flyway": { "locations": "db/notes-migration" }
}
```

The secondary datasource and Flyway runner use custom config keys with a `-tags`
suffix:

```json
"boot": {
  "datasource-tags": { "url": "pydbc:sqlite::memory:", "pool": { "max": 2 } },
  "flyway-tags": { "locations": "db/tags-migration" }
}
```

`invoke.py` wires them together:

```python
# Primary (notes)
notes_beans = pydbc_auto_configuration() + flyway_starter()

# Secondary (tags) — DataSourceBuilder with custom bean names
tags_ds = (
    DataSourceBuilder.create()
    .prefix('boot.datasource-tags')
    .bean_names({'data_source': 'tags_data_source', ...})
    .without_schema_initializer()
    .build()
)

# Second Flyway runner — renamed to avoid colliding with managed_flyway
tags_flyway = flyway_starter(
    prefix='boot.flyway-tags',
    datasource_bean='tags_data_source',
)
# Re-create with name='managed_flyway_tags'
tags_flyway = [
    Singleton({'reference': comp.reference, 'name': 'managed_flyway_tags', ...})
    if comp.name == 'managed_flyway' else comp
    for comp in tags_flyway
]
```

`TagRepository` autowires to `tags_pydbc_template` by name — the same CDI
null-property naming convention used across all alt-python/boot packages.

Part of the [`alt-python/boot`](https://github.com/alt-python/boot) monorepo.
