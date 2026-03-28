import json
from handler import handler


def make_event(method, path, params=None, body=None):
    return {
        'version': '2.0',
        'routeKey': f'{method} {path}',
        'rawPath': path,
        'pathParameters': params or {},
        'queryStringParameters': {},
        'headers': {'content-type': 'application/json'},
        'body': json.dumps(body) if body else None,
        'isBase64Encoded': False,
    }


if __name__ == '__main__':
    for label, event in [
        ('GET /health', make_event('GET', '/health')),
        ('GET /greet/{name}', make_event('GET', '/greet/{name}', {'name': 'World'})),
        ('GET /missing', make_event('GET', '/missing')),
    ]:
        result = handler(event, {})
        body = json.loads(result['body']) if result['body'] else None
        print(f"{label} [{result['statusCode']}] {json.dumps(body)}")
