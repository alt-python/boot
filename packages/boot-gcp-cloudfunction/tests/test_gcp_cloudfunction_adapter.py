"""
Test suite for boot-gcp-cloudfunction — 15 tests mirroring the Azure spec.

All async dispatch tests use asyncio.run() directly — no pytest-asyncio needed.
Flask Request objects replace azure.functions HttpRequest; response inspection
uses resp.status_code, resp.get_data(), and resp.mimetype.
"""
import asyncio
import json

import pytest
from cdi import ApplicationContext, Singleton
from cdi.context import Context
from flask import Request as FlaskRequest
from werkzeug.test import EnvironBuilder

from boot import ErrorHandlerMiddleware, NotFoundMiddleware, RequestLoggerMiddleware
from boot_gcp_cloudfunction import (
    GCPCloudFunctionAdapter,
    GCPCloudFunctionControllerRegistrar,
    gcp_cloudfunction_starter,
)

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


class DeleteController:
    __routes__ = [{"method": "DELETE", "path": "/items/{id}", "handler": "delete"}]

    def delete(self, req):
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def flask_req(method, path, data=None, content_type="application/json", headers=None):
    """Build a minimal Flask Request using werkzeug's EnvironBuilder."""
    kwargs = {"method": method, "path": path}
    if data:
        kwargs["data"] = data
        kwargs["content_type"] = content_type
    if headers:
        kwargs["headers"] = headers
    builder = EnvironBuilder(**kwargs)
    return FlaskRequest(builder.get_environ())


def build_context(*extra):
    """Build and start an ApplicationContext with gcp_cloudfunction_starter() + extras."""
    ctx = ApplicationContext(
        {"contexts": [Context(list(gcp_cloudfunction_starter()) + list(extra))]}
    )
    ctx.start(run=False)
    return ctx


# ---------------------------------------------------------------------------
# 1. Import symbols
# ---------------------------------------------------------------------------


def test_import_symbols():
    """GCPCloudFunctionAdapter, GCPCloudFunctionControllerRegistrar, and gcp_cloudfunction_starter are importable."""
    assert GCPCloudFunctionAdapter is not None
    assert GCPCloudFunctionControllerRegistrar is not None
    assert gcp_cloudfunction_starter is not None


# ---------------------------------------------------------------------------
# 2. gcp_cloudfunction_starter() returns four singletons covering all required types
# ---------------------------------------------------------------------------


def test_gcp_cloudfunction_starter_returns_four_singletons():
    """gcp_cloudfunction_starter() yields exactly 4 CDI Singletons for the required components."""
    starters = list(gcp_cloudfunction_starter())
    assert len(starters) == 4

    references = {s.reference for s in starters}
    assert GCPCloudFunctionAdapter in references
    assert RequestLoggerMiddleware in references
    assert ErrorHandlerMiddleware in references
    assert NotFoundMiddleware in references


# ---------------------------------------------------------------------------
# 3. Adapter registered in CDI context
# ---------------------------------------------------------------------------


def test_adapter_registered_in_context():
    """build_context() starts cleanly and ctx.get() returns a GCPCloudFunctionAdapter with routes."""
    ctx = build_context(
        Singleton({"reference": HealthController, "name": "healthController"})
    )
    adapter = ctx.get("gcp_cloud_function_adapter")
    assert isinstance(adapter, GCPCloudFunctionAdapter)
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
    adapter = ctx.get("gcp_cloud_function_adapter")
    assert adapter.route_count == 3


# ---------------------------------------------------------------------------
# 5. GET /health returns 200
# ---------------------------------------------------------------------------


def test_get_health_returns_200():
    """GET /health responds with status_code 200 and {'status': 'ok'}."""
    ctx = build_context(
        Singleton({"reference": HealthController, "name": "healthController"})
    )
    adapter = ctx.get("gcp_cloud_function_adapter")
    req = flask_req("GET", "/health")
    resp = asyncio.run(adapter.handle(req))
    assert resp.status_code == 200
    assert json.loads(resp.get_data()) == {"status": "ok"}


# ---------------------------------------------------------------------------
# 6. GET with path parameter
# ---------------------------------------------------------------------------


def test_get_with_path_param():
    """GET /greet/Alice extracts 'Alice' from the URL path and injects into request['params']."""
    ctx = build_context(
        Singleton({"reference": GreetController, "name": "greetController"})
    )
    adapter = ctx.get("gcp_cloud_function_adapter")
    # No route_params — _match_route extracts params from URL segments
    req = flask_req("GET", "/greet/Alice")
    resp = asyncio.run(adapter.handle(req))
    assert resp.status_code == 200
    assert "Alice" in resp.get_data(as_text=True)


# ---------------------------------------------------------------------------
# 7. POST with JSON body
# ---------------------------------------------------------------------------


def test_post_with_json_body():
    """POST /echo parses the JSON body and echoes it back."""
    ctx = build_context(
        Singleton({"reference": EchoController, "name": "echoController"})
    )
    adapter = ctx.get("gcp_cloud_function_adapter")
    req = flask_req(
        "POST",
        "/echo",
        data=json.dumps({"key": "val"}),
        content_type="application/json",
    )
    resp = asyncio.run(adapter.handle(req))
    assert resp.status_code == 200
    assert json.loads(resp.get_data()) == {"received": {"key": "val"}}


# ---------------------------------------------------------------------------
# 8. Plain object response — 200 application/json
# ---------------------------------------------------------------------------


def test_plain_object_response_200():
    """A plain-dict response gets status_code 200 and application/json mimetype."""
    ctx = build_context(
        Singleton({"reference": HealthController, "name": "healthController"})
    )
    adapter = ctx.get("gcp_cloud_function_adapter")
    req = flask_req("GET", "/health")
    resp = asyncio.run(adapter.handle(req))
    assert resp.status_code == 200
    assert json.loads(resp.get_data()) == {"status": "ok"}


# ---------------------------------------------------------------------------
# 9. statusCode dict passthrough — 201
# ---------------------------------------------------------------------------


def test_statuscode_dict_passthrough_201():
    """A handler returning {'statusCode': 201, 'body': {...}} passes through with 201."""
    ctx = build_context(
        Singleton({"reference": StatusController, "name": "statusController"})
    )
    adapter = ctx.get("gcp_cloud_function_adapter")
    req = flask_req("POST", "/items")
    resp = asyncio.run(adapter.handle(req))
    assert resp.status_code == 201
    assert json.loads(resp.get_data()) == {"created": True}


# ---------------------------------------------------------------------------
# 10. Handler returning None → 204 No Content
# ---------------------------------------------------------------------------


def test_none_result_returns_204():
    """A handler that returns None produces a 204 No Content response."""
    ctx = build_context(
        Singleton({"reference": DeleteController, "name": "deleteController"})
    )
    adapter = ctx.get("gcp_cloud_function_adapter")
    req = flask_req("DELETE", "/items/5")
    resp = asyncio.run(adapter.handle(req))
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# 11. Unhandled error → 500
# ---------------------------------------------------------------------------


def test_unhandled_error_returns_500():
    """An unhandled RuntimeError is caught by ErrorHandlerMiddleware and returns 500."""
    ctx = build_context(
        Singleton({"reference": ErrorController, "name": "errorController"})
    )
    adapter = ctx.get("gcp_cloud_function_adapter")
    req = flask_req("GET", "/error/500")
    resp = asyncio.run(adapter.handle(req))
    assert resp.status_code == 500
    assert json.loads(resp.get_data()) == {"error": "Something went wrong"}


# ---------------------------------------------------------------------------
# 12. Error with custom status code
# ---------------------------------------------------------------------------


def test_error_with_custom_status():
    """An error with err.status_code=403 is returned as 403 Forbidden."""
    ctx = build_context(
        Singleton({"reference": ErrorController, "name": "errorController"})
    )
    adapter = ctx.get("gcp_cloud_function_adapter")
    req = flask_req("GET", "/error/custom")
    resp = asyncio.run(adapter.handle(req))
    assert resp.status_code == 403
    assert json.loads(resp.get_data()) == {"error": "Forbidden"}


# ---------------------------------------------------------------------------
# 13. Unregistered route → 404
# ---------------------------------------------------------------------------


def test_unregistered_route_404():
    """A path with no matching handler returns 404 via NotFoundMiddleware."""
    ctx = build_context(
        Singleton({"reference": HealthController, "name": "healthController"})
    )
    adapter = ctx.get("gcp_cloud_function_adapter")
    req = flask_req("GET", "/nonexistent")
    resp = asyncio.run(adapter.handle(req))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 14. Empty body is handled gracefully (no JSON parse error)
# ---------------------------------------------------------------------------


def test_empty_body_handled_gracefully():
    """A request with no body doesn't raise a JSONDecodeError."""
    ctx = build_context(
        Singleton({"reference": HealthController, "name": "healthController"})
    )
    adapter = ctx.get("gcp_cloud_function_adapter")
    # data=None → no body in the request
    req = flask_req("GET", "/health")
    resp = asyncio.run(adapter.handle(req))
    assert resp.status_code == 200


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
    adapter = ctx.get("gcp_cloud_function_adapter")
    req = flask_req("GET", "/imperative")
    resp = asyncio.run(adapter.handle(req))
    assert resp.status_code == 200
    assert json.loads(resp.get_data()) == {"from": "imperative"}
