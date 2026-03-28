import base64
import inspect
import json

from boot.middleware_pipeline import MiddlewarePipeline

from .lambda_controller_registrar import LambdaControllerRegistrar


class LambdaAdapter:
    """
    CDI-managed AWS Lambda handler.

    Boots the route table once via LambdaControllerRegistrar, collects CDI
    middleware instances via MiddlewarePipeline.collect, then dispatches
    API Gateway HTTP API v2 events through the pipeline.

    CDI lifecycle:
      1. set_application_context(ctx) — CDI injects the application context
      2. init()                       — CDI calls after all singletons are wired
      3. handle(event, lambda_context) — invoked per request
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
        registrar = LambdaControllerRegistrar()
        registrar.register(self._routes, ctx)
        self.route_count = registrar.route_count
        self._middlewares = MiddlewarePipeline.collect(ctx)

    # ------------------------------------------------------------------
    # Request handling
    # ------------------------------------------------------------------

    async def handle(self, event: dict, lambda_context=None) -> dict:
        """
        Handle an API Gateway HTTP API v2 event.

        :param event: API Gateway v2 event dict
        :param lambda_context: AWS Lambda context object (optional)
        :returns: Lambda response dict {statusCode, body, headers}
        """
        headers = {"Content-Type": "application/json"}

        route_key = event.get("routeKey")
        if not route_key:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing routeKey"}),
                "headers": headers,
            }

        # Parse JSON body if present
        parsed_body = None
        raw_body = event.get("body")
        if raw_body:
            try:
                if event.get("isBase64Encoded"):
                    decoded = base64.b64decode(raw_body).decode("utf-8")
                    parsed_body = json.loads(decoded)
                else:
                    parsed_body = json.loads(raw_body)
            except (ValueError, TypeError):
                parsed_body = raw_body

        request_context = event.get("requestContext") or {}
        http_ctx = request_context.get("http") or {}

        request = {
            "method": http_ctx.get("method") or route_key.split(" ")[0],
            "path": http_ctx.get("path") or route_key.split(" ")[1],
            "params": event.get("pathParameters") or {},
            "query": event.get("queryStringParameters") or {},
            "headers": event.get("headers") or {},
            "body": parsed_body,
            "rawEvent": event,
            "lambdaContext": lambda_context,
            "ctx": self._application_context,
        }

        result = await MiddlewarePipeline.compose(self._middlewares, self._dispatch)(request)
        return self._normalize_response(result, headers)

    async def _dispatch(self, request: dict):
        """
        Inner-most pipeline handler — routes to the matching controller method.

        Returns None if no route matches (NotFoundMiddleware converts to 404).
        Returns {'statusCode': 204} when a route matched but returned nothing.
        """
        route = self._match_route(request["rawEvent"]["routeKey"])
        if not route:
            return None  # NotFoundMiddleware will convert this to 404

        handler = route["handler"]
        result = handler(request)
        if inspect.isawaitable(result):
            result = await result

        if result is None or result == {}:
            return {"statusCode": 204}
        return result

    def _match_route(self, route_key: str):
        """
        Look up a routeKey in the registered route table.

        :param route_key: e.g. "GET /health"
        :returns: route entry dict or None
        """
        return self._routes.get(route_key)

    def _normalize_response(self, result, default_headers: dict) -> dict:
        """
        Normalise a handler / pipeline return value into Lambda response format.

        - None         → 204 No Content
        - Has statusCode key → passthrough (body always serialised as JSON string)
        - Plain dict   → 200 with JSON-encoded body
        """
        if result is None:
            return {"statusCode": 204, "body": "", "headers": default_headers}

        if "statusCode" in result:
            body = result.get("body")
            if not isinstance(body, str):
                body = json.dumps(body)
            return {
                "statusCode": result["statusCode"],
                "body": body,
                "headers": {**default_headers, **(result.get("headers") or {})},
            }

        return {
            "statusCode": 200,
            "body": json.dumps(result),
            "headers": default_headers,
        }
