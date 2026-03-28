class GreetingController:
    __routes__ = [
        {'method': 'GET', 'path': '/health', 'handler': 'health'},
        {'method': 'GET', 'path': '/greet/{name}', 'handler': 'greet'},
    ]

    def __init__(self):
        self.greeting_service = None

    def health(self, req):
        return {'status': 'ok'}

    def greet(self, req):
        return {'message': self.greeting_service.greet(req['params']['name'])}
