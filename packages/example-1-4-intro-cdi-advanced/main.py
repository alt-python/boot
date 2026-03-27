"""
example-1-4-intro-cdi-advanced

Demonstrates advanced CDI features: profile-conditional beans, primary strategy
disambiguation, depends_on ordering, and set_application_context callback.

Run:
  python main.py                         # Good day, World. / Good day, Alt-Python.
  PY_ACTIVE_PROFILES=dev python main.py  # Hey World! / Hey Alt-Python!
"""

from config import ConfigFactory
from cdi import ApplicationContext, Context, Singleton
from services import (ConnectionPool, MetricsService, FormalGreetingStrategy,
                      CasualGreetingStrategy, GreetingService, Application)

cfg = ConfigFactory.get_config()

app_ctx = ApplicationContext({
    'config': cfg,
    'contexts': [Context([
        Singleton(ConnectionPool),
        Singleton(MetricsService),
        Singleton({'reference': FormalGreetingStrategy, 'name': 'greetingStrategy'}),
        Singleton({'reference': CasualGreetingStrategy, 'name': 'greetingStrategy', 'primary': True}),
        Singleton(GreetingService),
        Singleton(Application),
    ])],
})
app_ctx.start()
