# alt-python-boot-aws-lambda

[![Language](https://img.shields.io/badge/language-Python-3776ab.svg)](https://www.python.org/)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

AWS Lambda adapter for the alt-python/boot framework. Handles API Gateway HTTP
API v2 events with CDI-managed controllers and a CDI middleware pipeline for
cross-cutting concerns.

CDI boots once on cold start and is reused on warm invocations — the same
pattern as Spring's `ApplicationContext` in a serverless launcher.

Part of the [`alt-python/boot`](https://github.com/alt-python/boot) monorepo.

## Install

```bash
uv add alt-python-boot-aws-lambda   # or: pip install alt-python-boot-aws-lambda
```

Requires Python 3.12+ and `alt-python-boot-lib`.

## Quick Start

```python
# handler.py (your Lambda entry point)
import asyncio
from boot import Boot
from cdi import Context, Singleton
from boot_aws_lambda import lambda_starter
from services import TodoService
from controllers import TodoController

context = Context([
    *lambda_starter(),
    Singleton(TodoService),
    Singleton(TodoController),
])

# Boot once — CDI is wired on cold start and reused on warm invocations
app_ctx = Boot.boot({'contexts': [context]})


def handler(event, lambda_context):
    adapter = app_ctx.get('lambda_adapter')
    return asyncio.run(adapter.handle(event, lambda_context))
```

## Controller Convention

Controllers declare routes via the `__routes__` class attribute. Path
parameters use `{param}` syntax (`:param` is auto-converted at registration
time):

```python
class TodoController:
    __routes__ = [
        {'method': 'GET',    'path': '/todos',       'handler': 'list'},
        {'method': 'POST',   'path': '/todos',       'handler': 'create'},
        {'method': 'GET',    'path': '/todos/{id}',  'handler': 'get_by_id'},
        {'method': 'DELETE', 'path': '/todos/{id}',  'handler': 'remove'},
    ]

    def __init__(self):
        self.todo_service = None  # CDI-autowired

    async def list(self, request):
        return self.todo_service.find_all()

    async def create(self, request):
        return self.todo_service.create(request['body'])

    async def get_by_id(self, request):
        return self.todo_service.find_by_id(request['params']['id'])

    async def remove(self, request):
        self.todo_service.delete(request['params']['id'])
```

Handler methods receive a normalised `request` dict and return one of:

- A plain `dict` → 200 with JSON body
- `{'statusCode': N, 'body': ...}` → explicit status code
- `None` or `{}` → 204 No Content

## Middleware Pipeline

`lambda_starter()` registers three built-in middleware components:

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
        token = request.get('headers', {}).get('authorization', '').removeprefix('Bearer ')
        if not token:
            return {'statusCode': 401, 'body': {'error': 'Unauthorized'}}
        return await next_fn({**request, 'user': {'token': token}})


context = Context([
    *lambda_starter(),
    Singleton(AuthMiddleware),   # auto-detected — no extra wiring
    Singleton(TodoController),
])
```

## Request Shape

The normalised request dict passed to middleware and handlers:

```python
{
    'method':        'GET',
    'path':          '/todos/42',
    'params':        {'id': '42'},
    'query':         {'page': '1'},
    'headers':       {'authorization': 'Bearer token'},
    'body':          None,
    'rawEvent':      event,          # original API Gateway v2 event
    'lambdaContext': lambda_context,
    'ctx':           app_ctx,
}
```

Path parameters are extracted from `event['pathParameters']`. The JSON body is
decoded automatically, including base64-encoded bodies (`isBase64Encoded: true`).

## Response Format

The adapter normalises handler return values into the Lambda response format:

| Return value | statusCode | body |
|---|---|---|
| Plain `dict` | 200 | JSON-encoded |
| `{'statusCode': N, 'body': ...}` | N | JSON-encoded |
| `None` or `{}` | 204 | empty string |

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

Test the handler directly with API Gateway v2 event shapes — no AWS account or
SAM/LocalStack needed:

```python
import asyncio
from handler import handler

def test_list_todos():
    event = {
        'routeKey': 'GET /todos',
        'pathParameters': {},
        'queryStringParameters': {},
        'headers': {},
        'body': None,
        'isBase64Encoded': False,
        'requestContext': {'http': {'method': 'GET', 'path': '/todos'}},
    }
    response = handler(event, {})
    assert response['statusCode'] == 200
```

## Spring Attribution

The cold-start/warm-reuse pattern maps to holding a Spring `ApplicationContext`
in a static field inside a serverless launcher — a common pattern for running
Spring Boot in AWS Lambda.

## License

MIT
