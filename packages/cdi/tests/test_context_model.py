"""Tests for the CDI context model types (T01).

Covers: Component, Singleton, Prototype, Property, Context, Scopes —
construction, attribute defaults, normalisation, and scope constants.
"""

import pytest

from cdi import Component, Context, Property, Prototype, Scopes, Singleton


# ---------------------------------------------------------------------------
# Scopes
# ---------------------------------------------------------------------------

class TestScopes:
    def test_singleton_constant(self):
        assert Scopes.SINGLETON == "singleton"

    def test_prototype_constant(self):
        assert Scopes.PROTOTYPE == "prototype"


# ---------------------------------------------------------------------------
# Component
# ---------------------------------------------------------------------------

class SampleClass:
    pass


class TestComponent:
    def test_accepts_class_directly(self):
        c = Component(SampleClass)
        assert c.reference is SampleClass

    def test_accepts_dict_with_reference(self):
        c = Component({"reference": SampleClass, "name": "sample"})
        assert c.reference is SampleClass
        assert c.name == "sample"

    def test_defaults(self):
        c = Component(SampleClass)
        assert c.name is None
        assert c.qualifier is None
        assert c.scope is None
        assert c.properties is None
        assert c.profiles is None
        assert c.primary is None
        assert c.factory is None
        assert c.factory_function is None
        assert c.factory_args is None
        assert c.wire_factory is None
        assert c.constructor_args is None
        assert c.depends_on is None
        assert c.is_active is True
        assert c.instance is None
        assert c.is_class is False

    def test_factory_function_camel_snake(self):
        c = Component({"factory": "some_factory", "factoryFunction": "get_bean"})
        assert c.factory == "some_factory"
        assert c.factory_function == "get_bean"

    def test_factory_function_snake(self):
        c = Component({"factory": "some_factory", "factory_function": "get_bean"})
        assert c.factory_function == "get_bean"

    def test_depends_on_camel_snake(self):
        c = Component({"reference": SampleClass, "dependsOn": ["other"]})
        assert c.depends_on == ["other"]

    def test_depends_on_snake(self):
        c = Component({"reference": SampleClass, "depends_on": "other"})
        assert c.depends_on == "other"

    def test_constructor_args(self):
        c = Component({"reference": SampleClass, "constructor_args": {"x": 1}})
        assert c.constructor_args == {"x": 1}


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_accepts_class(self):
        s = Singleton(SampleClass)
        assert s.reference is SampleClass
        assert s.scope == Scopes.SINGLETON

    def test_accepts_dict_with_reference(self):
        s = Singleton({"reference": SampleClass, "name": "my_sample"})
        assert s.reference is SampleClass
        assert s.scope == Scopes.SINGLETON
        assert s.name == "my_sample"

    def test_accepts_dict_with_factory(self):
        s = Singleton({"factory": "logger_factory", "factory_function": "get_logger"})
        assert s.factory == "logger_factory"
        assert s.scope == Scopes.SINGLETON

    def test_accepts_dict_with_wire_factory(self):
        s = Singleton({"wire_factory": "logger_factory", "factory_function": "get_logger"})
        assert s.wire_factory == "logger_factory"
        assert s.scope == Scopes.SINGLETON

    def test_is_subclass_of_component(self):
        assert isinstance(Singleton(SampleClass), Component)


# ---------------------------------------------------------------------------
# Prototype
# ---------------------------------------------------------------------------

class TestPrototype:
    def test_accepts_class(self):
        p = Prototype(SampleClass)
        assert p.reference is SampleClass
        assert p.scope == Scopes.PROTOTYPE

    def test_accepts_dict_with_reference(self):
        p = Prototype({"reference": SampleClass})
        assert p.scope == Scopes.PROTOTYPE

    def test_accepts_dict_with_wire_factory(self):
        p = Prototype({"wire_factory": "logger_factory", "factory_function": "get_logger"})
        assert p.wire_factory == "logger_factory"
        assert p.scope == Scopes.PROTOTYPE

    def test_is_subclass_of_component(self):
        assert isinstance(Prototype(SampleClass), Component)


# ---------------------------------------------------------------------------
# Property
# ---------------------------------------------------------------------------

class TestProperty:
    def test_basic_construction(self):
        prop = Property({"name": "db_url", "value": "sqlite://:memory:"})
        assert prop.name == "db_url"
        assert prop.value == "sqlite://:memory:"

    def test_reference_aliases(self):
        prop = Property({"name": "repo", "ref": "my_repo"})
        assert prop.reference == "my_repo"

        prop2 = Property({"name": "repo2", "reference": "other_repo"})
        assert prop2.reference == "other_repo"

    def test_path_and_default(self):
        prop = Property({"name": "timeout", "path": "app.timeout", "default_value": 30})
        assert prop.path == "app.timeout"
        assert prop.default_value == 30

    def test_default_value_camel(self):
        prop = Property({"name": "x", "defaultValue": 99})
        assert prop.default_value == 99

    def test_defaults_are_none(self):
        prop = Property({"name": "x"})
        assert prop.reference is None
        assert prop.value is None
        assert prop.path is None
        assert prop.default_value is None


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------

class TestContext:
    def test_empty_construction(self):
        ctx = Context()
        assert ctx.components == []

    def test_single_component_normalised_to_list(self):
        s = Singleton(SampleClass)
        ctx = Context(s)
        assert ctx.components == [s]

    def test_list_of_components(self):
        a = Singleton(SampleClass)
        b = Prototype(SampleClass)
        ctx = Context([a, b])
        assert len(ctx.components) == 2

    def test_profile(self):
        ctx = Context([], profile="dev")
        assert ctx.profile == "dev"

    def test_none_components_default_to_empty_list(self):
        ctx = Context(None)
        assert ctx.components == []
