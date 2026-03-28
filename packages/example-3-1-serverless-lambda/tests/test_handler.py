"""Tests for example-3-1-serverless-lambda (AWS Lambda warm-start pattern)."""
import json
import sys
import os

# ---------------------------------------------------------------------------
# Isolation: evict generic flat-module names and prepend this package's root
# so that 'from handler import handler' resolves to this package's handler.py.
# This is required when all three serverless example packages are tested in
# the same pytest run — they all have handler.py / controllers.py / services.py.
# ---------------------------------------------------------------------------
_PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _m in ('handler', 'controllers', 'services'):
    sys.modules.pop(_m, None)
if _PKG not in sys.path:
    sys.path.insert(0, _PKG)

from handler import handler  # noqa: E402 — must follow sys.path setup

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_health_returns_200():
    result = handler(make_event('GET', '/health'), {})
    assert result['statusCode'] == 200
    assert json.loads(result['body']) == {'status': 'ok'}


def test_greet_returns_message():
    result = handler(make_event('GET', '/greet/{name}', {'name': 'World'}), {})
    assert result['statusCode'] == 200
    assert 'World' in json.loads(result['body'])['message']


def test_missing_route_returns_404():
    result = handler(make_event('GET', '/missing'), {})
    assert result['statusCode'] == 404


def test_post_not_registered_returns_404():
    result = handler(make_event('POST', '/health'), {})
    assert result['statusCode'] == 404


def test_warm_start_reuses_context():
    r1 = handler(make_event('GET', '/health'), {})
    r2 = handler(make_event('GET', '/health'), {})
    assert r1['statusCode'] == r2['statusCode'] == 200
