"""
logger.caching_logger_factory — LoggerFactory variant that injects CachingConsole.

Intended for test use only: every logger produced by this factory writes
to an in-memory CachingConsole so tests can assert on emitted messages
without depending on stdout or a real config file.
"""

from __future__ import annotations

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

from logger.logger_factory import LoggerFactory
from logger.configurable_logger import ConfigurableLogger
from logger.console_logger import ConsoleLogger
from logger.caching_console import CachingConsole


class CachingLoggerFactory(LoggerFactory):
    """LoggerFactory that wires each logger with CachingConsole (test use only)."""

    def get_logger(self, category=None) -> ConfigurableLogger:
        cat = self._resolve_category(category)
        formatter = self._get_formatter()
        caching_console = CachingConsole()
        provider = ConsoleLogger(category=cat, formatter=formatter, stdlib_logger=caching_console)
        return ConfigurableLogger(
            config=self.config,
            provider=provider,
            category=cat,
            config_path=self.config_path,
            cache=self.cache,
        )
