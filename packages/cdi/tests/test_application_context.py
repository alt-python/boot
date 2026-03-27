"""Tests for ApplicationContext — basic lifecycle, get(), error cases."""

import pytest

from cdi import ApplicationContext, Context, Component, Singleton, Scopes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class SimpleClass:
    def __init__(self):
        self.value = 42


class WithInit:
    def __init__(self):
        self.inited = False

    def init(self):
        self.inited = True


# ---------------------------------------------------------------------------
# Constructor / parse_contexts
# ---------------------------------------------------------------------------

def test_empty_context_starts():
    """ApplicationContext with empty Context starts without error."""
    ctx = ApplicationContext(Context())
    ctx.start()
    # config and logger_factory should be registered automatically
    assert ctx.get("config") is not None


def test_accepts_context_list():
    """ApplicationContext accepts a list of Context objects."""
    ctx = ApplicationContext([Context([Component(SimpleClass)])])
    ctx.start()
    obj = ctx.get("simple_class")
    assert obj is not None
    assert obj.value == 42


def test_accepts_single_context():
    """ApplicationContext accepts a bare Context (not in a list)."""
    ctx = ApplicationContext(Context([Component(SimpleClass)]))
    ctx.start()
    obj = ctx.get("simple_class")
    assert isinstance(obj, SimpleClass)


def test_accepts_component_directly():
    """ApplicationContext accepts a bare Component."""
    ctx = ApplicationContext(Component(SimpleClass))
    ctx.start()
    obj = ctx.get("simple_class")
    assert isinstance(obj, SimpleClass)


def test_accepts_class_directly():
    """ApplicationContext accepts a raw class."""
    ctx = ApplicationContext(SimpleClass)
    ctx.start()
    obj = ctx.get("simple_class")
    assert isinstance(obj, SimpleClass)


def test_nullish_context_raises():
    """Passing None as a context element raises ValueError."""
    ctx = ApplicationContext([None])
    with pytest.raises(ValueError, match="nullish context"):
        ctx.start()


def test_duplicate_component_raises():
    """Registering the same component twice raises ValueError."""
    ctx = ApplicationContext(Context([Component(SimpleClass), Component(SimpleClass)]))
    with pytest.raises(ValueError, match="Duplicate definition"):
        ctx.start()


# ---------------------------------------------------------------------------
# get()
# ---------------------------------------------------------------------------

def test_get_singleton_returns_same_instance():
    """get() returns the same singleton instance on repeated calls."""
    ctx = ApplicationContext(Context([Singleton(SimpleClass)]))
    ctx.start()
    a = ctx.get("simple_class")
    b = ctx.get("simple_class")
    assert a is b


def test_get_missing_with_default():
    """get() returns the default when component is not found."""
    ctx = ApplicationContext(Context())
    ctx.start()
    result = ctx.get("nonexistent", "fallback")
    assert result == "fallback"


def test_get_missing_no_default_raises():
    """get() raises KeyError when component is not found and no default."""
    ctx = ApplicationContext(Context())
    ctx.start()
    with pytest.raises(KeyError, match="Failed component reference lookup"):
        ctx.get("nonexistent")


def test_get_none_default():
    """get() with default=None returns None for missing components."""
    ctx = ApplicationContext(Context())
    ctx.start()
    result = ctx.get("missing", None)
    assert result is None


# ---------------------------------------------------------------------------
# Lifecycle init() ordering
# ---------------------------------------------------------------------------

def test_init_called_during_start():
    """init() is called on singletons during start()."""
    ctx = ApplicationContext(Context([Singleton(WithInit)]))
    ctx.start()
    obj = ctx.get("with_init")
    assert obj.inited is True


# ---------------------------------------------------------------------------
# Infrastructure components
# ---------------------------------------------------------------------------

def test_config_auto_registered():
    """config singleton is always auto-registered."""
    ctx = ApplicationContext(Context())
    ctx.start()
    config = ctx.get("config")
    assert config is not None


def test_logger_factory_auto_registered():
    """logger_factory singleton is always auto-registered."""
    ctx = ApplicationContext(Context())
    ctx.start()
    lf = ctx.get("logger_factory")
    assert lf is not None


def test_run_false_skips_run_phase():
    """start(run=False) does not call start() on singletons."""
    class Server:
        def __init__(self):
            self.started = False

        def start(self):
            self.started = True

    ctx = ApplicationContext(Context([Singleton(Server)]))
    ctx.start(run=False)
    server = ctx.get("server")
    assert server.started is False


def test_run_true_calls_start_on_singletons():
    """start() (default run=True) calls start() on lifecycle singletons."""
    class Server:
        def __init__(self):
            self.started = False

        def start(self):
            self.started = True

    ctx = ApplicationContext(Context([Singleton(Server)]))
    ctx.start()
    server = ctx.get("server")
    assert server.started is True


def test_snake_case_name_derivation():
    """PascalCase class names are converted to snake_case component names."""
    class GreetingRepository:
        pass

    ctx = ApplicationContext(Context([Singleton(GreetingRepository)]))
    ctx.start()
    obj = ctx.get("greeting_repository")
    assert isinstance(obj, GreetingRepository)


def test_custom_name_used_verbatim():
    """Explicit 'name' on a component dict is converted to snake_case and used."""
    ctx = ApplicationContext(Context([Component({"reference": SimpleClass, "name": "MyCustomName"})]))
    ctx.start()
    # MyCustomName → my_custom_name
    obj = ctx.get("my_custom_name")
    assert isinstance(obj, SimpleClass)
