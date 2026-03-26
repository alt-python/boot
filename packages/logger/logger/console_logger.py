"""
logger.console_logger — Logger that writes formatted records to stdout.

The formatter (JSONFormatter or PlainTextFormatter) produces the final string.
Output goes to sys.stdout so all levels appear on stdout — error and fatal
included. Callers that want stderr routing can pass a custom sink.

The optional stdlib_logger parameter accepts a CachingConsole (or any object
with isEnabledFor(int) and log(int, str)) for use in tests.
"""

from __future__ import annotations

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

import sys
from datetime import datetime, timezone
from typing import Any

from logger.logger import Logger
from logger.logger_level import LoggerLevel
from logger.json_formatter import JSONFormatter


class ConsoleLogger(Logger):
    """
    Logger implementation that emits formatted records to stdout.

    Mirrors the JS ConsoleLogger class.
    """

    def __init__(
        self,
        category: str | None = None,
        level: str | None = None,
        formatter: Any = None,
        stdlib_logger: Any = None,
    ) -> None:
        super().__init__(category, level)
        self.formatter = formatter or JSONFormatter()
        # stdlib_logger is kept for test injection (CachingConsole).
        # When None we write directly to sys.stdout — no stdlib handler chain.
        self._sink = stdlib_logger  # None means use sys.stdout

    # ------------------------------------------------------------------
    # Emit
    # ------------------------------------------------------------------

    def _emit(self, level_name: str, message: str, meta: Any = None) -> None:
        formatted = self.formatter.format(
            datetime.now(timezone.utc), self.category, level_name, message, meta
        )
        if self._sink is not None:
            stdlib_level = LoggerLevel.STDLIB[level_name]
            if self._sink.isEnabledFor(stdlib_level):
                self._sink.log(stdlib_level, formatted)
        else:
            print(formatted, file=sys.stdout)

    def log(self, level: str, message: str, meta: Any = None) -> None:
        if self.is_level_enabled(level):
            self._emit(level, message, meta)

    def debug(self, message: str, meta: Any = None) -> None:
        if self.is_debug_enabled():
            self._emit(LoggerLevel.DEBUG, message, meta)

    def verbose(self, message: str, meta: Any = None) -> None:
        if self.is_verbose_enabled():
            self._emit(LoggerLevel.VERBOSE, message, meta)

    def info(self, message: str, meta: Any = None) -> None:
        if self.is_info_enabled():
            self._emit(LoggerLevel.INFO, message, meta)

    def warn(self, message: str, meta: Any = None) -> None:
        if self.is_warn_enabled():
            self._emit(LoggerLevel.WARN, message, meta)

    def error(self, message: str, meta: Any = None) -> None:
        if self.is_error_enabled():
            self._emit(LoggerLevel.ERROR, message, meta)

    def fatal(self, message: str, meta: Any = None) -> None:
        if self.is_fatal_enabled():
            self._emit(LoggerLevel.FATAL, message, meta)
