"""
logger.logger — Base logger with level-gated methods.
"""

from __future__ import annotations

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

from logger.logger_level import LoggerLevel


class Logger:
    """
    Base logger.  Stores severity level and provides is_*_enabled() guards.

    severity_level: int from LoggerLevel.ENUMS (fatal=0, debug=5).
    A logger with level X enables all methods whose ENUMS value is <= X.
    """

    DEFAULT_CATEGORY = "ROOT"

    def __init__(
        self,
        category: str | None = None,
        level: str | None = None,
    ) -> None:
        self.category: str = category or Logger.DEFAULT_CATEGORY
        self._levels = LoggerLevel.ENUMS
        self.set_level(level or LoggerLevel.INFO)

    def set_level(self, level: str) -> None:
        self._level_name = level or LoggerLevel.INFO
        self._severity = self._levels.get(self._level_name, self._levels[LoggerLevel.INFO])

    def is_level_enabled(self, level: str) -> bool:
        return self._levels.get(level, -1) <= self._severity

    def is_fatal_enabled(self) -> bool:
        return self.is_level_enabled(LoggerLevel.FATAL)

    def is_error_enabled(self) -> bool:
        return self.is_level_enabled(LoggerLevel.ERROR)

    def is_warn_enabled(self) -> bool:
        return self.is_level_enabled(LoggerLevel.WARN)

    def is_info_enabled(self) -> bool:
        return self.is_level_enabled(LoggerLevel.INFO)

    def is_verbose_enabled(self) -> bool:
        return self.is_level_enabled(LoggerLevel.VERBOSE)

    def is_debug_enabled(self) -> bool:
        return self.is_level_enabled(LoggerLevel.DEBUG)
