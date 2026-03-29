# example-3-2-serverless-azure-function

Step 3.2 — Azure Functions serverless adapter example using alt-python/boot.

Demonstrates the CDI + `AzureFunctionAdapter` warm-start pattern: CDI boots
once at module level and is reused across warm Azure Functions invocations.

## What it demonstrates

- `azure_function_starter()` wires the adapter and built-in middleware in one call
- `__routes__` declarative controller registration
- Property placeholder injection (`'${app.greeting:Hello}'`)
- Config-driven greeting from `config/application.json`
- Local invocation without an Azure Functions host via `invoke.py`

## Run locally

```bash
cd packages/example-3-2-serverless-azure-function
uv run python invoke.py
```

## Run tests

```bash
uv run pytest packages/example-3-2-serverless-azure-function -v
```

## Key files

| File | Description |
|---|---|
| `handler.py` | Function entry point — boots CDI and dispatches `func.HttpRequest` |
| `controllers.py` | `GreetingController` with `GET /health` and `GET /greet/{name}` |
| `services.py` | `GreetingService` — reads greeting from config |
| `config/application.json` | App config — greeting text, log level |
| `invoke.py` | Local runner — constructs `func.HttpRequest` objects and prints results |

## How it works

```python
# handler.py
_app_ctx = Boot.boot({
    'contexts': [Context([*azure_function_starter(), Singleton(GreetingService), Singleton(GreetingController)])],
    'run': False,
})
_adapter = _app_ctx.get('azure_function_adapter')

def handler(req: func.HttpRequest, context=None) -> func.HttpResponse:
    return asyncio.run(_adapter.handle(req, context))
```

Path parameters are extracted from `func.HttpRequest.route_params`, which Azure
pre-populates from the URL. The adapter merges them into
`request['params']` for the controller.

Part of the [`alt-python/boot`](https://github.com/alt-python/boot) monorepo.
