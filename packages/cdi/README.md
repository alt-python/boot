# alt-python-cdi

[![Language](https://img.shields.io/badge/language-Python-3776ab.svg)](https://www.python.org/)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

IoC container and dependency injection for the alt-python framework. Provides
`ApplicationContext`, `Singleton`, `Prototype`, `Context`, `Component`,
`Property`, and `Scopes` — a synchronous, profile-aware CDI container with
name-based autowiring and lifecycle management.

The design is a direct port of the [Spring Framework](https://spring.io/)'s
`ApplicationContext` and component model to idiomatic Python.

Part of the [`alt-python/boot`](https://github.com/alt-python/boot) monorepo.

## Install

```bash
uv add alt-python-cdi   # or: pip install alt-python-cdi
```

Requires Python 3.12+, `alt-python-config`, and `alt-python-logger`.

## Quick Start

```python
from config import EphemeralConfig
from cdi import ApplicationContext, Context, Singleton


class UserRepository:
    def __init__(self):
        self._users = []

    def add(self, user):
        self._users.append(user)

    def find_all(self):
        return list(self._users)


class UserService:
    def __init__(self):
        self.user_repository = None  # CDI-autowired by name

    def create_user(self, name):
        self.user_repository.add({"name": name})


cfg = EphemeralConfig({"logging": {"level": {"/": "warn"}}})
ctx = ApplicationContext({
    "config": cfg,
    "contexts": [Context([Singleton(UserRepository), Singleton(UserService)])],
})
ctx.start()

ctx.get('user_service').create_user("Alice")
print(ctx.get('user_repository').find_all())  # [{'name': 'Alice'}]
```

## Autowiring

CDI wires beans by **name matching**. Set a constructor attribute to `None`
and name it after the target bean (in `snake_case`) — CDI sets it to the live
instance after all singletons are instantiated.

```python
class OrderService:
    def __init__(self):
        self.order_repository = None  # wired to the OrderRepository bean
        self.email_service    = None  # wired to the EmailService bean
```

`ApplicationContext` converts class names to `snake_case` for the registry key
(`OrderService` → `order_service`). CamelCase names passed to `Singleton({"name":
"myBean"})` are also converted (`myBean` → `my_bean`). Use `ctx.get('order_service')`
to retrieve beans.

## Lifecycle

The CDI lifecycle mirrors Spring's component lifecycle:

| Phase | Spring | CDI Python |
|---|---|---|
| Wire + init | `refresh()` | `ctx.start()` |
| Post-construct | `@PostConstruct` | `bean.init()` |
| Pre-destroy | `@PreDestroy` | `bean.destroy()` |
| Context wiring callback | `ApplicationContextAware` | `bean.set_application_context(ctx)` |

After `ctx.start()`, CDI:

1. Instantiates all `Singleton` components.
2. Injects the `ApplicationContext` by calling `set_application_context(ctx)` on
   any bean that defines it.
3. Autowires `None`-valued constructor attributes by name.
4. Resolves `Property` placeholders (e.g. `'${app.port:8080}'`) from config.
5. Calls `init()` on each bean that defines it, in dependency order.

On shutdown (SIGINT / explicit stop), CDI calls `destroy()` on each bean in
reverse order.

> `init()` and `destroy()` **must be regular `def` methods**, not `async def`.
> If you need to call async code, bridge with `asyncio.run()`. See
> [ADR-012](../../docs/decisions/ADR-012-cdi-lifecycle-methods-synchronous.md).

## Component Definitions

### `Singleton(reference_or_dict)`

Registers a class as a CDI-managed singleton. The same instance is returned on
every `ctx.get()` call.

```python
# Class form — name derived from class name (snake_case)
Singleton(OrderService)

# Dict form — explicit name, conditions, scope
Singleton({
    "reference": OrderService,
    "name":      "orderService",
    "scope":     Scopes.SINGLETON,
})
```

Dict form keys:

| Key | Type | Description |
|---|---|---|
| `reference` | class | The class to instantiate |
| `name` | `str` | CDI bean name (camelCase converted to snake_case) |
| `scope` | `str` | `Scopes.SINGLETON` (default) or `Scopes.PROTOTYPE` |
| `primary` | `bool` | Wins disambiguation when multiple beans share a name |

### `Prototype(reference_or_dict)`

Like `Singleton` but creates a new instance on every `ctx.get()` call. Useful
for stateful per-request objects.

### `Context([components])`

Groups component definitions. An `ApplicationContext` accepts one or more
`Context` objects.

```python
from cdi import Context, Singleton

repo_context = Context([Singleton(UserRepository)])
svc_context  = Context([Singleton(UserService)])

app_ctx = ApplicationContext({
    "config": cfg,
    "contexts": [repo_context, svc_context],
})
```

### `Property`

Declares a config-value property. Use placeholder syntax `'${path:default}'` as
the default value in `__init__`:

```python
class ServerConfig:
    def __init__(self):
        self.port    = '${server.port:8080}'
        self.host    = '${server.host:localhost}'
        self.timeout = '${server.timeout:30}'
```

CDI resolves placeholders against the wired config bean before calling `init()`.

## Profiles

Restrict a bean to specific active profiles using the `profiles` class attribute:

```python
class DevEmailService:
    profiles = ['dev']

class ProdEmailService:
    profiles = ['prod']
```

When `PY_ACTIVE_PROFILES=dev`, only `DevEmailService` is instantiated. Beans
without a `profiles` attribute are always active.

Use `primary = True` on the profile-conditional bean to ensure it wins when two
beans would resolve to the same attribute name:

```python
class DevEmailService:
    profiles = ['dev']
    primary  = True
```

## Scopes

```python
from cdi import Scopes

Scopes.SINGLETON   # "singleton"  — one instance per context
Scopes.PROTOTYPE   # "prototype"  — new instance per ctx.get() call
```

## Dependency Ordering

Set `depends_on` as a class attribute to declare explicit ordering:

```python
class SchemaInitializer:
    depends_on = ['data_source']

    def init(self):
        # data_source is guaranteed to be initialised before this runs
        ...
```

CDI resolves `depends_on` chains before calling `init()`, even if the dependency
is not directly wired via a `None` attribute.

## ApplicationContext API

### `ApplicationContext(options)`

```python
ctx = ApplicationContext({
    "config":   cfg,      # config-like object (required)
    "contexts": [context] # list of Context objects (required)
})
```

> Use the dict form. The single-`Context` form (`ApplicationContext(Context([...]))`)
> creates an empty `EphemeralConfig` internally — it does not load any config
> files from disk. See the monorepo README for the canonical invocation pattern.

### `ctx.start()`

Wires and initialises all components. Equivalent to Spring's
`ApplicationContext.refresh()` + `start()`.

### `ctx.get(name)`

Retrieve a bean by name (snake_case). Raises `KeyError` if not found.

```python
svc = ctx.get('order_service')
```

### `ctx.stop()`

Calls `destroy()` on all beans in reverse init order.

## Using with Boot

The canonical entry point is `Boot.boot()`, which handles config loading, banner
printing, and CDI wiring in one call:

```python
from boot import Boot
from cdi import Context, Singleton

Boot.boot({
    'contexts': [Context([Singleton(MyService), Singleton(Application)])]
})
```

`Boot.boot()` auto-registers `config`, `logger_factory`, and
`logger_category_cache` as CDI beans before `ctx.start()` is called — any bean
with `self.config = None` receives the live config instance without extra wiring.

For tests, use `Boot.test()`:

```python
from boot import Boot
from cdi import Context, Singleton

ctx = Boot.test({'contexts': [Context([Singleton(MyService)])]})
svc = ctx.get('my_service')
```

## All Exports

```python
from cdi import (
    ApplicationContext,
    Component,
    Context,
    Property,
    Prototype,
    Scopes,
    Singleton,
)
```

## Spring Attribution

| Spring concept | alt-python-cdi equivalent |
|---|---|
| `@Component` / `@Service` / `@Repository` | `Singleton` |
| `@Autowired` (field injection) | `self.dependency = None` naming convention |
| `@Value("${key:default}")` | `self.port = '${server.port:8080}'` |
| `@PostConstruct` | `def init(self)` |
| `@PreDestroy` | `def destroy(self)` |
| `ApplicationContextAware` | `def set_application_context(self, ctx)` |
| `ApplicationContext.refresh()` | `ctx.start()` |
| `ApplicationContext.getBean()` | `ctx.get('bean_name')` |
| `@Profile` | `profiles = ['dev']` class attribute |
| `@Primary` | `primary = True` class attribute |
| `@DependsOn` | `depends_on = ['other_bean']` class attribute |
| Prototype scope | `Prototype(MyClass)` |

## License

MIT
