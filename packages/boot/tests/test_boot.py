"""
tests/test_boot.py — pytest test suite for Boot class and print_banner.
"""

from __future__ import annotations

import pytest
import boot.boot as _boot_module

from boot import Boot, print_banner
from config.ephemeral_config import EphemeralConfig


@pytest.fixture(autouse=True)
def clear_root():
    _boot_module._root.clear()
    yield
    _boot_module._root.clear()


# ---------------------------------------------------------------------------
# 1. detect_config defaults
# ---------------------------------------------------------------------------

def test_detect_config_defaults_to_config_factory():
    """detect_config() with no args returns an object with has() and get()."""
    cfg = Boot.detect_config()
    assert callable(getattr(cfg, "has", None))
    assert callable(getattr(cfg, "get", None))


# ---------------------------------------------------------------------------
# 2. detect_config passes through a duck-typed config object
# ---------------------------------------------------------------------------

def test_detect_config_passes_through_has_get_object():
    """detect_config({"config": EphemeralConfig({})}) returns the same object."""
    ec = EphemeralConfig({})
    result = Boot.detect_config({"config": ec})
    assert result is ec


# ---------------------------------------------------------------------------
# 3. boot populates _root
# ---------------------------------------------------------------------------

def test_boot_populates_root():
    """Boot.boot() with banner suppressed populates _root["config"]."""
    cfg = EphemeralConfig({"boot": {"banner-mode": "off"}})
    Boot.boot({"config": cfg})
    assert Boot.root("config") is not None


# ---------------------------------------------------------------------------
# 4. boot with contexts returns ApplicationContext
# ---------------------------------------------------------------------------

def test_boot_with_contexts_returns_app_ctx():
    """Boot.boot(contexts=[...]) returns an ApplicationContext and wires components."""
    from cdi import ApplicationContext, Context, Singleton

    class Greeter:
        qualifier = "greeter"

        def __init__(self):
            pass

    cfg = EphemeralConfig({"boot": {"banner-mode": "off"}})
    app_ctx = Boot.boot({
        "config": cfg,
        "contexts": [Context([Singleton(Greeter)])],
        "run": False,
    })
    assert isinstance(app_ctx, ApplicationContext)
    assert app_ctx.get("greeter") is not None


# ---------------------------------------------------------------------------
# 5. Boot.test suppresses banner output
# ---------------------------------------------------------------------------

def test_test_suppresses_banner(capsys):
    """Boot.test() produces no stdout output (banner is suppressed)."""
    Boot.test()
    captured = capsys.readouterr()
    assert captured.out == ""


# ---------------------------------------------------------------------------
# 6. Boot.root returns default when key absent
# ---------------------------------------------------------------------------

def test_root_returns_default_when_absent():
    """Boot.root("nonexistent", "default") returns "default"."""
    assert Boot.root("nonexistent", "default") == "default"


# ---------------------------------------------------------------------------
# 7. print_banner — off mode produces no output
# ---------------------------------------------------------------------------

def test_print_banner_off_mode(capsys):
    """print_banner with banner-mode=off produces no output."""
    cfg = EphemeralConfig({"boot": {"banner-mode": "off"}})
    print_banner(cfg)
    captured = capsys.readouterr()
    assert captured.out == ""


# ---------------------------------------------------------------------------
# 8. print_banner — console mode prints banner art
# ---------------------------------------------------------------------------

def test_print_banner_console_mode(capsys):
    """print_banner with default config prints banner art to stdout."""
    cfg = EphemeralConfig({})
    print_banner(cfg)
    captured = capsys.readouterr()
    # BANNER_ART contains this distinctive substring
    assert "alt-python/boot" in captured.out
