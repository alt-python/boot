"""Tests for all three injection modes defined in D002."""

import pytest

from cdi import ApplicationContext, Context, Component, Singleton, Property
from config import EphemeralConfig


# ---------------------------------------------------------------------------
# Mode 1: Null-property autowiring
# ---------------------------------------------------------------------------

class Repo:
    def __init__(self):
        self.value = "repo"


class ServiceWithNullDep:
    """Has a null attribute that should be autowired to 'repo' by name."""

    def __init__(self):
        self.repo = None  # will be autowired to Repo singleton


def test_null_property_autowired():
    """self.repo = None is autowired to the Repo singleton by name."""
    ctx = ApplicationContext(Context([
        Singleton(Repo),
        Singleton(ServiceWithNullDep),
    ]))
    ctx.start()
    svc = ctx.get("service_with_null_dep")
    assert svc.repo is not None
    assert isinstance(svc.repo, Repo)


def test_null_property_no_match_is_silent():
    """self.unknown = None stays None when no component named 'unknown' exists."""
    class WithUnknown:
        def __init__(self):
            self.unknown = None  # no matching component

    ctx = ApplicationContext(Context([Singleton(WithUnknown)]))
    ctx.start()
    obj = ctx.get("with_unknown")
    # should remain None, no exception raised
    assert obj.unknown is None


def test_non_null_attribute_not_overwritten():
    """Non-null attributes are not touched by autowiring."""
    class Stable:
        def __init__(self):
            self.value = "original"

    ctx = ApplicationContext(Context([Singleton(Stable)]))
    ctx.start()
    obj = ctx.get("stable")
    assert obj.value == "original"


# ---------------------------------------------------------------------------
# Mode 2: Placeholder resolution ${path:default}
# ---------------------------------------------------------------------------

class ConfigUser:
    def __init__(self):
        self.greeting = "${app.greeting:hello}"


def test_placeholder_resolved_from_config():
    """${path} is resolved against the config object."""
    cfg = EphemeralConfig({"app": {"greeting": "hi"}})
    ctx = ApplicationContext({"contexts": [Context([Singleton(ConfigUser)])], "config": cfg})
    ctx.start()
    obj = ctx.get("config_user")
    assert obj.greeting == "hi"


def test_placeholder_uses_default_when_missing():
    """${path:default} uses the default when the config path is absent."""
    cfg = EphemeralConfig({})
    ctx = ApplicationContext({"contexts": [Context([Singleton(ConfigUser)])], "config": cfg})
    ctx.start()
    obj = ctx.get("config_user")
    assert obj.greeting == "hello"


def test_placeholder_no_default_raises_on_missing():
    """${path} with no default raises KeyError when the path is not in config."""
    class Strict:
        def __init__(self):
            self.val = "${missing.path}"

    cfg = EphemeralConfig({})
    ctx = ApplicationContext({"contexts": [Context([Singleton(Strict)])], "config": cfg})
    with pytest.raises(KeyError):
        ctx.start()


# ---------------------------------------------------------------------------
# Mode 3: Explicit Property wiring
# ---------------------------------------------------------------------------

class SimpleValue:
    def __init__(self):
        self.attribute = None


def test_explicit_property_value():
    """Property(name, value=X) sets the attribute directly."""
    ctx = ApplicationContext(Context([
        Component({
            "reference": SimpleValue,
            "properties": [Property({"name": "attribute", "value": 99})],
        })
    ]))
    ctx.start()
    obj = ctx.get("simple_value")
    assert obj.attribute == 99


def test_explicit_property_reference():
    """Property(name, reference='repo') wires in the named component."""
    ctx = ApplicationContext(Context([
        Singleton(Repo),
        Component({
            "reference": SimpleValue,
            "properties": [Property({"name": "attribute", "reference": "repo"})],
        }),
    ]))
    ctx.start()
    obj = ctx.get("simple_value")
    assert isinstance(obj.attribute, Repo)


def test_explicit_property_path():
    """Property(name, path='some.key') reads from config."""
    cfg = EphemeralConfig({"some": {"key": 42}})
    ctx = ApplicationContext({
        "contexts": [Context([
            Component({
                "reference": SimpleValue,
                "properties": [Property({"name": "attribute", "path": "some.key"})],
            })
        ])],
        "config": cfg,
    })
    ctx.start()
    obj = ctx.get("simple_value")
    assert obj.attribute == 42


def test_explicit_property_path_with_default():
    """Property(name, path='x', default_value=7) falls back to 7."""
    cfg = EphemeralConfig({})
    ctx = ApplicationContext({
        "contexts": [Context([
            Component({
                "reference": SimpleValue,
                "properties": [
                    Property({"name": "attribute", "path": "missing.key", "default_value": 7})
                ],
            })
        ])],
        "config": cfg,
    })
    ctx.start()
    obj = ctx.get("simple_value")
    assert obj.attribute == 7


# ---------------------------------------------------------------------------
# Multiple injection modes together
# ---------------------------------------------------------------------------

class MultiWired:
    def __init__(self):
        self.repo = None                    # null-prop → Repo
        self.greeting = "${greet:default}"  # placeholder
        self.attribute = None               # will be set by explicit Property


def test_all_three_modes_together():
    """All three injection modes work correctly on the same component."""
    cfg = EphemeralConfig({"greet": "world"})
    ctx = ApplicationContext({
        "contexts": [Context([
            Singleton(Repo),
            Component({
                "reference": MultiWired,
                "properties": [Property({"name": "attribute", "value": "explicit"})],
            }),
        ])],
        "config": cfg,
    })
    ctx.start()
    obj = ctx.get("multi_wired")
    assert isinstance(obj.repo, Repo)
    assert obj.greeting == "world"
    assert obj.attribute == "explicit"
