# example-3-3-serverless-gcp-cloudfunction

Step 3.3 — GCP Cloud Functions serverless adapter example using alt-python/boot.

Demonstrates the CDI + `GCPCloudFunctionAdapter` warm-start pattern: CDI boots
once at module level and is reused across warm GCP Functions invocations.

## What it demonstrates

- `gcp_cloudfunction_starter()` wires the adapter and built-in middleware in one call
- `__routes__` declarative controller registration
- Property placeholder injection (`'${app.greeting:Hello}'`)
- Config-driven greeting from `config/application.json`
- Local invocation without a GCP Functions Framework via `invoke.py`

## Run locally

```bash
cd packages/example-3-3-serverless-gcp-cloudfunction
uv run python invoke.py
```

## Run tests

```bash
uv run pytest packages/example-3-3-serverless-gcp-cloudfunction -v
```

## Key files

| File | Description |
|---|---|
| `handler.py` | Function entry point — boots CDI and dispatches `flask.Request` |
| `controllers.py` | `GreetingController` with `GET /health` and `GET /greet/{name}` |
| `services.py` | `GreetingService` — reads greeting from config |
| `config/application.json` | App config — greeting text, log level |
| `invoke.py` | Local runner — constructs `flask.Request` objects and prints results |

## How it works

```python
# handler.py
_app_ctx = Boot.boot({
    'contexts': [Context([*gcp_cloudfunction_starter(), Singleton(GreetingService), Singleton(GreetingController)])],
    'run': False,
})
_adapter = _app_ctx.get('gcp_cloud_function_adapter')

def handler(request: FlaskRequest):
    return asyncio.run(_adapter.handle(request))
```

GCP Cloud Functions pass a `flask.Request`. The adapter extracts path parameters
by URL segment comparison against the registered route pattern — there is no
pre-populated route params dict as with Azure Functions.

Part of the [`alt-python/boot`](https://github.com/alt-python/boot) monorepo.
