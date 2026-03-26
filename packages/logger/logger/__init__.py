"""
logger — Spring-inspired config-driven logger for Python.

Quick start::

    from logger import logger_factory

    log = logger_factory.get_logger("com.example.MyService")
    log.info("Application started")
    log.debug("Debug detail")  # suppressed unless logging.level.com.example = debug

    # Or with ConfigFactory-backed config for full Spring-style setup:
    from config import ConfigFactory
    from logger import LoggerFactory

    factory = LoggerFactory(config=ConfigFactory.get_config())
    log = factory.get_logger("com.example.MyService")

Level hierarchy (config keys):
  logging.level./             → root level (default: info)
  logging.level.com           → level for all 'com.*' loggers
  logging.level.com.example   → level for 'com.example.*' loggers

Log format (config key):
  logging.format=text         → PlainTextFormatter
  logging.format=json         → JSONFormatter (default)
"""

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

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

# Module-level singleton — zero setup required.
logger_factory = LoggerFactory()

__all__ = [
    "LoggerLevel",
    "Logger",
    "ConsoleLogger",
    "DelegatingLogger",
    "ConfigurableLogger",
    "LoggerCategoryCache",
    "LoggerFactory",
    "JSONFormatter",
    "PlainTextFormatter",
    "CachingConsole",
    "MultiLogger",
    "logger_factory",
]
