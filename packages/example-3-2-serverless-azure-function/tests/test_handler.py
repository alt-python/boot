"""Tests for example-3-2-serverless-azure-function (Azure Function warm-start pattern)."""
import json
import sys
import os

# ---------------------------------------------------------------------------
# Isolation: evict generic flat-module names and prepend this package's root.
# ---------------------------------------------------------------------------
_PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _m in ('handler', 'controllers', 'services'):
    sys.modules.pop(_m, None)
if _PKG not in sys.path:
    sys.path.insert(0, _PKG)

import azure.functions as func  # noqa: E402
from handler import handler  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_request(method, url_path, params=None, body=None):
    return func.HttpRequest(
        method=method,
        url=f'http://localhost:7071{url_path}',
        route_params=params or {},
        headers={'Content-Type': 'application/json'},
        params={},
        body=json.dumps(body).encode() if body else b'',
    )

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_health_returns_200():
    resp = handler(make_request('GET', '/health'))
    assert resp.status_code == 200
    assert json.loads(resp.get_body()) == {'status': 'ok'}


def test_greet_returns_message():
    resp = handler(make_request('GET', '/greet/World', {'name': 'World'}))
    assert resp.status_code == 200
    assert 'World' in json.loads(resp.get_body())['message']


def test_missing_route_returns_404():
    resp = handler(make_request('GET', '/missing'))
    assert resp.status_code == 404


def test_post_not_registered_returns_404():
    resp = handler(make_request('POST', '/health'))
    assert resp.status_code == 404


def test_warm_start_reuses_context():
    r1 = handler(make_request('GET', '/health'))
    r2 = handler(make_request('GET', '/health'))
    assert r1.status_code == r2.status_code == 200
