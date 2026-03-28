# ADR-012: CDI lifecycle methods must be synchronous

- **Status:** Accepted
- **Date:** 2026-03-28
- **Deciders:** Agent

## Context

CDI beans implement `init()` and `destroy()` as lifecycle hooks. The
`ApplicationContext` calls `init()` after wiring all beans, and `destroy()` when
the application receives SIGINT. Both calls are made synchronously — the CDI
runtime does not `await` them.

Several persistence beans (e.g. `ManagedNosqlClient`) depend on async backends
whose connect and close operations are coroutines. The question is whether
lifecycle methods can be declared `async def`.

The answer is no: if `init()` or `destroy()` are `async def`, the CDI runtime
calls them as regular functions. Python returns a coroutine object rather than
executing the body. For `destroy()` this produces
`RuntimeWarning: coroutine was never awaited` and the teardown logic is silently
skipped.

## Decision

CDI lifecycle methods (`init()`, `destroy()`) must always be declared as regular
`def`. When the method needs to call async code, use `asyncio.run()` as a
synchronous bridge:

```python
def init(self):
    asyncio.run(self._connect())

def destroy(self):
    if self._client is not None:
        asyncio.run(self._client.close())
        self._client = None
```

`asyncio.run()` is safe here because:
- The CDI SIGINT handler fires outside any running event loop.
- `init()` is called during `ApplicationContext.start()`, which is synchronous.
- No competing event loop is active at either call site.

## Consequences

**Positive:**
- Lifecycle hooks execute reliably under CDI's synchronous dispatch model.
- `asyncio.run()` is idiomatic Python for bridging sync → async at a top-level
  boundary.

**Negative:**
- Verbose compared to `await self._connect()` inside an `async def`.
- Cannot be used if an event loop is already running at the call site (e.g.
  inside a FastAPI route). Boot applications call `init()` before any server
  thread starts, so this is not an issue in practice.

**Risks:**
- If CDI is extended in a future version to support async lifecycle dispatch
  (e.g. `await bean.init()` inside an `async` context), existing sync `init()`
  methods remain valid. The change would be additive.
