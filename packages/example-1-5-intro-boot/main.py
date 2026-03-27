from boot import Boot
from cdi import Context, Singleton
from services import GreetingRepository, GreetingService, Application

Boot.boot({
    'contexts': [Context([
        Singleton(GreetingRepository),
        Singleton(GreetingService),
        Singleton(Application),
    ])]
})
