"""
tests/test_config_core.py — tests for EphemeralConfig, PropertySourceChain,
EnvPropertySource, PropertiesParser, and ProfileConfigLoader.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from config.ephemeral_config import EphemeralConfig
from config.property_source_chain import PropertySourceChain
from config.env_property_source import EnvPropertySource
from config.properties_parser import PropertiesParser
from config.profile_config_loader import ProfileConfigLoader


# ---------------------------------------------------------------------------
# EphemeralConfig
# ---------------------------------------------------------------------------

class TestEphemeralConfig:
    def test_get_flat_key(self):
        c = EphemeralConfig({"foo": "bar"})
        assert c.get("foo") == "bar"

    def test_get_dotted_path(self):
        c = EphemeralConfig({"a": {"b": {"c": 42}}})
        assert c.get("a.b.c") == 42

    def test_get_falsy_values(self):
        c = EphemeralConfig({"x": 0, "y": False, "z": ""})
        assert c.get("x") == 0
        assert c.get("y") is False
        assert c.get("z") == ""

    def test_get_default_when_missing(self):
        c = EphemeralConfig({})
        assert c.get("missing", "default") == "default"

    def test_get_raises_when_missing_and_no_default(self):
        c = EphemeralConfig({})
        with pytest.raises(KeyError):
            c.get("missing")

    def test_has_existing(self):
        c = EphemeralConfig({"a": {"b": 1}})
        assert c.has("a.b") is True

    def test_has_missing(self):
        c = EphemeralConfig({"a": 1})
        assert c.has("a.b") is False

    def test_get_none_value_via_has(self):
        # A key explicitly set to None is "has" but returns None
        c = EphemeralConfig({"x": None})
        assert c.has("x") is True
        assert c.get("x") is None

    def test_flat_key_with_dot_in_name(self):
        # Flat dict key containing a dot is accessible directly
        c = EphemeralConfig({"a.b": "flat"})
        assert c.get("a.b") == "flat"


# ---------------------------------------------------------------------------
# PropertySourceChain
# ---------------------------------------------------------------------------

class TestPropertySourceChain:
    def test_first_source_wins(self):
        s1 = EphemeralConfig({"key": "high"})
        s2 = EphemeralConfig({"key": "low"})
        chain = PropertySourceChain([s1, s2])
        assert chain.get("key") == "high"

    def test_falls_through_to_second(self):
        s1 = EphemeralConfig({"other": "x"})
        s2 = EphemeralConfig({"key": "found"})
        chain = PropertySourceChain([s1, s2])
        assert chain.get("key") == "found"

    def test_default_when_nothing(self):
        chain = PropertySourceChain([EphemeralConfig({})])
        assert chain.get("missing", "def") == "def"

    def test_raises_when_missing(self):
        chain = PropertySourceChain([EphemeralConfig({})])
        with pytest.raises(KeyError):
            chain.get("missing")

    def test_add_source_at_priority(self):
        chain = PropertySourceChain([EphemeralConfig({"k": "low"})])
        chain.add_source(EphemeralConfig({"k": "high"}), priority=0)
        assert chain.get("k") == "high"

    def test_has(self):
        chain = PropertySourceChain([EphemeralConfig({"a": 1})])
        assert chain.has("a") is True
        assert chain.has("b") is False


# ---------------------------------------------------------------------------
# EnvPropertySource
# ---------------------------------------------------------------------------

class TestEnvPropertySource:
    def test_direct_key(self):
        s = EnvPropertySource({"MY_VAR": "hello"})
        assert s.has("MY_VAR") is True
        assert s.get("MY_VAR") == "hello"

    def test_relaxed_binding_upper_to_dots(self):
        s = EnvPropertySource({"MY_APP_PORT": "8080"})
        assert s.has("my.app.port") is True
        assert s.get("my.app.port") == "8080"

    def test_double_underscore_becomes_dot(self):
        s = EnvPropertySource({"APP__NAME": "myapp"})
        assert s.has("app.name") is True
        assert s.get("app.name") == "myapp"

    def test_missing_returns_none(self):
        s = EnvPropertySource({})
        assert s.has("nope") is False
        assert s.get("nope") is None

    def test_default_value(self):
        s = EnvPropertySource({})
        assert s.get("nope", "fallback") == "fallback"


# ---------------------------------------------------------------------------
# PropertiesParser
# ---------------------------------------------------------------------------

class TestPropertiesParser:
    def test_basic_key_value(self):
        result = PropertiesParser.parse("foo=bar\nbaz=qux\n")
        assert result == {"foo": "bar", "baz": "qux"}

    def test_colon_separator(self):
        result = PropertiesParser.parse("key: value\n")
        assert result["key"] == "value"

    def test_comment_lines_skipped(self):
        result = PropertiesParser.parse("# comment\n! also comment\nkey=val\n")
        assert result == {"key": "val"}

    def test_blank_lines_skipped(self):
        result = PropertiesParser.parse("\n\nkey=val\n\n")
        assert result == {"key": "val"}

    def test_dotted_key_nested(self):
        result = PropertiesParser.parse("a.b.c=1\n")
        assert result == {"a": {"b": {"c": "1"}}}

    def test_array_notation(self):
        result = PropertiesParser.parse("a.b[0]=x\na.b[1]=y\n")
        assert result == {"a": {"b": ["x", "y"]}}

    def test_array_of_objects(self):
        result = PropertiesParser.parse("a.b[0].x=1\na.b[0].y=2\n")
        assert result == {"a": {"b": [{"x": "1", "y": "2"}]}}

    def test_unicode_escape(self):
        result = PropertiesParser.parse("key=caf\\u00e9\n")
        assert result["key"] == "café"

    def test_line_continuation(self):
        result = PropertiesParser.parse("key=hel\\\n    lo\n")
        assert result["key"] == "hello"

    def test_escape_sequences(self):
        result = PropertiesParser.parse("key=line1\\nline2\n")
        assert result["key"] == "line1\nline2"

    def test_app_name(self):
        result = PropertiesParser.parse("app.name=Config Example\n")
        assert result["app"]["name"] == "Config Example"


# ---------------------------------------------------------------------------
# ProfileConfigLoader
# ---------------------------------------------------------------------------

class TestProfileConfigLoader:
    def test_loads_json_file(self, tmp_path):
        (tmp_path / "application.json").write_text('{"greeting": "Hello"}')
        chain = ProfileConfigLoader.load(base_path=str(tmp_path))
        assert chain.get("greeting") == "Hello"

    def test_loads_properties_file(self, tmp_path):
        (tmp_path / "application.properties").write_text("app.name=MyApp\n")
        chain = ProfileConfigLoader.load(base_path=str(tmp_path))
        assert chain.get("app.name") == "MyApp"

    def test_loads_yaml_file(self, tmp_path):
        (tmp_path / "application.yaml").write_text("server:\n  port: 8080\n")
        chain = ProfileConfigLoader.load(base_path=str(tmp_path))
        assert chain.get("server.port") == 8080

    def test_profile_overlay_overrides_default(self, tmp_path):
        (tmp_path / "application.json").write_text('{"port": 8080}')
        (tmp_path / "application-dev.json").write_text('{"port": 9090}')
        chain = ProfileConfigLoader.load(
            base_path=str(tmp_path), profiles="dev"
        )
        assert chain.get("port") == 9090

    def test_default_used_when_no_profile_match(self, tmp_path):
        (tmp_path / "application.json").write_text('{"port": 8080}')
        chain = ProfileConfigLoader.load(base_path=str(tmp_path))
        assert chain.get("port") == 8080

    def test_overrides_highest_priority(self, tmp_path):
        (tmp_path / "application.json").write_text('{"port": 8080}')
        chain = ProfileConfigLoader.load(
            base_path=str(tmp_path), overrides={"port": 1234}
        )
        assert chain.get("port") == 1234

    def test_env_binding_higher_than_files(self, tmp_path):
        (tmp_path / "application.json").write_text('{"server": {"port": 8080}}')
        env = {"SERVER_PORT": "9999"}
        chain = ProfileConfigLoader.load(base_path=str(tmp_path), env=env)
        assert chain.get("server.port") == "9999"

    def test_fallback_lowest_priority(self, tmp_path):
        chain = ProfileConfigLoader.load(
            base_path=str(tmp_path),
            fallback={"fallback_key": "fb"},
        )
        assert chain.get("fallback_key") == "fb"

    def test_config_dir_takes_priority_over_cwd(self, tmp_path):
        (tmp_path / "application.json").write_text('{"key": "cwd"}')
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "application.json").write_text('{"key": "config-dir"}')
        chain = ProfileConfigLoader.load(base_path=str(tmp_path))
        # config/ file found first in SEARCH_DIRS
        assert chain.get("key") == "config-dir"

    def test_missing_key_raises(self, tmp_path):
        chain = ProfileConfigLoader.load(base_path=str(tmp_path))
        with pytest.raises(KeyError):
            chain.get("definitely.missing")

    def test_missing_key_default(self, tmp_path):
        chain = ProfileConfigLoader.load(base_path=str(tmp_path))
        assert chain.get("missing", "default") == "default"

    def test_py_active_profiles_env_var(self, tmp_path):
        """PY_ACTIVE_PROFILES is the Python-side env var for profile activation."""
        (tmp_path / "application.json").write_text('{"port": 8080}')
        (tmp_path / "application-dev.json").write_text('{"port": 9090}')
        env = {"PY_ACTIVE_PROFILES": "dev"}
        chain = ProfileConfigLoader.load(base_path=str(tmp_path), env=env)
        assert chain.get("port") == 9090
