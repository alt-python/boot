class GreetingService:
    def __init__(self):
        self.config = None
        self.greeting = '${app.greeting:Hello}'

    def greet(self, name):
        return f"{self.greeting}, {name}!"
