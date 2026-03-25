"""
logger.delegating_logger — Logger that delegates all calls to a provider.
"""

from __future__ import annotations

from typing import Any

from logger.logger import Logger
from logger.logger_level import LoggerLevel


class DelegatingLogger(Logger):
    """
    Wraps a provider logger, forwarding all calls to it.

    Mirrors the JS DelegatingLogger class.
    """

    def __init__(self, provider: Logger) -> None:
        if provider is None:
            raise ValueError("provider is required")
        # Don't call super().__init__() with a level — level lives on the provider
        self.provider = provider
        self.category = provider.category

    def set_level(self, level: str) -> None:
        self.provider.set_level(level)

    def is_level_enabled(self, level: str) -> bool:
        return self.provider.is_level_enabled(level)

    def is_fatal_enabled(self) -> bool:
        return self.provider.is_fatal_enabled()

    def is_error_enabled(self) -> bool:
        return self.provider.is_error_enabled()

    def is_warn_enabled(self) -> bool:
        return self.provider.is_warn_enabled()

    def is_info_enabled(self) -> bool:
        return self.provider.is_info_enabled()

    def is_verbose_enabled(self) -> bool:
        return self.provider.is_verbose_enabled()

    def is_debug_enabled(self) -> bool:
        return self.provider.is_debug_enabled()

    def log(self, level: str, message: str, meta: Any = None) -> None:
        self.provider.log(level, message, meta)

    def debug(self, message: str, meta: Any = None) -> None:
        self.provider.debug(message, meta)

    def verbose(self, message: str, meta: Any = None) -> None:
        self.provider.verbose(message, meta)

    def info(self, message: str, meta: Any = None) -> None:
        self.provider.info(message, meta)

    def warn(self, message: str, meta: Any = None) -> None:
        self.provider.warn(message, meta)

    def error(self, message: str, meta: Any = None) -> None:
        self.provider.error(message, meta)

    def fatal(self, message: str, meta: Any = None) -> None:
        self.provider.fatal(message, meta)
