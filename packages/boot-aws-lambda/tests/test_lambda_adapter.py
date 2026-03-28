"""
Test suite for boot-aws-lambda — 15 tests mirroring the JS spec.

All async dispatch tests use asyncio.run() directly — no pytest-asyncio needed.
"""
import asyncio
import json

import pytest
from cdi import ApplicationContext, Singleton
from cdi.context import Context

from boot import ErrorHandlerMiddleware, NotFoundMiddleware, RequestLoggerMiddleware
from boot_aws_lambda import LambdaAdapter, LambdaControllerRegistrar, lambda_starter

# ---------------------------------------------------------------------------
# Test controllers (defined at module level so CDI can scan them)
# ---------------------------------------------------------------------------


class HealthController:
    __routes__ = [{"method": "GET", "path": "/health", "handler": "health"}]

    def health(self, req):
        return {"status": "ok"}


class GreetController:
    __routes__ = [{"method": "GET", "path": "/greet/{name}", "handler": "greet"}]

    def greet(self, req):
        return {"message": f'Hello, {req["params"]["name"]}!'}


class EchoController:
    __routes__ = [{"method": "POST", "path": "/echo", "handler": "echo"}]

    def echo(self, req):
        return {"received": req["body"]}


class StatusController:
    __routes__ = [{"method": "POST", "path": "/items", "handler": "create"}]

    def create(self, req):
        return {"statusCode": 201, "body": {"created": True}}


class ErrorController:
    __routes__ = [
        {"method": "GET", "path": "/error/500", "handler": "server_error"},
        {"method": "GET", "path": "/error/custom", "handler": "custom_error"},
    ]

    def server_error(self, req):
        raise RuntimeError("Something went wrong")

    def custom_error(self, req):
        err = RuntimeError("Forbidden")
        err.status_code = 403
        raise err


class ImperativeController:
    def routes(self, router, ctx):
        router["GET /imperative"] = {"handler": lambda req: {"from": "imperative"}}


class ExpressStyleController:
    __routes__ = [{"method": "GET", "path": "/users/:userId", "handler": "get_user"}]

    def get_user(self, req):
        return {"userId": req["params"]["userId"]}


class DeleteController:
    __routes__ = [{"method": "DELETE", "path": "/items/{id}", "handler": "delete"}]

    def delete(self, req):
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def api_event(route_key, overrides=None):
    """Build a minimal API Gateway v2 event dict."""
    parts = route_key.split(" ", 1)
    e = {
        "routeKey": route_key,
        "pathParameters": {},
        "queryStringParameters": {},
        "headers": {"content-type": "application/json"},
        "body": None,
        "isBase64Encoded": False,
        "requestContext": {
            "http": {
                "method": parts[0],
                "path": parts[1] if len(parts) > 1 else "/",
            }
        },
    }
    if overrides:
        e.update(overrides)
    return e


def build_context(*extra_singletons):
    """Build and start an ApplicationContext with lambda_starter() + extra components."""
    ctx = ApplicationContext(
        {"contexts": [Context(list(lambda_starter()) + list(extra_singletons))]}
    )
    ctx.start(run=False)
    return ctx


# ---------------------------------------------------------------------------
# 1. Import symbols
# ---------------------------------------------------------------------------


def test_import_symbols():
    """LambdaAdapter, LambdaControllerRegistrar, and lambda_starter are importable."""
    assert LambdaAdapter is not None
    assert LambdaControllerRegistrar is not None
    assert lambda_starter is not None


# ---------------------------------------------------------------------------
# 2. lambda_starter() returns four singletons covering all required types
# ---------------------------------------------------------------------------


def test_lambda_starter_returns_four_singletons():
    """lambda_starter() yields exactly 4 CDI Singletons for the required components."""
    starters = list(lambda_starter())
    assert len(starters) == 4

    references = {s.reference for s in starters}
    assert LambdaAdapter in references
    assert RequestLoggerMiddleware in references
    assert ErrorHandlerMiddleware in references
    assert NotFoundMiddleware in references


# ---------------------------------------------------------------------------
# 3. Adapter registered in CDI context
# ---------------------------------------------------------------------------


def test_adapter_registered_in_context():
    """build_context() starts cleanly and ctx.get() returns a LambdaAdapter with routes."""
    ctx = build_context(
        Singleton({"reference": HealthController, "name": "healthController"})
    )
    adapter = ctx.get("lambda_adapter")
    assert isinstance(adapter, LambdaAdapter)
    assert adapter.route_count > 0


# ---------------------------------------------------------------------------
# 4. Route count from __routes__
# ---------------------------------------------------------------------------


def test_registers_routes_from_dunder_routes():
    """Three declarative controllers produce exactly 3 registered routes."""
    ctx = build_context(
        Singleton({"reference": HealthController, "name": "healthController"}),
        Singleton({"reference": GreetController, "name": "greetController"}),
        Singleton({"reference": EchoController, "name": "echoController"}),
    )
    adapter = ctx.get("lambda_adapter")
    assert adapter.route_count == 3


# ---------------------------------------------------------------------------
# 5. GET /health returns 200
# ---------------------------------------------------------------------------


def test_get_health_returns_200():
    """GET /health responds with statusCode 200 and {'status': 'ok'}."""
    ctx = build_context(
        Singleton({"reference": HealthController, "name": "healthController"})
    )
    adapter = ctx.get("lambda_adapter")
    result = asyncio.run(adapter.handle(api_event("GET /health")))
    assert result["statusCode"] == 200
    assert json.loads(result["body"]) == {"status": "ok"}


# ---------------------------------------------------------------------------
# 6. GET with path parameter
# ---------------------------------------------------------------------------


def test_get_with_path_param():
    """GET /greet/{name} injects path parameters into request['params']."""
    ctx = build_context(
        Singleton({"reference": GreetController, "name": "greetController"})
    )
    adapter = ctx.get("lambda_adapter")
    event = api_event("GET /greet/{name}", {"pathParameters": {"name": "Alice"}})
    result = asyncio.run(adapter.handle(event))
    assert result["statusCode"] == 200
    assert "Alice" in result["body"]


# ---------------------------------------------------------------------------
# 7. POST with JSON body
# ---------------------------------------------------------------------------


def test_post_with_json_body():
    """POST /echo parses the JSON body and echoes it back."""
    ctx = build_context(
        Singleton({"reference": EchoController, "name": "echoController"})
    )
    adapter = ctx.get("lambda_adapter")
    event = api_event("POST /echo", {"body": json.dumps({"key": "val"})})
    result = asyncio.run(adapter.handle(event))
    assert result["statusCode"] == 200
    assert json.loads(result["body"]) == {"received": {"key": "val"}}


# ---------------------------------------------------------------------------
# 8. Plain object response includes Content-Type header
# ---------------------------------------------------------------------------


def test_plain_object_response_200():
    """A plain-dict response gets statusCode 200 and application/json Content-Type."""
    ctx = build_context(
        Singleton({"reference": HealthController, "name": "healthController"})
    )
    adapter = ctx.get("lambda_adapter")
    result = asyncio.run(adapter.handle(api_event("GET /health")))
    assert result["statusCode"] == 200
    assert result["headers"]["Content-Type"] == "application/json"


# ---------------------------------------------------------------------------
# 9. statusCode dict passthrough — 201
# ---------------------------------------------------------------------------


def test_statuscode_dict_passthrough_201():
    """A handler returning {'statusCode': 201, 'body': {...}} passes through with 201."""
    ctx = build_context(
        Singleton({"reference": StatusController, "name": "statusController"})
    )
    adapter = ctx.get("lambda_adapter")
    result = asyncio.run(adapter.handle(api_event("POST /items")))
    assert result["statusCode"] == 201
    assert json.loads(result["body"]) == {"created": True}


# ---------------------------------------------------------------------------
# 10. Handler returning None → 204 No Content
# ---------------------------------------------------------------------------


def test_none_result_returns_204():
    """A handler that returns None produces a 204 No Content response."""
    ctx = build_context(
        Singleton({"reference": DeleteController, "name": "deleteController"})
    )
    adapter = ctx.get("lambda_adapter")
    event = api_event("DELETE /items/{id}", {"pathParameters": {"id": "5"}})
    result = asyncio.run(adapter.handle(event))
    assert result["statusCode"] == 204


# ---------------------------------------------------------------------------
# 11. Unhandled error → 500
# ---------------------------------------------------------------------------


def test_unhandled_error_returns_500():
    """An unhandled RuntimeError is caught by ErrorHandlerMiddleware and returns 500."""
    ctx = build_context(
        Singleton({"reference": ErrorController, "name": "errorController"})
    )
    adapter = ctx.get("lambda_adapter")
    result = asyncio.run(adapter.handle(api_event("GET /error/500")))
    assert result["statusCode"] == 500
    assert json.loads(result["body"]) == {"error": "Something went wrong"}


# ---------------------------------------------------------------------------
# 12. Error with custom status code
# ---------------------------------------------------------------------------


def test_error_with_custom_status():
    """An error with err.status_code=403 is returned as 403 Forbidden."""
    ctx = build_context(
        Singleton({"reference": ErrorController, "name": "errorController"})
    )
    adapter = ctx.get("lambda_adapter")
    result = asyncio.run(adapter.handle(api_event("GET /error/custom")))
    assert result["statusCode"] == 403
    assert json.loads(result["body"]) == {"error": "Forbidden"}


# ---------------------------------------------------------------------------
# 13. Unregistered route → 404
# ---------------------------------------------------------------------------


def test_unregistered_route_404():
    """A routeKey with no matching handler returns 404 via NotFoundMiddleware."""
    ctx = build_context(
        Singleton({"reference": HealthController, "name": "healthController"})
    )
    adapter = ctx.get("lambda_adapter")
    result = asyncio.run(adapter.handle(api_event("GET /nonexistent")))
    assert result["statusCode"] == 404


# ---------------------------------------------------------------------------
# 14. Missing routeKey → 400
# ---------------------------------------------------------------------------


def test_missing_route_key_400():
    """An event dict missing 'routeKey' returns 400 Bad Request."""
    ctx = build_context()
    adapter = ctx.get("lambda_adapter")
    result = asyncio.run(adapter.handle({}))
    assert result["statusCode"] == 400


# ---------------------------------------------------------------------------
# 15. Imperative routes pattern
# ---------------------------------------------------------------------------


def test_imperative_routes_pattern():
    """ImperativeController registers routes via routes(router, ctx) and handles requests."""
    ctx = build_context(
        Singleton(
            {"reference": ImperativeController, "name": "imperativeController"}
        )
    )
    adapter = ctx.get("lambda_adapter")
    result = asyncio.run(adapter.handle(api_event("GET /imperative")))
    assert result["statusCode"] == 200
    assert json.loads(result["body"]) == {"from": "imperative"}
