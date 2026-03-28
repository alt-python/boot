"""
boot-aws-lambda — AWS Lambda adapter for alt-python/boot.

Public API:
  - LambdaAdapter          — CDI-managed Lambda handler
  - LambdaControllerRegistrar — scans CDI components for route metadata
  - lambda_starter()       — returns the CDI Singleton list for Lambda apps
"""

from cdi import Singleton
from boot import RequestLoggerMiddleware, ErrorHandlerMiddleware, NotFoundMiddleware

from .lambda_adapter import LambdaAdapter
from .lambda_controller_registrar import LambdaControllerRegistrar

__all__ = [
    "LambdaAdapter",
    "LambdaControllerRegistrar",
    "lambda_starter",
]


def lambda_starter():
    """
    Returns the list of CDI Singletons required to run a Lambda application.

    Usage::

        from boot_aws_lambda import lambda_starter
        from cdi import ApplicationContext

        ctx = ApplicationContext([
            *lambda_starter(),
            # ... your controllers
        ])
        ctx.start()
        adapter = ctx.get('lambdaAdapter')

        def handler(event, context):
            import asyncio
            return asyncio.run(adapter.handle(event, context))
    """
    return [
        Singleton({"reference": LambdaAdapter, "name": "lambdaAdapter"}),
        Singleton({"reference": RequestLoggerMiddleware, "name": "requestLoggerMiddleware"}),
        Singleton({"reference": ErrorHandlerMiddleware, "name": "errorHandlerMiddleware"}),
        Singleton({"reference": NotFoundMiddleware, "name": "notFoundMiddleware"}),
    ]
