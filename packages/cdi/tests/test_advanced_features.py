"""Tests for profiles, depends_on, prototype scope, set_application_context,
lifecycle methods (init/run/start/destroy), and SIGINT handler registration."""

import os
import signal
import pytest

from cdi import ApplicationContext, Context, Component, Singleton, Prototype, Scopes


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------

def test_no_profile_always_active(monkeypatch):
    """Component with no profiles is active regardless of PY_ACTIVE_PROFILES."""
    monkeypatch.setenv("PY_ACTIVE_PROFILES", "prod")

    class Always:
        pass

    ctx = ApplicationContext(Context([Singleton(Always)]))
    ctx.start()
    assert ctx.get("always") is not None


def test_component_profile_matches_active(monkeypatch):
    """Component with profile='dev' is active when PY_ACTIVE_PROFILES=dev."""
    monkeypatch.setenv("PY_ACTIVE_PROFILES", "dev")

    DevBean = type("DevBean", (), {"__init__": lambda self: None})
    ctx = ApplicationContext(Context([
        Component({"reference": DevBean, "name": "DevBean", "profiles": "dev"})
    ]))
    ctx.start()
    obj = ctx.get("dev_bean")
    assert obj is not None


def test_component_profile_inactive_when_no_active(monkeypatch):
    """Component with profiles is inactive when PY_ACTIVE_PROFILES is empty."""
    monkeypatch.delenv("PY_ACTIVE_PROFILES", raising=False)

    class ProdOnly:
        pass

    ctx = ApplicationContext(Context([
        Component({"reference": ProdOnly, "profiles": "prod"})
    ]))
    ctx.start()
    with pytest.raises(KeyError, match="Failed component reference lookup"):
        ctx.get("prod_only")


def test_component_profile_inactive_different_active(monkeypatch):
    """Component with profile='prod' is inactive when PY_ACTIVE_PROFILES=dev."""
    monkeypatch.setenv("PY_ACTIVE_PROFILES", "dev")

    class ProdOnly:
        pass

    ctx = ApplicationContext(Context([
        Component({"reference": ProdOnly, "profiles": "prod"})
    ]))
    ctx.start()
    with pytest.raises(KeyError):
        ctx.get("prod_only")


def test_profile_negation_active_when_different(monkeypatch):
    """Component with profiles='!prod' is active when PY_ACTIVE_PROFILES=dev."""
    monkeypatch.setenv("PY_ACTIVE_PROFILES", "dev")

    class NotProd:
        pass

    ctx = ApplicationContext(Context([
        Component({"reference": NotProd, "profiles": "!prod"})
    ]))
    ctx.start()
    obj = ctx.get("not_prod")
    assert obj is not None


def test_profile_negation_inactive_when_matches(monkeypatch):
    """Component with profiles='!prod' is inactive when PY_ACTIVE_PROFILES=prod."""
    monkeypatch.setenv("PY_ACTIVE_PROFILES", "prod")

    class NotProd:
        pass

    ctx = ApplicationContext(Context([
        Component({"reference": NotProd, "profiles": "!prod"})
    ]))
    ctx.start()
    with pytest.raises(KeyError):
        ctx.get("not_prod")


def test_profiles_from_options_dict(monkeypatch):
    """profiles key in options dict overrides PY_ACTIVE_PROFILES."""
    monkeypatch.delenv("PY_ACTIVE_PROFILES", raising=False)

    class DevBean:
        pass

    ctx = ApplicationContext({
        "contexts": [Context([Component({"reference": DevBean, "profiles": "dev"})])],
        "profiles": "dev",
    })
    ctx.start()
    assert ctx.get("dev_bean") is not None


# ---------------------------------------------------------------------------
# depends_on topological ordering
# ---------------------------------------------------------------------------

def test_depends_on_controls_init_order():
    """depends_on ensures First.init() is called before Second.init()."""
    order = []

    class First:
        def init(self):
            order.append("first")

    class Second:
        def init(self):
            order.append("second")

    ctx = ApplicationContext(Context([
        Component({"reference": Second, "name": "Second", "depends_on": ["first"]}),
        Component({"reference": First, "name": "First"}),
    ]))
    ctx.start(run=False)
    assert order.index("first") < order.index("second")


def test_depends_on_as_string():
    """depends_on='first' (string, not list) is normalised to ['first']."""
    order = []

    class A:
        def init(self):
            order.append("a")

    class B:
        def init(self):
            order.append("b")

    ctx = ApplicationContext(Context([
        Component({"reference": B, "name": "B", "depends_on": "a"}),
        Component({"reference": A, "name": "A"}),
    ]))
    ctx.start(run=False)
    assert order.index("a") < order.index("b")


def test_depends_on_missing_dep_raises():
    """depends_on referencing non-existent component raises ValueError."""
    class Lonely:
        pass

    ctx = ApplicationContext(Context([
        Component({"reference": Lonely, "name": "Lonely", "depends_on": ["ghost"]})
    ]))
    with pytest.raises((ValueError, KeyError)):
        ctx.start(run=False)


def test_circular_depends_on_raises():
    """Circular depends_on raises RuntimeError."""
    class P:
        pass

    class Q:
        pass

    ctx = ApplicationContext(Context([
        Component({"reference": P, "name": "P", "depends_on": ["q"]}),
        Component({"reference": Q, "name": "Q", "depends_on": ["p"]}),
    ]))
    with pytest.raises(RuntimeError, match="Circular"):
        ctx.start(run=False)


# ---------------------------------------------------------------------------
# Prototype scope
# ---------------------------------------------------------------------------

def test_prototype_new_instance_per_get():
    """Prototype scope returns a new instance on every get() call."""
    import uuid as _uuid

    class Proto:
        def __init__(self):
            self.uid = str(_uuid.uuid4())

    ctx = ApplicationContext(Context([Prototype(Proto)]))
    ctx.start()
    a = ctx.get("proto")
    b = ctx.get("proto")
    assert a is not b
    assert a.uid != b.uid


def test_prototype_not_stored_in_registry():
    """Prototype instances are not stored in the component registry."""
    class Proto:
        pass

    ctx = ApplicationContext(Context([Prototype(Proto)]))
    ctx.start()
    _ = ctx.get("proto")
    assert ctx.components["proto"]["instance"] is None


# ---------------------------------------------------------------------------
# set_application_context callback (aware interface)
# ---------------------------------------------------------------------------

def test_set_application_context_called():
    """set_application_context(ctx) is invoked on singletons that implement it."""
    class Aware:
        def __init__(self):
            self.app_ctx = None

        def set_application_context(self, ctx):
            self.app_ctx = ctx

    ctx = ApplicationContext(Context([Singleton(Aware)]))
    ctx.start()
    obj = ctx.get("aware")
    assert obj.app_ctx is ctx


# ---------------------------------------------------------------------------
# Lifecycle methods: init / run / start / destroy
# ---------------------------------------------------------------------------

def test_init_called_before_start():
    """init() is called during initialise_singletons, before start() in run phase."""
    calls = []

    class Ordered:
        def init(self):
            calls.append("init")

        def start(self):
            calls.append("start")

    ctx = ApplicationContext(Context([Singleton(Ordered)]))
    ctx.start()
    assert calls.index("init") < calls.index("start")


def test_run_called_during_run_phase():
    """run() is called during the run phase."""
    called = []

    class Runner:
        def run(self):
            called.append("run")

    ctx = ApplicationContext(Context([Singleton(Runner)]))
    ctx.start()
    assert "run" in called


def test_start_not_called_when_run_false():
    """start() on component is skipped when run=False."""
    started = []

    class Server:
        def start(self):
            started.append(True)

    ctx = ApplicationContext(Context([Singleton(Server)]))
    ctx.start(run=False)
    assert not started


def test_run_false_dict_form():
    """start({'run': False}) also skips the run phase."""
    started = []

    class Server:
        def start(self):
            started.append(True)

    ctx = ApplicationContext(Context([Singleton(Server)]))
    ctx.start({"run": False})
    assert not started


# ---------------------------------------------------------------------------
# SIGINT handler registration
# ---------------------------------------------------------------------------

def test_sigint_handler_registered():
    """register_singleton_destroyers installs a SIGINT handler."""
    class Stoppable:
        def destroy(self):
            pass

    orig = signal.getsignal(signal.SIGINT)
    try:
        ctx = ApplicationContext(Context([Singleton(Stoppable)]))
        ctx.start(run=False)
        new_handler = signal.getsignal(signal.SIGINT)
        # A new combined handler should have been installed
        assert new_handler is not orig
    finally:
        signal.signal(signal.SIGINT, orig)


def test_sigint_handler_calls_destroy():
    """Sending SIGINT (simulated) triggers the destroyer."""
    destroyed = []

    class Killable:
        def destroy(self):
            destroyed.append(True)

    orig = signal.getsignal(signal.SIGINT)
    try:
        ctx = ApplicationContext(Context([Singleton(Killable)]))
        ctx.start(run=False)
        handler = signal.getsignal(signal.SIGINT)
        if callable(handler):
            try:
                handler(signal.SIGINT, None)
            except (SystemExit, KeyboardInterrupt):
                pass
    finally:
        signal.signal(signal.SIGINT, orig)
    assert destroyed == [True]
