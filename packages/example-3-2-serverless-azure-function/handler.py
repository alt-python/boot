import asyncio
import azure.functions as func
from boot import Boot
from cdi import Context, Singleton
from boot_azure_function import azure_function_starter
from controllers import GreetingController
from services import GreetingService

_app_ctx = Boot.boot({
    'contexts': [Context([*azure_function_starter(), Singleton(GreetingService), Singleton(GreetingController)])],
    'run': False,
})
_adapter = _app_ctx.get('azure_function_adapter')


def handler(req: func.HttpRequest, context=None) -> func.HttpResponse:
    return asyncio.run(_adapter.handle(req, context))
