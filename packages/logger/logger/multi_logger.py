"""
logger.multi_logger — Fan-out logger that writes to multiple loggers simultaneously.
"""

from __future__ import annotations

from typing import Any

from logger.logger import Logger
from logger.logger_level import LoggerLevel


class MultiLogger(Logger):
    """
    Fans out log calls to multiple child loggers.

    Mirrors the JS MultiLogger class.
    """

    def __init__(
        self,
        loggers: list[Logger] | None = None,
        category: str | None = None,
        level: str | None = None,
    ) -> None:
        # Assign loggers BEFORE calling super().__init__() because set_level()
        # iterates self.loggers and is called during base class construction.
        self.loggers: list[Logger] = list(loggers) if loggers else []
        super().__init__(category, level)

    def set_level(self, level: str) -> None:
        super().set_level(level)
        for lg in self.loggers:
            lg.set_level(level)

    def log(self, level: str, message: str, meta: Any = None) -> None:
        if self.is_level_enabled(level):
            for lg in self.loggers:
                lg.log(level, message, meta)

    def debug(self, message: str, meta: Any = None) -> None:
        self.log(LoggerLevel.DEBUG, message, meta)

    def verbose(self, message: str, meta: Any = None) -> None:
        self.log(LoggerLevel.VERBOSE, message, meta)

    def info(self, message: str, meta: Any = None) -> None:
        self.log(LoggerLevel.INFO, message, meta)

    def warn(self, message: str, meta: Any = None) -> None:
        self.log(LoggerLevel.WARN, message, meta)

    def error(self, message: str, meta: Any = None) -> None:
        self.log(LoggerLevel.ERROR, message, meta)

    def fatal(self, message: str, meta: Any = None) -> None:
        self.log(LoggerLevel.FATAL, message, meta)
