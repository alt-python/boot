import asyncio
from boot import Boot
from cdi import Context, Singleton
from boot_gcp_cloudfunction import gcp_cloudfunction_starter
from flask import Request as FlaskRequest
from controllers import GreetingController
from services import GreetingService

_app_ctx = Boot.boot({
    'contexts': [Context([*gcp_cloudfunction_starter(), Singleton(GreetingService), Singleton(GreetingController)])],
    'run': False,
})
_adapter = _app_ctx.get('gcp_cloud_function_adapter')


def handler(request: FlaskRequest):
    return asyncio.run(_adapter.handle(request))
