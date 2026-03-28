"""
boot-azure-function — Azure Function adapter for alt-python/boot.

Public API:
  - AzureFunctionAdapter          — CDI-managed Azure Function HTTP handler
  - AzureFunctionControllerRegistrar — scans CDI components for route metadata
  - azure_function_starter()      — returns the CDI Singleton list for Azure Function apps
"""

from cdi import Singleton
from boot import RequestLoggerMiddleware, ErrorHandlerMiddleware, NotFoundMiddleware

from .azure_function_adapter import AzureFunctionAdapter
from .controller_registrar import AzureFunctionControllerRegistrar

__all__ = [
    "AzureFunctionAdapter",
    "AzureFunctionControllerRegistrar",
    "azure_function_starter",
]


def azure_function_starter():
    """
    Returns the list of CDI Singletons required to run an Azure Function application.

    Usage::

        from boot_azure_function import azure_function_starter
        from cdi import ApplicationContext

        ctx = ApplicationContext([
            *azure_function_starter(),
            # ... your controllers
        ])
        ctx.start()
        adapter = ctx.get('azure_function_adapter')

        async def main(req: func.HttpRequest) -> func.HttpResponse:
            return await adapter.handle(req)
    """
    return [
        Singleton({"reference": AzureFunctionAdapter, "name": "azureFunctionAdapter"}),
        Singleton({"reference": RequestLoggerMiddleware, "name": "requestLoggerMiddleware"}),
        Singleton({"reference": ErrorHandlerMiddleware, "name": "errorHandlerMiddleware"}),
        Singleton({"reference": NotFoundMiddleware, "name": "notFoundMiddleware"}),
    ]
