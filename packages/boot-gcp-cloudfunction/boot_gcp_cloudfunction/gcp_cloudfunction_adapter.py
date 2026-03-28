import asyncio
import inspect
import json
import re

from flask import Request as FlaskRequest, Response as FlaskResponse

from boot.middleware_pipeline import MiddlewarePipeline

from .controller_registrar import GCPCloudFunctionControllerRegistrar


class GCPCloudFunctionAdapter:
    """
    CDI-managed GCP Cloud Function HTTP handler.

    Boots the route table once via GCPCloudFunctionControllerRegistrar, collects CDI
    middleware instances via MiddlewarePipeline.collect, then dispatches HTTP
    requests through the pipeline.

    CDI lifecycle:
      1. set_application_context(ctx) — CDI injects the application context
      2. init()                       — CDI calls after all singletons are wired
      3. handle(flask_request)        — invoked per request
    """

    def __init__(self):
        self._application_context = None
        self._routes = {}
        self._middlewares = []
        self.route_count = 0

    # ------------------------------------------------------------------
    # CDI lifecycle
    # ------------------------------------------------------------------

    def set_application_context(self, ctx) -> None:
        """CDI callback — stores the application context."""
        self._application_context = ctx

    def init(self) -> None:
        """
        CDI post-construct hook.

        Populates the route table and collects sorted middleware instances.
        """
        ctx = self._application_context
        registrar = GCPCloudFunctionControllerRegistrar()
        registrar.register(self._routes, ctx)
        self.route_count = registrar.route_count
        self._middlewares = MiddlewarePipeline.collect(ctx)

    # ------------------------------------------------------------------
    # Request handling
    # ------------------------------------------------------------------

    async def handle(self, flask_request: FlaskRequest) -> FlaskResponse:
        """
        Handle a GCP Cloud Function HTTP request.

        :param flask_request: Flask ``Request`` object (provided by functions-framework)
        :returns: Flask ``Response``
        """
        # Parse body — guard against JSONDecodeError
        body = None
        raw_data = flask_request.data
        if raw_data:
            try:
                body = flask_request.get_json(silent=True)
                if body is None:
                    body = raw_data  # return raw bytes on parse failure
            except (ValueError, TypeError):
                body = raw_data

        request = {
            "method": flask_request.method.upper(),
            "path": flask_request.path,
            "params": {},
            "query": dict(flask_request.args),
            "headers": dict(flask_request.headers),
            "body": body,
            "gcpRequest": flask_request,
            "ctx": self._application_context,
        }

        result = await MiddlewarePipeline.compose(self._middlewares, self._dispatch)(request)
        return self._normalize_response(result)

    async def _dispatch(self, request: dict):
        """
        Inner-most pipeline handler — routes to the matching controller method.

        Returns None if no route matches (NotFoundMiddleware converts to 404).
        Returns {'statusCode': 204} when a route matched but returned nothing.
        """
        route = self._match_route(request["method"], request["path"])
        if not route:
            return None  # NotFoundMiddleware will convert this to 404

        # Merge extracted URL path params into request['params']
        if route.get("params"):
            request["params"].update(route["params"])

        handler = route["handler"]
        result = handler(request)
        if inspect.isawaitable(result):
            result = await result

        if result is None or result == {}:
            return {"statusCode": 204}
        return result

    def _match_route(self, method: str, path: str):
        """
        Match a method + URL path against the registered route table.

        Supports colon-style path parameters (e.g. ``/users/:id``).

        :param method: HTTP method (upper-case)
        :param path: URL path (e.g. ``/users/42``)
        :returns: ``{'handler': callable, 'params': dict}`` or None
        """
        path_segments = [s for s in path.split("/") if s != "" or path == "/"]
        # Normalise: split on '/' and keep empty strings only for root
        path_parts = path.split("/")

        for route_key, entry in self._routes.items():
            parts = route_key.split(" ", 1)
            if len(parts) != 2:
                continue
            route_method, route_pattern = parts

            if route_method != method:
                continue

            pattern_parts = route_pattern.split("/")

            if len(pattern_parts) != len(path_parts):
                continue

            extracted = {}
            matched = True
            for pat_seg, path_seg in zip(pattern_parts, path_parts):
                if pat_seg.startswith(":"):
                    # Colon-style path parameter
                    extracted[pat_seg[1:]] = path_seg
                elif pat_seg != path_seg:
                    matched = False
                    break

            if matched:
                return {"handler": entry["handler"], "params": extracted}

        return None

    def _normalize_response(self, result) -> FlaskResponse:
        """
        Normalise a handler / pipeline return value into Flask ``Response``.

        - None         → 204 No Content (text/plain, empty body)
        - Has statusCode key → passthrough (body serialised to JSON string if needed)
        - Plain dict   → 200 with JSON-encoded body
        """
        if result is None:
            return FlaskResponse('', status=204, mimetype='text/plain')

        if 'statusCode' in result:
            body = result.get('body')
            if not isinstance(body, str):
                body = json.dumps(body)
            return FlaskResponse(body, status=result['statusCode'], mimetype='application/json')

        return FlaskResponse(json.dumps(result), status=200, mimetype='application/json')
