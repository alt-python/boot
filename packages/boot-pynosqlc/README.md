# alt-python-boot-pynosqlc

[![Language](https://img.shields.io/badge/language-Python-3776ab.svg)](https://www.python.org/)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Spring Boot-style CDI auto-configuration for document stores via
[pynosqlc](https://github.com/alt-python/pynosqlc). Provides
`ManagedNosqlClient`, `ConfiguredClientDataSource`, and a CDI auto-configuration
factory that wires a connected NoSQL client into a Boot application from a
single config property.

Part of the [`alt-python/boot`](https://github.com/alt-python/boot) monorepo.

## Quick Start

```bash
# pynosqlc packages are not on PyPI — use path sources (see Installation)
uv add alt-python-boot-pynosqlc
```

```python
# invoke.py
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import pynosqlc.memory  # registers the memory driver
from boot import Boot
from cdi import Context, Singleton
from boot_pynosqlc import pynosqlc_auto_configuration

from services import NoteRepository, Application

Boot.boot({
    'contexts': [
        Context(pynosqlc_auto_configuration()),
        Context([Singleton(NoteRepository), Singleton(Application)]),
    ]
})
```

```json
// config/application.json
{
  "boot": {
    "nosql": {
      "url": "pynosqlc:memory:"
    }
  }
}
```

Boot reads `config/application.json`, connects to the NoSQL backend, and injects
a ready `ManagedNosqlClient` into the application.

## What's Included

| Class / Function | Description |
|---|---|
| `ConfiguredClientDataSource` | CDI bean that reads `boot.nosql.*` config and creates a `ClientDataSource` |
| `ManagedNosqlClient` | CDI bean wrapping the NoSQL client; provides `get_collection()` |
| `NoSqlClientBuilder` | Fluent builder for secondary NoSQL clients |
| `pynosqlc_auto_configuration()` | Returns 2 CDI Singletons ready for `Context()` |
| `pynosqlc_starter()` | Alias for `pynosqlc_auto_configuration()` |
| `pynosqlc_boot()` | One-call `Boot.boot()` entry point |
| `DEFAULT_NOSQL_PREFIX` | `'boot.nosql'` |

## Configuration

All properties are under `boot.nosql` by default (override with a custom prefix).

| Property | Type | Default | Description |
|---|---|---|---|
| `boot.nosql.url` | string | — | pynosqlc URL, e.g. `pynosqlc:memory:` |
| `boot.nosql.username` | string | — | Username (optional) |
| `boot.nosql.password` | string | — | Password (optional) |

If `boot.nosql.url` is absent, the `ConfiguredClientDataSource` bean is still
registered but its `_delegate` is `None`. Calling `get_collection()` will raise
`RuntimeError('NoSQL client not ready')`. This lets you deploy with an optional
NoSQL client without breaking CDI wiring.

## Installation

`alt-python-pynosqlc-core` and `alt-python-pynosqlc-memory` are not on PyPI.
Add them as editable path sources pointing to the local `pynosqlc` repository in
both your package's `pyproject.toml` and the workspace root `pyproject.toml`:

```toml
# pyproject.toml (package level)
[tool.uv.sources]
alt-python-pynosqlc-core   = { path = "/path/to/pynosqlc/packages/core",   editable = true }
alt-python-pynosqlc-memory = { path = "/path/to/pynosqlc/packages/memory", editable = true }
```

```toml
# pyproject.toml (workspace root)
[tool.uv.sources]
alt-python-pynosqlc-core   = { path = "/path/to/pynosqlc/packages/core",   editable = true }
alt-python-pynosqlc-memory = { path = "/path/to/pynosqlc/packages/memory", editable = true }
```

Both levels must use `editable = true`. The pynosqlc-memory package declares
pynosqlc-core as an editable workspace dependency; a mixed editable/non-editable
reference from boot-pynosqlc causes uv to raise a "conflicting URLs" error.

## Working with Collections

`ManagedNosqlClient.get_collection(name)` is synchronous. All collection
operations are async — use `asyncio.run()` to bridge from synchronous CDI
lifecycle methods:

```python
import asyncio

class NoteRepository:
    def __init__(self):
        self.nosql_client = None  # CDI-autowired

    async def find_all(self):
        col = self.nosql_client.get_collection('notes')  # sync
        cursor = await col.find({'type': 'and', 'conditions': []})
        return cursor.get_documents()  # synchronous — do NOT await

    async def store(self, key, note):
        col = self.nosql_client.get_collection('notes')
        await col.store(key, note)


class Application:
    def __init__(self):
        self.note_repository = None  # CDI-autowired

    def run(self):
        # CDI calls run() synchronously — bridge to async here
        asyncio.run(self._run_async())

    async def _run_async(self):
        await self.note_repository.store('k1', {'title': 'First', 'done': False})
        notes = await self.note_repository.find_all()
        for note in notes:
            print(note['title'])
```

### Collection API

| Method | Signature | Description |
|---|---|---|
| `store` | `async (key, doc) → None` | Insert or replace a document by key |
| `get` | `async (key) → dict \| None` | Retrieve a document; `None` if absent |
| `insert` | `async (doc) → str` | Insert and return an auto-assigned ID |
| `update` | `async (key, patch) → None` | Merge patch into an existing document |
| `delete` | `async (key) → None` | Remove a document |
| `find` | `async (filter) → Cursor` | Query with a filter; returns a `Cursor` |

`Cursor.get_documents()` is **synchronous** — it returns a plain list and must
not be awaited:

```python
cursor = await col.find(filter)
docs = cursor.get_documents()  # not: await cursor.get_documents()
```

## Secondary NoSQL Clients

`NoSqlClientBuilder` creates a second set of CDI beans with a custom config
prefix and custom bean names:

```python
from boot_pynosqlc import NoSqlClientBuilder, pynosqlc_auto_configuration
from cdi import Context

primary = pynosqlc_auto_configuration()  # boot.nosql.url

secondary = (
    NoSqlClientBuilder.create()
    .prefix('myapp.reporting')
    .bean_names({
        'nosql_client_data_source': 'reporting_ds',
        'nosql_client': 'reporting_client',
    })
    .build()
)

ctx = Context([*primary, *secondary, ...])
```

Config for the secondary client lives under `myapp.reporting.*`:

```json
{
  "myapp": {
    "reporting": {
      "url": "pynosqlc:memory:"
    }
  }
}
```

## Using with Boot

### `pynosqlc_auto_configuration()`

Returns a flat list of 2 `Singleton` beans. Concatenate with your application
beans and pass to `Context()`:

```python
from boot import Boot
from cdi import Context, Singleton
from boot_pynosqlc import pynosqlc_auto_configuration

Boot.boot({
    'contexts': [
        Context(pynosqlc_auto_configuration()),
        Context([Singleton(MyService), Singleton(MyApp)]),
    ]
})
```

### `pynosqlc_boot()`

One-call entry point for applications that need only a single NoSQL client:

```python
from boot_pynosqlc import pynosqlc_boot
from cdi import Context, Singleton

pynosqlc_boot({
    'contexts': [Context([Singleton(MyService), Singleton(MyApp)])],
})
```

## CDI Lifecycle Notes

`ManagedNosqlClient` uses synchronous CDI lifecycle methods (`init()`,
`destroy()`) with `asyncio.run()` as a bridge to the async pynosqlc client:

- `init()` calls `asyncio.run(self._connect())` to establish the client connection.
- `destroy()` calls `asyncio.run(self._client.close())` for clean shutdown.

CDI's SIGINT handler calls `destroy()` synchronously. Do not override `destroy()`
as `async def` — the coroutine will never be awaited and Python will emit
`RuntimeWarning: coroutine was never awaited`.

## Running Tests

```bash
uv run pytest packages/boot-pynosqlc -v
```

## License

MIT
