# example-3-1-serverless-lambda

Step 3.1 — AWS Lambda serverless adapter example using alt-python/boot.

Demonstrates the CDI + `LambdaAdapter` warm-start pattern: CDI boots once at
module level and is reused across warm Lambda invocations.

## What it demonstrates

- `lambda_starter()` wires the adapter and built-in middleware in one call
- `__routes__` declarative controller registration
- Property placeholder injection (`'${app.greeting:Hello}'`)
- Config-driven greeting from `config/application.json`
- Local invocation without a Lambda runtime via `invoke.py`

## Run locally

```bash
cd packages/example-3-1-serverless-lambda
uv run python invoke.py
```

Expected output:

```
GET /health [200] {"status": "ok"}
GET /greet/{name} [200] {"message": "Hello, World!"}
GET /missing [404] {"error": "Not Found", "path": "/missing"}
```

## Run tests

```bash
uv run pytest packages/example-3-1-serverless-lambda -v
```

## Key files

| File | Description |
|---|---|
| `handler.py` | Lambda entry point — boots CDI and dispatches events |
| `controllers.py` | `GreetingController` with `GET /health` and `GET /greet/{name}` |
| `services.py` | `GreetingService` — reads greeting from config |
| `config/application.json` | App config — greeting text, log level |
| `invoke.py` | Local runner — constructs API Gateway v2 events and prints results |

## How it works

```python
# handler.py
_app_ctx = Boot.boot({
    'contexts': [Context([*lambda_starter(), Singleton(GreetingService), Singleton(GreetingController)])],
    'run': False,
})
_adapter = _app_ctx.get('lambda_adapter')

def handler(event, context):
    return asyncio.run(_adapter.handle(event, context))
```

`Boot.boot()` with `run: False` wires all CDI beans but does not call
`Application.run()`. CDI initialises once on cold start; `_adapter.handle()` is
called on every invocation.

The `GreetingService` reads its greeting text from config via a CDI property
placeholder:

```python
class GreetingService:
    def __init__(self):
        self.greeting = '${app.greeting:Hello}'  # resolved from config

    def greet(self, name):
        return f"{self.greeting}, {name}!"
```

Part of the [`alt-python/boot`](https://github.com/alt-python/boot) monorepo.
