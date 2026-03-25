"""
tests/test_logger_primitives.py — tests for LoggerLevel, Logger, formatters, and cache.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from logger.logger_level import LoggerLevel
from logger.logger import Logger
from logger.json_formatter import JSONFormatter
from logger.plain_text_formatter import PlainTextFormatter
from logger.logger_category_cache import LoggerCategoryCache


# ---------------------------------------------------------------------------
# LoggerLevel
# ---------------------------------------------------------------------------

class TestLoggerLevel:
    def test_enums_ordering(self):
        # Lower number = more severe
        assert LoggerLevel.ENUMS["fatal"] < LoggerLevel.ENUMS["error"]
        assert LoggerLevel.ENUMS["error"] < LoggerLevel.ENUMS["warn"]
        assert LoggerLevel.ENUMS["warn"] < LoggerLevel.ENUMS["info"]
        assert LoggerLevel.ENUMS["info"] < LoggerLevel.ENUMS["verbose"]
        assert LoggerLevel.ENUMS["verbose"] < LoggerLevel.ENUMS["debug"]

    def test_stdlib_mapping_ascending(self):
        # STDLIB: higher = more severe (Python convention inverted)
        assert LoggerLevel.STDLIB["debug"] < LoggerLevel.STDLIB["verbose"]
        assert LoggerLevel.STDLIB["verbose"] < LoggerLevel.STDLIB["info"]
        assert LoggerLevel.STDLIB["info"] < LoggerLevel.STDLIB["warn"]
        assert LoggerLevel.STDLIB["warn"] < LoggerLevel.STDLIB["error"]
        assert LoggerLevel.STDLIB["error"] < LoggerLevel.STDLIB["fatal"]


# ---------------------------------------------------------------------------
# Logger base
# ---------------------------------------------------------------------------

class TestLogger:
    def test_default_level_is_info(self):
        lg = Logger("test")
        assert lg.is_info_enabled() is True
        assert lg.is_warn_enabled() is True
        assert lg.is_error_enabled() is True
        assert lg.is_fatal_enabled() is True
        # debug/verbose suppressed at info
        assert lg.is_debug_enabled() is False
        assert lg.is_verbose_enabled() is False

    def test_debug_level_enables_all(self):
        lg = Logger("test", level="debug")
        assert lg.is_debug_enabled() is True
        assert lg.is_verbose_enabled() is True
        assert lg.is_info_enabled() is True
        assert lg.is_warn_enabled() is True
        assert lg.is_error_enabled() is True
        assert lg.is_fatal_enabled() is True

    def test_warn_level_suppresses_info_and_below(self):
        lg = Logger("test", level="warn")
        assert lg.is_warn_enabled() is True
        assert lg.is_error_enabled() is True
        assert lg.is_fatal_enabled() is True
        assert lg.is_info_enabled() is False
        assert lg.is_verbose_enabled() is False
        assert lg.is_debug_enabled() is False

    def test_fatal_level_suppresses_everything_else(self):
        lg = Logger("test", level="fatal")
        assert lg.is_fatal_enabled() is True
        assert lg.is_error_enabled() is False
        assert lg.is_warn_enabled() is False
        assert lg.is_info_enabled() is False

    def test_set_level_changes_behaviour(self):
        lg = Logger("test", level="info")
        assert lg.is_debug_enabled() is False
        lg.set_level("debug")
        assert lg.is_debug_enabled() is True

    def test_default_category(self):
        lg = Logger()
        assert lg.category == Logger.DEFAULT_CATEGORY

    def test_custom_category(self):
        lg = Logger("com.example.MyService")
        assert lg.category == "com.example.MyService"


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

TS = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


class TestJSONFormatter:
    def test_basic_format(self):
        fmt = JSONFormatter()
        output = fmt.format(TS, "myapp", "info", "hello")
        data = json.loads(output)
        assert data["level"] == "info"
        assert data["message"] == "hello"
        assert data["category"] == "myapp"
        assert "timestamp" in data

    def test_plain_meta_included(self):
        fmt = JSONFormatter()
        output = fmt.format(TS, "cat", "warn", "msg", "extra")
        data = json.loads(output)
        assert data["meta"] == "extra"

    def test_dict_meta_merged(self):
        fmt = JSONFormatter()
        output = fmt.format(TS, "cat", "error", "msg", {"requestId": "abc"})
        data = json.loads(output)
        assert data["requestId"] == "abc"
        assert "meta" not in data

    def test_no_meta(self):
        fmt = JSONFormatter()
        output = fmt.format(TS, "cat", "debug", "msg")
        data = json.loads(output)
        assert "meta" not in data


class TestPlainTextFormatter:
    def test_basic_format(self):
        fmt = PlainTextFormatter()
        output = fmt.format(TS, "myapp", "info", "hello")
        assert "myapp" in output
        assert "info" in output
        assert "hello" in output

    def test_meta_appended(self):
        fmt = PlainTextFormatter()
        output = fmt.format(TS, "cat", "warn", "msg", "extra")
        assert "extra" in output

    def test_no_meta(self):
        fmt = PlainTextFormatter()
        output = fmt.format(TS, "cat", "debug", "msg")
        assert output.endswith("msg")


# ---------------------------------------------------------------------------
# LoggerCategoryCache
# ---------------------------------------------------------------------------

class TestLoggerCategoryCache:
    def test_put_and_get(self):
        cache = LoggerCategoryCache()
        cache.put("com.example", "debug")
        assert cache.get("com.example") == "debug"

    def test_missing_returns_none(self):
        cache = LoggerCategoryCache()
        assert cache.get("nope") is None
