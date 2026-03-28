class NotFoundMiddleware:
    __middleware__ = {"order": 30}

    def __init__(self):
        self._application_context = None

    def set_application_context(self, ctx):
        self._application_context = ctx

    def _is_enabled(self):
        try:
            config = getattr(self._application_context, "config", None) if self._application_context else None
            if config and config.has("middleware.notFound.enabled"):
                val = config.get("middleware.notFound.enabled")
                return val is not False and val != "false"
        except Exception:
            pass
        return True

    async def handle(self, request, next_fn):
        if not self._is_enabled():
            return await next_fn(request)
        result = await next_fn(request)
        if result is None:
            return {"statusCode": 404, "body": {"error": "Not found"}}
        return result
