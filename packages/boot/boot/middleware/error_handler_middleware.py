class ErrorHandlerMiddleware:
    __middleware__ = {"order": 20}

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
            if config and config.has("middleware.errorHandler.enabled"):
                val = config.get("middleware.errorHandler.enabled")
                return val is not False and val != "false"
        except Exception:
            pass
        return True

    async def handle(self, request, next_fn):
        if not self._is_enabled():
            return await next_fn(request)
        try:
            return await next_fn(request)
        except Exception as err:
            status_code = getattr(err, "status_code", None) or getattr(err, "statusCode", None) or 500
            logger = self._logger()
            if logger:
                logger.error(f"Unhandled error ({status_code}): {err}")
            return {"statusCode": status_code, "body": {"error": str(err)}}
