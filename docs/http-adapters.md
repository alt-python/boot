# HTTP and Serverless Adapters

All adapters share the same CDI controller convention and `MiddlewarePipeline`.
Write a controller once — deploy it to any supported runtime.

## Controller Convention

Controllers declare routes as a `__routes__` class attribute:

```python
class TodoController:
    __routes__ = [
        {'method': 'GET',    'path': '/todos',      'handler': 'list'},
        {'method': 'POST',   'path': '/todos',      'handler': 'create'},
        {'method': 'GET',    'path': '/todos/{id}', 'handler': 'get_by_id'},
        {'method': 'DELETE', 'path': '/todos/{id}', 'handler': 'remove'},
    ]

    def __init__(self):
        self.todo_service = None  # CDI-autowired

    def list(self, request):
        return self.todo_service.find_all()

    def create(self, request):
        return self.todo_service.create(request['body'])

    def get_by_id(self, request):
        return self.todo_service.find_by_id(request['params']['id'])

    def remove(self, request):
        self.todo_service.delete(request['params']['id'])
```

Handler return values are normalised to a response by each adapter:

| Return value | Status | Body |
|---|---|---|
| Plain `dict` | 200 | JSON-encoded |
| `{'statusCode': N, 'body': ...}` | N | JSON-encoded |
| `None` | 204 | empty |

Path parameters use `{param}` syntax. `:param` style is also accepted and
auto-converted at registration time.

## Normalised Request Shape

All adapters present the same request dict to handlers and middleware:

```python
{
    'method':  'GET',
    'path':    '/todos/42',
    'params':  {'id': '42'},
    'query':   {'page': '1'},
    'headers': {'authorization': 'Bearer token'},
    'body':    None,
    'ctx':     app_ctx,   # CDI ApplicationContext
}
```

## Middleware Pipeline

Every `*_starter()` function registers three built-in middleware components.
Add your own by declaring `__middleware__ = {"order": N}`:

```python
class AuthMiddleware:
    __middleware__ = {"order": 5}  # runs before built-ins (order 10+)

    async def handle(self, request, next_fn):
        token = request.get('headers', {}).get('authorization', '').removeprefix('Bearer ')
        if not token:
            return {'statusCode': 401, 'body': {'error': 'Unauthorized'}}
        return await next_fn({**request, 'user': {'token': token}})
```

Register it like any other CDI bean — the pipeline collects it automatically:

```python
context = Context([
    *lambda_starter(),
    Singleton(AuthMiddleware),
    Singleton(TodoController),
])
```

| Built-in | Order | Behaviour |
|---|---|---|
| `RequestLoggerMiddleware` | 10 | Logs `METHOD /path → status (Xms)` |
| `ErrorHandlerMiddleware` | 20 | Converts unhandled exceptions to JSON `500` |
| `NotFoundMiddleware` | 30 | Returns `404` for unmatched routes |

## AWS Lambda

```bash
uv add alt-python-boot-aws-lambda
```

```python
# handler.py
import asyncio
from boot import Boot
from cdi import Context, Singleton
from boot_aws_lambda import lambda_starter
from services import TodoService
from controllers import TodoController

app_ctx = Boot.boot({
    'contexts': [Context([*lambda_starter(), Singleton(TodoService), Singleton(TodoController)])],
    'run': False,
})
adapter = app_ctx.get('lambda_adapter')

def handler(event, context):
    return asyncio.run(adapter.handle(event, context))
```

CDI boots once on cold start and is reused on warm invocations.

API Gateway HTTP API v2 `routeKey` (`"GET /todos"`) is used for dispatch.
`pathParameters` provides path parameter values.

## Azure Functions

```bash
uv add alt-python-boot-azure-function
```

```python
# function_app.py
import asyncio
import azure.functions as func
from boot import Boot
from cdi import Context, Singleton
from boot_azure_function import azure_function_starter
from services import TodoService
from controllers import TodoController

app_ctx = Boot.boot({
    'contexts': [Context([*azure_function_starter(), Singleton(TodoService), Singleton(TodoController)])],
    'run': False,
})
adapter = app_ctx.get('azure_function_adapter')
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="{*route}", methods=["GET","POST","PUT","DELETE","PATCH"])
def http_handler(req: func.HttpRequest) -> func.HttpResponse:
    return asyncio.run(adapter.handle(req))
```

Azure pre-populates path parameters in `func.HttpRequest.route_params`; the
adapter merges them into `request['params']`.

## GCP Cloud Functions

```bash
uv add alt-python-boot-gcp-cloudfunction
```

```python
# main.py
import asyncio
from flask import Request as FlaskRequest
from boot import Boot
from cdi import Context, Singleton
from boot_gcp_cloudfunction import gcp_cloudfunction_starter
from services import TodoService
from controllers import TodoController

app_ctx = Boot.boot({
    'contexts': [Context([*gcp_cloudfunction_starter(), Singleton(TodoService), Singleton(TodoController)])],
    'run': False,
})
adapter = app_ctx.get('gcp_cloud_function_adapter')

def handler(request: FlaskRequest):
    return asyncio.run(adapter.handle(request))
```

GCP passes a `flask.Request`. The adapter extracts path parameters via URL
segment comparison — there is no pre-populated `route_params` dict as with
Azure.

## Testing Adapters Locally

All three adapters can be tested without any cloud account:

```python
# Lambda
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

```python
# Azure Functions
import azure.functions as func
import asyncio
from function_app import adapter

def test_list_todos():
    req = func.HttpRequest(
        method='GET', url='http://localhost/todos',
        headers={}, params={}, route_params={}, body=b'',
    )
    response = asyncio.run(adapter.handle(req))
    assert response.status_code == 200
```

```python
# GCP Cloud Functions
from flask import Request as FlaskRequest
from werkzeug.test import EnvironBuilder
import asyncio
from main import adapter

def test_list_todos():
    builder = EnvironBuilder(method='GET', path='/todos')
    req = FlaskRequest(builder.get_environ())
    response = asyncio.run(adapter.handle(req))
    assert response.status_code == 200
```
