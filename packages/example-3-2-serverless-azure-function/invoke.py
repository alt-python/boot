import json
import azure.functions as func
from handler import handler


def make_request(method, url, params=None, body=None):
    return func.HttpRequest(
        method=method,
        url=f'http://localhost:7071/api{url}',
        route_params=params or {},
        headers={'Content-Type': 'application/json'},
        params={},
        body=json.dumps(body).encode() if body else b'',
    )


if __name__ == '__main__':
    for label, req in [
        ('GET /health', make_request('GET', '/health')),
        ('GET /greet/World', make_request('GET', '/greet/World', {'name': 'World'})),
        ('GET /missing', make_request('GET', '/missing')),
    ]:
        resp = handler(req)
        body = json.loads(resp.get_body()) if resp.get_body() else None
        print(f"{label} [{resp.status_code}] {json.dumps(body)}")
