# ADR-011: CDI beans access config via ctx.get('config')

- **Status:** Accepted
- **Date:** 2026-03-28
- **Deciders:** Agent

## Context

CDI beans that need to read application configuration at startup implement
`set_application_context(ctx)` to receive the `ApplicationContext`. They then
call configuration accessors in `init()`.

The intuitive access pattern — `self._application_context.config` — does not
work because `ApplicationContext` does not expose a `.config` public property.
This was confirmed when `ctx.config` raised `AttributeError` during the initial
implementation of `ConfiguredDataSource.init()` in M005/S01.

## Decision

CDI beans must access the config bean via `ctx.get('config')`:

```python
def init(self):
    config = self._application_context.get('config')
    if config.has('boot.datasource.url'):
        url = config.get('boot.datasource.url')
```

The `config` bean is auto-registered under the key `'config'` during
`ApplicationContext.parse_contexts()`. It is always available after context
start.

## Consequences

**Positive:**
- Works reliably — `ctx.get('config')` is the documented CDI bean retrieval API.
- Consistent with how application code retrieves any other CDI-managed bean.

**Negative:**
- Not discoverable from the `ApplicationContext` class signature alone — a
  developer relying on IDE completion will not see `.config` as an option.

**Risks:**
- Future `ApplicationContext` versions may add a `.config` convenience property.
  If they do, existing `ctx.get('config')` calls remain valid.
