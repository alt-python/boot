"""
tests/test_config_resolvers.py — tests for the resolver chain, ValueResolvingConfig,
JasyptDecryptor, PlaceholderResolver, and ConfigFactory.
"""

from __future__ import annotations

import pytest

from config.ephemeral_config import EphemeralConfig
from config.selector import PrefixSelector, ParenthesisSelector, PlaceholderSelector
from config.resolver import DelegatingResolver
from config.placeholder_resolver import PlaceholderResolver
from config.jasypt_decryptor import JasyptDecryptor
from config.value_resolving_config import ValueResolvingConfig
from config.config_factory import ConfigFactory
from config.profile_config_loader import ProfileConfigLoader
from pysypt import Jasypt


# ---------------------------------------------------------------------------
# Selector
# ---------------------------------------------------------------------------

class TestSelectors:
    def test_prefix_selector_matches(self):
        sel = PrefixSelector("enc.")
        assert sel.matches("enc.abcdef") is True
        assert sel.matches("other") is False

    def test_prefix_selector_resolve_value(self):
        sel = PrefixSelector("enc.")
        assert sel.resolve_value("enc.ciphertext") == "ciphertext"

    def test_parenthesis_selector_matches(self):
        sel = ParenthesisSelector("ENC")
        assert sel.matches("ENC(ciphertext)") is True
        assert sel.matches("enc.ciphertext") is False
        assert sel.matches("ENC(text") is False

    def test_parenthesis_selector_case_insensitive(self):
        sel = ParenthesisSelector("ENC")
        assert sel.matches("enc(ciphertext)") is True

    def test_parenthesis_selector_resolve_value(self):
        sel = ParenthesisSelector("ENC")
        assert sel.resolve_value("ENC(ciphertext)") == "ciphertext"

    def test_placeholder_selector_matches(self):
        sel = PlaceholderSelector()
        assert sel.matches("${my.key}") is True
        assert sel.matches("prefix ${key} suffix") is True
        assert sel.matches("plain text") is False


# ---------------------------------------------------------------------------
# PlaceholderResolver
# ---------------------------------------------------------------------------

class TestPlaceholderResolver:
    def test_resolves_single_placeholder(self):
        ref = EphemeralConfig({"name": "World"})
        resolver = PlaceholderResolver(reference=ref)
        result = resolver.resolve({"msg": "Hello ${name}"})
        assert result["msg"] == "Hello World"

    def test_resolves_multiple_placeholders(self):
        ref = EphemeralConfig({"a": "foo", "b": "bar"})
        resolver = PlaceholderResolver(reference=ref)
        result = resolver.resolve({"msg": "${a} and ${b}"})
        assert result["msg"] == "foo and bar"

    def test_leaves_non_placeholder_values_unchanged(self):
        ref = EphemeralConfig({})
        resolver = PlaceholderResolver(reference=ref)
        result = resolver.resolve({"key": "plain"})
        assert result["key"] == "plain"

    def test_placeholder_with_default(self):
        ref = EphemeralConfig({})
        resolver = PlaceholderResolver(reference=ref)
        result = resolver.resolve({"key": "${missing:fallback}"})
        assert result["key"] == "fallback"

    def test_unresolvable_placeholder_returns_original(self):
        ref = EphemeralConfig({})
        resolver = PlaceholderResolver(reference=ref)
        result = resolver.resolve({"key": "${nope}"})
        # Can't resolve — returns original
        assert result["key"] == "${nope}"

    def test_resolves_nested_dict(self):
        ref = EphemeralConfig({"port": "8080"})
        resolver = PlaceholderResolver(reference=ref)
        result = resolver.resolve({"server": {"url": "http://host:${port}"}})
        assert result["server"]["url"] == "http://host:8080"


# ---------------------------------------------------------------------------
# JasyptDecryptor
# ---------------------------------------------------------------------------

PASSWORD = "G0CvDz7oJn60"


def _make_encrypted(message: str) -> str:
    return Jasypt().encrypt(message, PASSWORD)


class TestJasyptDecryptor:
    def test_decrypts_enc_prefix(self):
        ciphertext = _make_encrypted("secret")
        decryptor = JasyptDecryptor(PrefixSelector("enc."), PASSWORD)
        result = decryptor.resolve({"key": f"enc.{ciphertext}"})
        assert result["key"] == "secret"

    def test_decrypts_enc_parenthesis(self):
        ciphertext = _make_encrypted("secret")
        decryptor = JasyptDecryptor(ParenthesisSelector("ENC"), PASSWORD)
        result = decryptor.resolve({"key": f"ENC({ciphertext})"})
        assert result["key"] == "secret"

    def test_leaves_unmatched_values_unchanged(self):
        decryptor = JasyptDecryptor(PrefixSelector("enc."), PASSWORD)
        result = decryptor.resolve({"key": "plaintext"})
        assert result["key"] == "plaintext"

    def test_bad_ciphertext_returns_original(self):
        decryptor = JasyptDecryptor(PrefixSelector("enc."), PASSWORD)
        result = decryptor.resolve({"key": "enc.not-base64!!!"})
        assert result["key"] == "enc.not-base64!!!"

    def test_nested_dict(self):
        ciphertext = _make_encrypted("mysecret")
        decryptor = JasyptDecryptor(ParenthesisSelector("ENC"), PASSWORD)
        result = decryptor.resolve({"db": {"password": f"ENC({ciphertext})"}})
        assert result["db"]["password"] == "mysecret"

    def test_password_from_env(self, monkeypatch):
        """PY_CONFIG_PASSPHRASE env var drives the decryption password."""
        monkeypatch.setenv("PY_CONFIG_PASSPHRASE", PASSWORD)
        ciphertext = _make_encrypted("envpass")
        # No explicit password — reads from env
        decryptor = JasyptDecryptor(ParenthesisSelector("ENC"))
        result = decryptor.resolve({"key": f"ENC({ciphertext})"})
        assert result["key"] == "envpass"


# ---------------------------------------------------------------------------
# ValueResolvingConfig
# ---------------------------------------------------------------------------

class TestValueResolvingConfig:
    def test_get_resolved_value(self):
        backing = EphemeralConfig({"key": "value"})
        resolver = DelegatingResolver([])
        vrc = ValueResolvingConfig(backing, resolver)
        assert vrc.get("key") == "value"

    def test_get_with_default(self):
        backing = EphemeralConfig({})
        resolver = DelegatingResolver([])
        vrc = ValueResolvingConfig(backing, resolver)
        assert vrc.get("missing", "default") == "default"

    def test_has_delegates_to_backing(self):
        backing = EphemeralConfig({"x": 1})
        resolver = DelegatingResolver([])
        vrc = ValueResolvingConfig(backing, resolver)
        assert vrc.has("x") is True
        assert vrc.has("y") is False

    def test_resolves_placeholder_on_get(self):
        backing = EphemeralConfig({"name": "World", "greeting": "Hello ${name}"})
        placeholder = PlaceholderResolver()
        resolver = DelegatingResolver([placeholder])
        vrc = ValueResolvingConfig(backing, resolver)
        placeholder.reference = vrc
        assert vrc.get("greeting") == "Hello World"


# ---------------------------------------------------------------------------
# ConfigFactory integration
# ---------------------------------------------------------------------------

class TestConfigFactory:
    def test_get_config_returns_value_resolving_config(self, tmp_path):
        (tmp_path / "application.json").write_text('{"app": {"name": "TestApp"}}')
        backing = ProfileConfigLoader.load(base_path=str(tmp_path))
        cfg = ConfigFactory.get_config(config=backing)
        assert cfg.get("app.name") == "TestApp"

    def test_enc_parenthesis_decrypted(self, tmp_path):
        ciphertext = _make_encrypted("topsecret")
        (tmp_path / "application.json").write_text(
            f'{{"app": {{"secret": "ENC({ciphertext})"}}}}'
        )
        backing = ProfileConfigLoader.load(base_path=str(tmp_path))
        cfg = ConfigFactory.get_config(config=backing, password=PASSWORD)
        assert cfg.get("app.secret") == "topsecret"

    def test_enc_prefix_decrypted(self, tmp_path):
        ciphertext = _make_encrypted("topsecret")
        (tmp_path / "application.properties").write_text(
            f"app.secret=enc.{ciphertext}\n"
        )
        backing = ProfileConfigLoader.load(base_path=str(tmp_path))
        cfg = ConfigFactory.get_config(config=backing, password=PASSWORD)
        assert cfg.get("app.secret") == "topsecret"

    def test_placeholder_resolved(self, tmp_path):
        (tmp_path / "application.json").write_text(
            '{"base": "http://localhost", "url": "${base}/api"}'
        )
        backing = ProfileConfigLoader.load(base_path=str(tmp_path))
        cfg = ConfigFactory.get_config(config=backing)
        assert cfg.get("url") == "http://localhost/api"

    def test_default_value(self, tmp_path):
        cfg = ConfigFactory.get_config(
            config=ProfileConfigLoader.load(base_path=str(tmp_path))
        )
        assert cfg.get("nope", "fallback") == "fallback"

    def test_py_config_passphrase_env(self, tmp_path, monkeypatch):
        """PY_CONFIG_PASSPHRASE is the Python-side env var for decryption."""
        monkeypatch.setenv("PY_CONFIG_PASSPHRASE", PASSWORD)
        ciphertext = _make_encrypted("from-env")
        (tmp_path / "application.json").write_text(
            f'{{"secret": "ENC({ciphertext})"}}'
        )
        backing = ProfileConfigLoader.load(base_path=str(tmp_path))
        cfg = ConfigFactory.get_config(config=backing)  # no explicit password
        assert cfg.get("secret") == "from-env"
