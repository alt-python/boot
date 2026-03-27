"""
example-1-4-intro-cdi-advanced — service classes

Demonstrates advanced CDI features:
  - Profile-conditional bean activation (CasualGreetingStrategy only active with 'dev' profile)
  - primary flag for strategy disambiguation (CasualGreetingStrategy is primary when active)
  - depends_on ordering (Application waits for MetricsService to be initialised first)
  - set_application_context callback (MetricsService receives the ApplicationContext ref)
  - ConnectionPool gets config injected to resolve db.host / db.port

CRITICAL: all wired attrs must be set as snake_case in __init__ (self.x = None).
CDI metadata (profiles, scope, depends_on) must be class-level attributes.
"""


class ConnectionPool:
    def __init__(self):
        self.config = None

    def get_connection(self):
        host = self.config.get('db.host', 'localhost')
        port = self.config.get('db.port', 5432)
        return f'{host}:{port}'


class MetricsService:
    def __init__(self):
        self.app_ctx = None  # set via set_application_context

    def set_application_context(self, app_ctx):
        self.app_ctx = app_ctx

    def record(self, key, value):
        print(f'[metrics] {key}={value}')


class FormalGreetingStrategy:
    def __init__(self):
        self.connection_pool = None

    def greet(self, name):
        conn = self.connection_pool.get_connection()
        return f'Good day, {name}. (conn={conn})'


class CasualGreetingStrategy:
    profiles = ['dev']

    def __init__(self):
        self.connection_pool = None

    def greet(self, name):
        conn = self.connection_pool.get_connection()
        return f'Hey {name}! (conn={conn})'


class GreetingService:
    def __init__(self):
        self.greeting_strategy = None
        self.metrics_service = None

    def greet(self, name):
        msg = self.greeting_strategy.greet(name)
        self.metrics_service.record('greet', name)
        return msg


class Application:
    depends_on = ['metrics_service']  # snake_case component name

    def __init__(self):
        self.greeting_service = None

    def run(self):
        print(self.greeting_service.greet('World'))
        print(self.greeting_service.greet('Alt-Python'))
