# alt-python-boot-gcp-cloudfunction

[![Language](https://img.shields.io/badge/language-Python-3776ab.svg)](https://www.python.org/)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

GCP Cloud Functions adapter for the alt-python/boot framework. Handles GCP
Cloud Functions HTTP trigger requests (passed as `flask.Request`) with
CDI-managed controllers and a CDI middleware pipeline for cross-cutting
concerns.

Part of the [`alt-python/boot`](https://github.com/alt-python/boot) monorepo.

## Install

```bash
uv add alt-python-boot-gcp-cloudfunction   # or: pip install alt-python-boot-gcp-cloudfunction
```

Requires Python 3.12+, `alt-python-boot-lib`, and `flask`.

## Quick Start

```python
# main.py
import asyncio
from boot import Boot
from cdi import Context, Singleton
from boot_gcp_cloudfunction import gcp_cloudfunction_starter
from services import TodoService
from controllers import TodoController

context = Context([
    *gcp_cloudfunction_starter(),
    Singleton(TodoService),
    Singleton(TodoController),
])

# Boot once — module-level initialisation; reused on warm invocations
app_ctx = Boot.boot({'contexts': [context]})


def handler(request):
    """GCP Cloud Functions entry point."""
    adapter = app_ctx.get('gcp_cloud_function_adapter')
    return asyncio.run(adapter.handle(request))
```

## Controller Convention

Controllers declare routes via the `__routes__` class attribute. Path
parameters use `{param}` syntax (`:param` is also accepted and auto-converted):

```python
class TodoController:
    __routes__ = [
        {'method': 'GET',  'path': '/todos',      'handler': 'list'},
        {'method': 'POST', 'path': '/todos',      'handler': 'create'},
        {'method': 'GET',  'path': '/todos/{id}', 'handler': 'get_by_id'},
    ]

    def __init__(self):
        self.todo_service = None  # CDI-autowired

    async def list(self, request):
        return self.todo_service.find_all()

    async def create(self, request):
        return self.todo_service.create(request['body'])

    async def get_by_id(self, request):
        return self.todo_service.find_by_id(request['params']['id'])
```

Handler methods receive a normalised `request` dict and return one of:

- A plain `dict` → 200 with JSON body
- `{'statusCode': N, 'body': ...}` → explicit status code
- `None` or `{}` → 204 No Content

The adapter returns `flask.Response`.

## Middleware Pipeline

`gcp_cloudfunction_starter()` registers three built-in middleware components:

| Component | Order | Behaviour |
|---|---|---|
| `RequestLoggerMiddleware` | 10 | Logs `METHOD /path → status (Xms)` at verbose level |
| `ErrorHandlerMiddleware` | 20 | Converts unhandled exceptions to JSON error responses |
| `NotFoundMiddleware` | 30 | Returns 404 for unmatched routes |

Add custom middleware by declaring `__middleware__ = {"order": N}`:

```python
class AuthMiddleware:
    __middleware__ = {"order": 5}

    async def handle(self, request, next_fn):
        token = request.get('headers', {}).get('Authorization', '').removeprefix('Bearer ')
        if not token:
            return {'statusCode': 401, 'body': {'error': 'Unauthorized'}}
        return await next_fn({**request, 'user': {'token': token}})
```

## Request Shape

The normalised request dict passed to middleware and handlers:

```python
{
    'method':  'GET',
    'path':    '/todos/42',
    'params':  {'id': '42'},    # extracted by URL segment matching
    'query':   {'page': '1'},
    'headers': {'Authorization': 'Bearer token'},
    'body':    None,
    'ctx':     app_ctx,
}
```

GCP Cloud Functions receive a `flask.Request` with no pre-populated route
parameters. The adapter extracts path parameters by comparing URL segments
against the registered route pattern. Pass the full URL path (e.g.
`/todos/42`) — the adapter splits it on `/` and matches `{id}` segments.

## Route Registration

Two registration patterns are supported:

### Declarative (`__routes__`)

```python
class HealthController:
    __routes__ = [
        {'method': 'GET', 'path': '/health', 'handler': 'check'},
    ]

    async def check(self, request):
        return {'status': 'ok'}
```

### Imperative (`routes()`)

```python
class CustomController:
    def routes(self, routes, ctx):
        routes['GET /custom'] = {'handler': self.handle_custom}

    async def handle_custom(self, request):
        return {'custom': True}
```

`__routes__` takes precedence when both are present.

## Testing

Use `werkzeug.test.EnvironBuilder` to construct `flask.Request` objects without
a running GCP Functions Framework:

```python
import asyncio
from flask import Request as FlaskRequest
from werkzeug.test import EnvironBuilder


def flask_req(method, path, data=None, content_type='application/json'):
    builder = EnvironBuilder(method=method, path=path, data=data, content_type=content_type)
    return FlaskRequest(builder.get_environ())


def test_list_todos():
    from main import app_ctx
    adapter = app_ctx.get('gcp_cloud_function_adapter')
    req = flask_req('GET', '/todos')
    response = asyncio.run(adapter.handle(req))
    assert response.status_code == 200
```

## License

MIT
