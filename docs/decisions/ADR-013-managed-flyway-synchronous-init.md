# ADR-013: ManagedFlyway Uses Synchronous init() — No ready() Method Needed

- **Status:** Accepted
- **Date:** 2026-03-29
- **Deciders:** Agent

## Context

The JavaScript `ManagedFlyway` bean (in `@alt-javascript/boot-flyway`) calls
`this._migrate()` inside `init()`, which is an `async` function. The JavaScript
CDI runtime calls `init()` but does not `await` its return value — the migration
promise runs concurrently with the rest of the context lifecycle. As a result,
the JS `ManagedFlyway` exposes a `ready()` method that callers must `await`
after `context.start()` to ensure migrations have completed before querying:

```javascript
await context.start();
await managedFlyway.ready(); // wait for migrations to finish
const rows = await template.queryForList('SELECT * FROM users');
```

The Python CDI runtime (per ADR-012) calls `init()` synchronously as a regular
function call — it never awaits a return value. This means:

1. `init()` can call `flyway.migrate()` directly (synchronous in Python).
2. `migrate()` completes before `init()` returns.
3. `init()` returns before any downstream bean's `init()` is called.
4. By the time `ApplicationContext.start()` returns, all migrations are complete.

## Decision

`ManagedFlyway.init()` calls `self._flyway.migrate()` synchronously with no
async wrapper. No `ready()` method is implemented or needed.

```python
def init(self):
    config = self._application_context.get('config')
    # ... build Flyway instance from config ...
    self._flyway.migrate()
    # migrations complete — init() returns, CDI moves to next bean
```

Downstream beans — `NoteRepository`, `TagRepository`, etc. — can query the
database immediately in their own `init()` methods without any explicit
synchronisation point. CDI's `depends_on` ordering guarantees that
`ManagedFlyway` initialises before any bean that declares it as a dependency,
and schema migration runs as part of that guarantee.

## Consequences

**Positive:**
- Simpler API — no `ready()` call required after `Boot.boot()` or `ctx.start()`.
- Consistent with CDI's synchronous lifecycle contract (ADR-012).
- Downstream beans can query the schema in their own `init()` without any
  explicit coordination.
- The `managed_flyway.get_flyway()` accessor still provides access to the
  underlying `Flyway` instance for `info()`, `validate()`, `repair()`, and
  `clean()` after startup.

**Negative:**
- Migration time adds directly to application startup latency, unlike the JS
  port where migration happens concurrently. For large schemas this is
  predictable but not parallelisable.
- The JavaScript CDI `ready()` pattern is not available as an escape hatch if a
  future Python CDI version adds async dispatch.

**Risks:**
- If a future Python CDI version calls lifecycle methods with `asyncio.run()` or
  `await`, the synchronous `migrate()` call inside `init()` remains valid and
  unchanged. No migration path is needed.
