# alt-python-boot-lib

[![Language](https://img.shields.io/badge/language-Python-3776ab.svg)](https://www.python.org/)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Application bootstrap for the alt-python framework. Provides the one-call
`Boot.boot()` entry point, the startup banner, and the `MiddlewarePipeline`
used by all HTTP and serverless adapters.

Inspired by [Spring Boot](https://spring.io/projects/spring-boot)'s
`SpringApplication.run()` auto-configuration and application context lifecycle.

Part of the [`alt-python/boot`](https://github.com/alt-python/boot) monorepo.

## Install

```bash
uv add alt-python-boot-lib   # or: pip install alt-python-boot-lib
```

Requires Python 3.12+, `alt-python-config`, `alt-python-logger`, and
`alt-python-cdi`.

## Quick Start

```python
from boot import Boot
from cdi import Context, Singleton


class GreetingService:
    def __init__(self):
        self.config = None   # CDI-autowired

    def greet(self, name: str) -> str:
        return f"Hello, {name}!"


class Application:
    def __init__(self):
        self.greeting_service = None  # CDI-autowired

    def run(self):
        print(self.greeting_service.greet("world"))


Boot.boot({
    'contexts': [
        Context([Singleton(GreetingService), Singleton(Application)])
    ]
})
```

`Boot.boot()` resolves config from the current directory, prints the startup
banner, and calls `application.run()` on the `Application` bean.

## API

```python
from boot import Boot, MiddlewarePipeline, RequestLoggerMiddleware, ErrorHandlerMiddleware, NotFoundMiddleware
```

### `Boot`

#### `Boot.boot(options=None)`

Bootstrap the application. Loads config, wires the CDI container, prints the
banner, and calls `run()` on the `Application` bean.

```python
Boot.boot({
    'contexts': [Context([Singleton(MyService), Singleton(Application)])]
})
```

Options:

| Key | Type | Description |
|---|---|---|
| `contexts` | `list[Context]` | CDI contexts to wire |
| `config` | config-like | Config source (default: auto-discovered via `ConfigFactory`) |

Returns the `ApplicationContext` after `start()` completes.

#### `Boot.test(options=None)`

Test bootstrap. Suppresses the startup banner and captures log output
in-memory. Accepts the same options as `Boot.boot()`.

```python
def test_my_service():
    ctx = Boot.test({
        'contexts': [Context([Singleton(MyService)])]
    })
    svc = ctx.get('my_service')
    assert svc.greet("world") == "Hello, world!"
```

#### `Boot.root(name, default=None)`

Read a value from the global boot context.

```python
config = Boot.root('config')
logger_factory = Boot.root('logger_factory')
```

---

### `MiddlewarePipeline`

The CDI middleware pipeline — the Python equivalent of Spring Security's filter
chain, applied uniformly across all HTTP and serverless adapters.

#### `MiddlewarePipeline.compose(middlewares, final_handler)`

Composes an ordered list of middleware instances and a final handler into a
single async callable.

```python
pipeline = MiddlewarePipeline.compose(middlewares, dispatch)
response = await pipeline(request)
```

`compose()` is called once per request. Middleware run in order (lowest `order`
value first). Each middleware calls `await next_fn(request)` to pass control
down the chain; returning without calling `next_fn` short-circuits the pipeline.

#### `MiddlewarePipeline.collect(ctx)`

Collects all CDI components that declare `__middleware__ = {"order": N}` from
an `ApplicationContext`, filters out uninstantiated entries, and returns them
sorted by `order`.

```python
middlewares = MiddlewarePipeline.collect(app_ctx)
```

#### Writing Middleware

A middleware component is a plain CDI class with `__middleware__ = {"order": N}`
as a class attribute and an `async def handle(self, request, next_fn)` method.
Lower order values run first (outermost).

```python
class AuthMiddleware:
    __middleware__ = {"order": 5}

    def __init__(self):
        self.logger = None  # CDI-autowired

    async def handle(self, request, next_fn):
        token = request.get("headers", {}).get("authorization", "").removeprefix("Bearer ")
        if not token:
            return {"statusCode": 401, "body": {"error": "Unauthorized"}}
        return await next_fn({**request, "user": {"token": token}})
```

Register it in the CDI context — no extra wiring needed:

```python
from boot_aws_lambda import lambda_starter
from cdi import Context, Singleton

context = Context([
    *lambda_starter(),
    Singleton(AuthMiddleware),   # auto-detected via __middleware__
    Singleton(TodoController),
])
```

#### Normalised Request Shape

All adapters present the same request dict to middleware:

```python
{
    "method":  "GET",
    "path":    "/todos/42",
    "params":  {"id": "42"},
    "query":   {"page": "1"},
    "headers": {...},
    "body":    {...},
    "ctx":     application_context,
}
```

Middleware written against this shape works identically across Lambda,
Azure Functions, GCP Cloud Functions, FastAPI, and Flask adapters.

---

### Built-in Middleware

Every `*_starter()` function registers these three middleware components:

| Class | Order | Behaviour |
|---|---|---|
| `RequestLoggerMiddleware` | 10 | Logs `METHOD /path → status (Xms)` at verbose level |
| `ErrorHandlerMiddleware` | 20 | Converts unhandled exceptions to JSON error responses |
| `NotFoundMiddleware` | 30 | Returns 404 when no route matches |

---

### `print_banner(config=None, logger=None)`

Prints the startup banner to stdout. Called automatically by `Boot.boot()`.
Pass `config` with `boot.banner-mode: off` to suppress:

```python
from boot import print_banner

print_banner()          # prints the banner
print_banner(config)    # suppressed if boot.banner-mode == "off"
```

## Testing

Use `Boot.test()` to suppress the banner and capture logs during tests:

```python
from boot import Boot
from cdi import Context, Singleton


def test_greet():
    ctx = Boot.test({
        'contexts': [Context([Singleton(GreetingService)])]
    })
    assert ctx.get('greeting_service').greet("world") == "Hello, world!"
```

`Boot.test()` wraps the config in a `PropertySourceChain` with
`boot.banner-mode: off` prepended, and uses `CachingLoggerFactory` so log
output is captured in-memory rather than printed.

## Spring Attribution

The `Boot` lifecycle maps to Spring Boot's `SpringApplication.run()`:

| Spring | alt-python-boot |
|---|---|
| `SpringApplication.run()` | `Boot.boot()` |
| `ApplicationContext.refresh()` + `start()` | `ApplicationContext.start()` |
| `@SpringBootApplication` banner | `print_banner()` |
| Spring Security `FilterChain` | `MiddlewarePipeline` |
| `Filter.doFilter(req, res, chain)` | `handle(request, next_fn)` |

## License

MIT
