"""
example-1-3-intro-cdi — service classes

Demonstrates null-property autowiring via CDI:
  - GreetingRepository: injected with 'config' singleton
  - GreetingService: injected with 'greeting_repository' singleton
  - Application: injected with 'greeting_service' singleton

CRITICAL: all wired attrs must be set as snake_case in __init__ (self.x = None).
Autowiring uses vars(instance), so only __init__-set attributes are considered.
"""


class GreetingRepository:
    def __init__(self):
        self.config = None

    def get_greeting(self):
        return self.config.get('app.greeting', 'Hello')


class GreetingService:
    def __init__(self):
        self.greeting_repository = None

    def greet(self, name):
        return f"{self.greeting_repository.get_greeting()}, {name}!"


class Application:
    def __init__(self):
        self.greeting_service = None

    def run(self):
        print(self.greeting_service.greet('World'))
        print(self.greeting_service.greet('Alt-Python'))
