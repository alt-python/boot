import json
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request
from handler import handler


def make_request(method, path, body=None):
    kwargs = {'method': method, 'path': path}
    if body:
        kwargs['data'] = json.dumps(body)
        kwargs['content_type'] = 'application/json'
    env = EnvironBuilder(**kwargs).get_environ()
    return Request(env)


if __name__ == '__main__':
    for label, req in [
        ('GET /health', make_request('GET', '/health')),
        ('GET /greet/World', make_request('GET', '/greet/World')),
        ('GET /missing', make_request('GET', '/missing')),
    ]:
        resp = handler(req)
        body = json.loads(resp.get_data()) if resp.get_data() else None
        print(f"{label} [{resp.status_code}] {json.dumps(body)}")
