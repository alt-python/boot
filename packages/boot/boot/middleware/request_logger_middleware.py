import time


class RequestLoggerMiddleware:
    __middleware__ = {"order": 10}

    def __init__(self):
        self._application_context = None

    def set_application_context(self, ctx):
        self._application_context = ctx

    def _logger(self):
        try:
            return self._application_context.get("logger", None) if self._application_context else None
        except Exception:
            return None

    def _is_enabled(self):
        try:
            config = getattr(self._application_context, "config", None) if self._application_context else None
            if config and config.has("middleware.requestLogger.enabled"):
                val = config.get("middleware.requestLogger.enabled")
                return val is not False and val != "false"
        except Exception:
            pass
        return True

    async def handle(self, request, next_fn):
        if not self._is_enabled():
            return await next_fn(request)
        method = request.get("method", "?") if isinstance(request, dict) else getattr(request, "method", "?")
        path = (request.get("path") or request.get("url", "?")) if isinstance(request, dict) else getattr(request, "path", "?")
        start = time.monotonic()
        try:
            result = await next_fn(request)
            status = result.get("statusCode", 200) if isinstance(result, dict) else getattr(result, "status_code", 200)
            duration_ms = int((time.monotonic() - start) * 1000)
            logger = self._logger()
            if logger:
                logger.verbose(f"[{method}] {path} → {status} ({duration_ms}ms)")
            return result
        except Exception:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger = self._logger()
            if logger:
                import sys
                exc = sys.exc_info()[1]
                logger.error(f"[{method}] {path} → ERROR ({duration_ms}ms): {exc}")
            raise
