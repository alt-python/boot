# Dependency Injection

## Contexts and Components

`ApplicationContext` manages a collection of component definitions. Components
are defined using `Singleton` or `Prototype` helper classes and grouped into
`Context` objects:

```python
from cdi import Context, Singleton, Prototype

context = Context([
    Singleton(MyService),         # one shared instance
    Prototype(RequestHandler),    # new instance per ctx.get() call
])
```

Or as dicts for full control:

```python
context = Context([
    {
        'reference': MyService,
        'name': 'myService',
        'scope': 'singleton',
        'depends_on': ['otherBean'],
        'primary': True,
    },
])
```

## Scopes

| Scope | Behaviour | Helper |
|---|---|---|
| `singleton` | One instance per context, shared | `Singleton` |
| `prototype` | New instance on every `ctx.get()` | `Prototype` |

## Autowiring

### Implicit (null-property matching)

CDI inspects each singleton's instance properties after creation. Any property
that is `None` and whose name matches a registered component (in `snake_case`)
gets the singleton instance injected:

```python
class OrderService:
    def __init__(self):
        self.order_repository = None  # injected from 'order_repository' bean
        self.email_service    = None  # injected from 'email_service' bean
        self._cache           = {}    # not None → not autowired
```

Class names are converted to `snake_case` for the registry key:
`OrderRepository` → `order_repository`. Explicit `name=` overrides this.

### Config property injection

Bind config values using `${path:default}` placeholder strings as the initial
value in `__init__`:

```python
class ServerConfig:
    def __init__(self):
        self.port    = '${server.port:8080}'     # resolved from config
        self.host    = '${server.host:localhost}'
        self.timeout = '${server.timeout:30}'
```

CDI resolves placeholders against the wired `config` bean before calling
`init()`.

### Explicit wiring with `Property`

Use `Property` for cases where the property name does not match the bean name,
or you want to inject a config value into a specific property:

```python
from cdi import Property

context = Context([
    Singleton(DatabaseConnection),
    Property({'name': 'database_connection', 'property': 'url', 'path': 'db.url'}),
    Property({'name': 'database_connection', 'property': 'pool_size', 'value': 10}),
])
```

## Profiles

Restrict a bean to specific active profiles using the `profiles` class
attribute:

```python
class DevEmailService:
    profiles = ['dev']

class ProdEmailService:
    profiles = ['prod']
```

Activate profiles via `PY_ACTIVE_PROFILES=prod`. Beans without a `profiles`
attribute are always active.

When two beans would resolve to the same attribute name, use `primary = True`
on the profile-conditional one:

```python
class MockCache:
    profiles = ['test']
    primary  = True   # wins when test profile is active
```

## DependsOn

Control initialisation order explicitly with the `depends_on` class attribute:

```python
class SchemaInitializer:
    depends_on = ['data_source']

    def init(self):
        # data_source.init() has completed before this runs
        ...
```

CDI uses topological sort to call `init()` in dependency order. Circular
`depends_on` chains raise a `ValueError` at startup.

## Lifecycle

| Method | When called | Purpose |
|---|---|---|
| `__init__()` | `start()` — instantiation phase | Declare wirable attributes as `None` or placeholder strings |
| `set_application_context(ctx)` | after wiring, before `init()` | Receive the `ApplicationContext` reference |
| `init()` | after wiring | Post-injection startup logic |
| `run()` | after all `init()` | Application entry point (called on the `Application` bean) |
| `destroy()` | on SIGINT / `ctx.stop()` | Cleanup in reverse init order |

All methods are optional — implement only the ones you need.

`init()` and `destroy()` must be regular `def`, not `async def`. If you need to
call async code, bridge with `asyncio.run()`. See
[ADR-012](decisions/ADR-012-cdi-lifecycle-methods-synchronous.md).

## ApplicationContext API

```python
from cdi import ApplicationContext, Context, Singleton

ctx = ApplicationContext({
    'config':   cfg,         # config-like object
    'contexts': [context],   # list of Context objects
})
ctx.start()

svc = ctx.get('order_service')           # retrieve by snake_case name
svc = ctx.get('unknown', None)           # returns None if not found
```

> Use the dict constructor form. `ApplicationContext(Context([...]))` creates an
> empty `EphemeralConfig` internally and does not load any config files from
> disk.

## Using with Boot

`Boot.boot()` handles config loading, banner printing, and CDI wiring in one
call. It also auto-registers `config`, `logger_factory`, and
`logger_category_cache` as beans — any bean with `self.config = None` receives
the live config instance:

```python
from boot import Boot
from cdi import Context, Singleton

Boot.boot({
    'contexts': [Context([Singleton(MyService), Singleton(Application)])]
})
```

For tests, use `Boot.test()` — it suppresses the banner and captures log output
in memory:

```python
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
