"""
logger.console_logger — Logger that emits via Python's stdlib logging.

Each ConsoleLogger wraps a stdlib logging.Logger so the full stdlib handler
ecosystem (StreamHandler, FileHandler, RotatingFileHandler, etc.) is available.

The formatter argument controls the output format of each log record's message
string; the stdlib handler controls destination and encoding.
"""

from __future__ import annotations

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

import logging
from datetime import datetime, timezone
from typing import Any

from logger.logger import Logger
from logger.logger_level import LoggerLevel, VERBOSE_INT
from logger.json_formatter import JSONFormatter


class ConsoleLogger(Logger):
    """
    Logger implementation that emits via a stdlib logging.Logger.

    Mirrors the JS ConsoleLogger class.
    """

    def __init__(
        self,
        category: str | None = None,
        level: str | None = None,
        formatter: Any = None,
        stdlib_logger: logging.Logger | None = None,
    ) -> None:
        super().__init__(category, level)
        self.formatter = formatter or JSONFormatter()
        self._stdlib = stdlib_logger or logging.getLogger(self.category)

    # ------------------------------------------------------------------
    # Emit methods
    # ------------------------------------------------------------------

    def _emit(self, level_name: str, message: str, meta: Any = None) -> None:
        stdlib_level = LoggerLevel.STDLIB[level_name]
        if self._stdlib.isEnabledFor(stdlib_level):
            formatted = self.formatter.format(
                datetime.now(timezone.utc), self.category, level_name, message, meta
            )
            self._stdlib.log(stdlib_level, formatted)

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
