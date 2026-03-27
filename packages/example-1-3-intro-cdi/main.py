"""
example-1-3-intro-cdi

Introduces alt-python/cdi — basic dependency injection with null-property autowiring.

Key concepts:
  - ApplicationContext wires singletons by matching __init__ attribute names to
    registered component names (snake_case)
  - GreetingRepository gets the 'config' singleton injected automatically
  - GreetingService gets 'greeting_repository' injected
  - Application gets 'greeting_service' injected; its run() is called by start()

Run:
  python main.py                         # Hello, World! / Hello, Alt-Python!
  PY_ACTIVE_PROFILES=dev python main.py  # G'day, World! / G'day, Alt-Python!
"""

from config import ConfigFactory
from cdi import ApplicationContext, Context, Singleton
from services import GreetingRepository, GreetingService, Application

cfg = ConfigFactory.get_config()

app_ctx = ApplicationContext({
    'config': cfg,
    'contexts': [Context([
        Singleton(GreetingRepository),
        Singleton(GreetingService),
        Singleton(Application),
    ])],
})
app_ctx.start()
