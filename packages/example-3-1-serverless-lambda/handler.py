import asyncio
from boot import Boot
from cdi import Context, Singleton
from boot_aws_lambda import lambda_starter
from controllers import GreetingController
from services import GreetingService

_app_ctx = Boot.boot({
    'contexts': [Context([*lambda_starter(), Singleton(GreetingService), Singleton(GreetingController)])],
    'run': False,
})
_adapter = _app_ctx.get('lambda_adapter')


def handler(event, context):
    return asyncio.run(_adapter.handle(event, context))
