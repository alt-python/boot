# Lifecycle

## Component Lifecycle Sequence

`ApplicationContext.start()` runs the full lifecycle in this order:

```
parse_contexts()
  → instantiate all Singleton beans (constructors called)
  → inject None-property autowiring + Property placeholders
  → inject set_application_context(ctx) callbacks
  → call init() on each bean in depends_on order
  → register destroy() handlers for SIGINT
  → call run() on the Application bean
```

On shutdown (SIGINT or explicit `ctx.stop()`):

```
call destroy() on each bean in reverse init order
```

## Lifecycle Methods

All are optional — implement only the ones you need.

| Method | When called | Purpose |
|---|---|---|
| `__init__()` | Instantiation | Declare wirable attributes (`= None` or `'${path}'`) |
| `set_application_context(ctx)` | After wiring, before `init()` | Receive the `ApplicationContext` reference |
| `init()` | After all wiring | Post-injection startup logic, open connections |
| `run()` | After all `init()` | Application entry point |
| `destroy()` | On shutdown | Cleanup: close connections, flush state |

```python
class NoteRepository:
    def __init__(self):
        self.pydbc_template = None       # CDI-autowired
        self._application_context = None

    def set_application_context(self, ctx):
        self._application_context = ctx

    def init(self):
        config = self._application_context.get('config')
        self._table = config.get('notes.table', 'notes')

    def find_all(self):
        return self.pydbc_template.query_for_list(f'SELECT * FROM {self._table}')

    def destroy(self):
        pass  # pydbc_template closes its own connections
```

> `init()` and `destroy()` **must be regular `def`**, not `async def`. If you
> need to call async code from a lifecycle method, bridge with `asyncio.run()`.
> See [ADR-012](decisions/ADR-012-cdi-lifecycle-methods-synchronous.md).

## DependsOn Ordering

Use `depends_on` to declare explicit initialisation dependencies. CDI
topologically sorts `init()` calls so dependencies initialise first:

```python
class ManagedFlyway:
    depends_on = ['data_source']

    def init(self):
        # data_source.init() has finished — schema migrations safe to run
        self._flyway.migrate()


class NoteRepository:
    depends_on = ['managed_flyway']

    def init(self):
        # migrations complete — safe to query the schema
        rows = self.pydbc_template.query_for_list('SELECT COUNT(*) FROM notes')
```

Circular `depends_on` chains raise `ValueError` at startup with the cycle
listed.

## run() — The Application Entry Point

CDI calls `run()` on any bean that defines it after all `init()` calls
complete. Conventionally, one `Application` bean owns `run()`:

```python
class Application:
    def __init__(self):
        self.note_service = None  # CDI-autowired

    def run(self):
        notes = self.note_service.find_all()
        for note in notes:
            print(note['title'])
```

To suppress `run()` — for example in serverless adapters — pass `'run': False`
to `Boot.boot()`:

```python
app_ctx = Boot.boot({
    'contexts': [Context([...])],
    'run': False,
})
# CDI is wired, no run() called
adapter = app_ctx.get('lambda_adapter')
```

## destroy() and Shutdown

CDI registers a SIGINT handler during `start()`. When the process receives
SIGINT (Ctrl+C), CDI calls `destroy()` on each bean in reverse initialisation
order:

```python
class ManagedNosqlClient:
    def destroy(self):
        if self._client is not None:
            import asyncio
            asyncio.run(self._client.close())
            self._client = None
```

`destroy()` is called synchronously. If you need to perform async cleanup, use
`asyncio.run()` as shown above — no event loop is running when the SIGINT
handler fires.

## Boot.test() — Test Lifecycle

`Boot.test()` runs the full CDI lifecycle with the startup banner suppressed
and log output captured in memory. Use it in test functions to avoid banner
noise and cross-test log leakage:

```python
from boot import Boot
from cdi import Context, Singleton

def test_note_repository():
    ctx = Boot.test({'contexts': [Context([Singleton(NoteRepository)])]})
    repo = ctx.get('note_repository')
    assert repo is not None
```

`Boot.test()` wraps the caller's config in a `PropertySourceChain` with
`boot.banner-mode: off` prepended and uses `CachingLoggerFactory` so log output
is captured in-memory rather than printed to stdout.
