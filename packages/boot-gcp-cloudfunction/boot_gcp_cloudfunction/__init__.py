"""
boot-gcp-cloudfunction — GCP Cloud Functions adapter for alt-python/boot.

Public API:
  - GCPCloudFunctionAdapter          — CDI-managed GCP Cloud Function HTTP handler
  - GCPCloudFunctionControllerRegistrar — scans CDI components for route metadata
  - gcp_cloudfunction_starter()      — returns the CDI Singleton list for GCP Cloud Function apps
"""

from cdi import Singleton
from boot import RequestLoggerMiddleware, ErrorHandlerMiddleware, NotFoundMiddleware

from .gcp_cloudfunction_adapter import GCPCloudFunctionAdapter
from .controller_registrar import GCPCloudFunctionControllerRegistrar

__all__ = [
    "GCPCloudFunctionAdapter",
    "GCPCloudFunctionControllerRegistrar",
    "gcp_cloudfunction_starter",
]


def gcp_cloudfunction_starter():
    """
    Returns the list of CDI Singletons required to run a GCP Cloud Function application.

    Usage::

        from boot_gcp_cloudfunction import gcp_cloudfunction_starter
        from cdi import ApplicationContext

        ctx = ApplicationContext([
            *gcp_cloudfunction_starter(),
            # ... your controllers
        ])
        ctx.start()
        adapter = ctx.get('gcpCloudFunctionAdapter')

        import functions_framework

        @functions_framework.http
        def main(request):
            import asyncio
            return asyncio.run(adapter.handle(request))
    """
    return [
        Singleton({"reference": GCPCloudFunctionAdapter, "name": "gcpCloudFunctionAdapter"}),
        Singleton({"reference": RequestLoggerMiddleware, "name": "requestLoggerMiddleware"}),
        Singleton({"reference": ErrorHandlerMiddleware, "name": "errorHandlerMiddleware"}),
        Singleton({"reference": NotFoundMiddleware, "name": "notFoundMiddleware"}),
    ]
