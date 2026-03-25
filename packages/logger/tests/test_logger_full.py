"""
tests/test_logger_full.py — full logger test suite.
"""

from __future__ import annotations

import json
import logging

import pytest

from config.ephemeral_config import EphemeralConfig
from logger.logger_level import LoggerLevel
from logger.logger import Logger
from logger.console_logger import ConsoleLogger
from logger.delegating_logger import DelegatingLogger
from logger.configurable_logger import ConfigurableLogger
from logger.logger_category_cache import LoggerCategoryCache
from logger.logger_factory import LoggerFactory
from logger.json_formatter import JSONFormatter
from logger.plain_text_formatter import PlainTextFormatter
from logger.caching_console import CachingConsole
from logger.multi_logger import MultiLogger


# ---------------------------------------------------------------------------
# Helper: ConsoleLogger with CachingConsole
# ---------------------------------------------------------------------------

def _make_caching_logger(category: str = "test", level: str = "debug") -> tuple[ConsoleLogger, CachingConsole]:
    cache_sink = CachingConsole()
    fmt = PlainTextFormatter()
    cl = ConsoleLogger(category=category, level=level, formatter=fmt, stdlib_logger=cache_sink)  # type: ignore[arg-type]
    return cl, cache_sink


# ---------------------------------------------------------------------------
# ConsoleLogger
# ---------------------------------------------------------------------------

class TestConsoleLogger:
    def test_info_message_emitted(self):
        cl, sink = _make_caching_logger(level="info")
        cl.info("hello")
        assert len(sink.messages) == 1
        assert "hello" in sink.messages[0][1]

    def test_debug_suppressed_at_info(self):
        cl, sink = _make_caching_logger(level="info")
        cl.debug("suppressed")
        assert len(sink.messages) == 0

    def test_debug_emitted_at_debug(self):
        cl, sink = _make_caching_logger(level="debug")
        cl.debug("visible")
        assert len(sink.messages) == 1

    def test_warn_emitted(self):
        cl, sink = _make_caching_logger(level="warn")
        cl.warn("warning")
        assert len(sink.messages) == 1

    def test_error_emitted(self):
        cl, sink = _make_caching_logger(level="error")
        cl.error("error msg")
        assert len(sink.messages) == 1

    def test_fatal_emitted(self):
        cl, sink = _make_caching_logger(level="fatal")
        cl.fatal("fatal msg")
        assert len(sink.messages) == 1

    def test_verbose_emitted_at_verbose(self):
        cl, sink = _make_caching_logger(level="verbose")
        cl.verbose("verbose msg")
        assert len(sink.messages) == 1

    def test_verbose_suppressed_at_info(self):
        cl, sink = _make_caching_logger(level="info")
        cl.verbose("suppressed")
        assert len(sink.messages) == 0

    def test_log_method(self):
        cl, sink = _make_caching_logger(level="debug")
        cl.log("info", "via log()")
        assert len(sink.messages) == 1


# ---------------------------------------------------------------------------
# DelegatingLogger
# ---------------------------------------------------------------------------

class TestDelegatingLogger:
    def test_delegates_info(self):
        cl, sink = _make_caching_logger(level="debug")
        dl = DelegatingLogger(cl)
        dl.info("delegated")
        assert len(sink.messages) == 1

    def test_requires_provider(self):
        with pytest.raises(ValueError, match="provider is required"):
            DelegatingLogger(None)  # type: ignore[arg-type]

    def test_set_level_propagates(self):
        cl, sink = _make_caching_logger(level="debug")
        dl = DelegatingLogger(cl)
        dl.set_level("warn")
        assert dl.is_info_enabled() is False
        assert dl.is_warn_enabled() is True


# ---------------------------------------------------------------------------
# ConfigurableLogger — level from config
# ---------------------------------------------------------------------------

def _make_cfg_logger(
    config_dict: dict,
    category: str = "test",
    level_in_config: str | None = None,
) -> tuple[ConfigurableLogger, CachingConsole]:
    cfg = EphemeralConfig(config_dict)
    sink = CachingConsole()
    provider = ConsoleLogger(category=category, formatter=PlainTextFormatter(), stdlib_logger=sink)  # type: ignore[arg-type]
    cache = LoggerCategoryCache()
    return ConfigurableLogger(
        config=cfg, provider=provider, category=category, cache=cache
    ), sink


class TestConfigurableLogger:
    def test_level_from_root_config(self):
        cl, sink = _make_cfg_logger({"logging": {"level": {"/": "debug"}}}, "myapp")
        cl.debug("visible")
        assert len(sink.messages) == 1

    def test_level_from_category_config(self):
        cl, sink = _make_cfg_logger(
            {"logging": {"level": {"/": "info", "com": {"example": "debug"}}}},
            "com.example.MyService",
        )
        assert cl.is_debug_enabled() is True

    def test_category_level_overrides_root(self):
        cl, sink = _make_cfg_logger(
            {"logging": {"level": {"/": "debug", "com": {"example": "warn"}}}},
            "com.example.MyService",
        )
        assert cl.is_info_enabled() is False
        assert cl.is_warn_enabled() is True

    def test_default_level_info_when_no_config(self):
        cl, sink = _make_cfg_logger({}, "no.config.here")
        assert cl.is_info_enabled() is True
        assert cl.is_debug_enabled() is False

    def test_requires_config(self):
        provider = ConsoleLogger("test")
        cache = LoggerCategoryCache()
        with pytest.raises(ValueError, match="config is required"):
            ConfigurableLogger(None, provider, cache=cache)  # type: ignore[arg-type]

    def test_requires_cache(self):
        cfg = EphemeralConfig({})
        provider = ConsoleLogger("test")
        with pytest.raises(ValueError, match="cache is required"):
            ConfigurableLogger(cfg, provider, cache=None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# ConfigurableLogger — dot hierarchy lookup
# ---------------------------------------------------------------------------

class TestDotHierarchy:
    def test_parent_level_applied_to_child(self):
        """logging.level.com set to debug; com.example.MyService inherits."""
        cfg = EphemeralConfig({"logging": {"level": {"/": "warn", "com": "debug"}}})
        sink = CachingConsole()
        provider = ConsoleLogger(
            category="com.example.MyService",
            formatter=PlainTextFormatter(),
            stdlib_logger=sink,  # type: ignore[arg-type]
        )
        cl = ConfigurableLogger(
            config=cfg,
            provider=provider,
            category="com.example.MyService",
            cache=LoggerCategoryCache(),
        )
        assert cl.is_debug_enabled() is True

    def test_more_specific_level_wins(self):
        """
        More specific config segment overrides less specific.
        Config uses nested dicts — dot-traversal walks segments in order.
        logging.level.com.example.MyService = warn overrides logging.level./ = info.
        """
        cfg = EphemeralConfig({
            "logging": {
                "level": {
                    "/": "info",
                    "com": {
                        "example": {
                            "MyService": "warn",
                        }
                    },
                }
            }
        })
        sink = CachingConsole()
        provider = ConsoleLogger(
            category="com.example.MyService",
            formatter=PlainTextFormatter(),
            stdlib_logger=sink,  # type: ignore[arg-type]
        )
        cl = ConfigurableLogger(
            config=cfg,
            provider=provider,
            category="com.example.MyService",
            cache=LoggerCategoryCache(),
        )
        assert cl.is_warn_enabled() is True
        assert cl.is_info_enabled() is False


# ---------------------------------------------------------------------------
# MultiLogger
# ---------------------------------------------------------------------------

class TestMultiLogger:
    def test_fans_out_to_all_loggers(self):
        cl1, sink1 = _make_caching_logger(level="debug")
        cl2, sink2 = _make_caching_logger(level="debug")
        ml = MultiLogger([cl1, cl2], level="debug")
        ml.info("broadcast")
        assert len(sink1.messages) == 1
        assert len(sink2.messages) == 1

    def test_level_gate_applies(self):
        cl1, sink1 = _make_caching_logger(level="debug")
        cl2, sink2 = _make_caching_logger(level="debug")
        ml = MultiLogger([cl1, cl2], level="warn")
        ml.info("suppressed")
        assert len(sink1.messages) == 0
        assert len(sink2.messages) == 0

    def test_set_level_propagates_to_children(self):
        cl1, sink1 = _make_caching_logger(level="debug")
        ml = MultiLogger([cl1], level="debug")
        ml.set_level("warn")
        assert ml.is_info_enabled() is False
        assert cl1.is_info_enabled() is False


# ---------------------------------------------------------------------------
# LoggerFactory
# ---------------------------------------------------------------------------

class TestLoggerFactory:
    def test_get_logger_returns_configurable_logger(self):
        cfg = EphemeralConfig({"logging": {"level": {"/": "debug"}}})
        factory = LoggerFactory(config=cfg)
        lg = factory.get_logger("com.example.MyService")
        assert isinstance(lg, ConfigurableLogger)

    def test_level_from_config(self):
        cfg = EphemeralConfig({
            "logging": {
                "level": {"/": "warn"},
                "format": "text",
            }
        })
        factory = LoggerFactory(config=cfg)
        lg = factory.get_logger("com.example.MyService")
        assert lg.is_warn_enabled() is True
        assert lg.is_info_enabled() is False

    def test_json_format_default(self):
        cfg = EphemeralConfig({})
        factory = LoggerFactory(config=cfg)
        formatter = factory._get_formatter()
        assert isinstance(formatter, JSONFormatter)

    def test_text_format_from_config(self):
        cfg = EphemeralConfig({"logging": {"format": "text"}})
        factory = LoggerFactory(config=cfg)
        formatter = factory._get_formatter()
        assert isinstance(formatter, PlainTextFormatter)

    def test_category_from_object(self):
        class MyService:
            pass

        cfg = EphemeralConfig({})
        factory = LoggerFactory(config=cfg)
        lg = factory.get_logger(MyService())
        assert lg.category == "MyService"

    def test_category_from_qualifier(self):
        class MyBean:
            qualifier = "my.qualifier"

        cfg = EphemeralConfig({})
        factory = LoggerFactory(config=cfg)
        lg = factory.get_logger(MyBean())
        assert lg.category == "my.qualifier"


# ---------------------------------------------------------------------------
# Integration: full stack config → logger
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_config_driven_logger_emits_at_correct_level(self, tmp_path):
        from config.profile_config_loader import ProfileConfigLoader
        from config.config_factory import ConfigFactory

        (tmp_path / "application.json").write_text(json.dumps({
            "logging": {
                "level": {
                    "/": "warn",
                    "com": {"example": "debug"},
                },
                "format": "text",
            }
        }))
        backing = ProfileConfigLoader.load(base_path=str(tmp_path))
        cfg = ConfigFactory.get_config(config=backing)

        factory = LoggerFactory(config=cfg)

        # com.example.Service → inherits debug from com.example
        lg_svc = factory.get_logger("com.example.Service")
        assert lg_svc.is_debug_enabled() is True

        # other.pkg → inherits warn from root
        lg_other = factory.get_logger("other.pkg.Handler")
        assert lg_other.is_info_enabled() is False
        assert lg_other.is_warn_enabled() is True

    def test_module_level_singleton(self):
        """logger_factory singleton is usable with no setup."""
        from logger import logger_factory
        lg = logger_factory.get_logger("test.integration")
        assert lg is not None
        assert isinstance(lg, ConfigurableLogger)
