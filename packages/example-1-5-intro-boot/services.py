"""
example-1-5-intro-boot — service classes

Same structure as example-1-3-intro-cdi but bootstrapped via Boot.boot()
instead of ApplicationContext directly. Boot.boot() injects the config
singleton automatically so GreetingRepository.config is wired by CDI.
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
