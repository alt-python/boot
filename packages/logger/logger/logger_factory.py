"""
logger.logger_factory — Factory for creating ConfigurableLoggers.

LoggerFactory.get_logger(category) creates a logger whose level is read from
the active config at logging.level.<category> (dot hierarchy).

The module-level loggerFactory singleton is usable with no setup — it reads
from the config module's default config.

Format selection:
  logging.format=json  → JSONFormatter (default in non-browser contexts)
  logging.format=text  → PlainTextFormatter
"""

from __future__ import annotations

from typing import Any

from logger.configurable_logger import ConfigurableLogger
from logger.console_logger import ConsoleLogger
from logger.logger_category_cache import LoggerCategoryCache
from logger.json_formatter import JSONFormatter
from logger.plain_text_formatter import PlainTextFormatter


_shared_cache = LoggerCategoryCache()


class LoggerFactory:
    """
    Creates ConfigurableLogger instances wired to a config source.

    Mirrors the JS LoggerFactory class.
    """

    def __init__(
        self,
        config: Any = None,
        cache: LoggerCategoryCache | None = None,
        config_path: str | None = None,
    ) -> None:
        if config is None:
            from config import config as _default_config
            config = _default_config
        self.config = config
        # Each factory gets its own cache by default to avoid cross-instance pollution.
        # Pass a shared cache explicitly when you want level caching across factories.
        self.cache = cache if cache is not None else LoggerCategoryCache()
        self.config_path = config_path or ConfigurableLogger.DEFAULT_CONFIG_PATH

    # ------------------------------------------------------------------
    # Instance method
    # ------------------------------------------------------------------

    def get_logger(self, category: Any = None) -> ConfigurableLogger:
        """
        Create a ConfigurableLogger for the given category.

        category may be:
          - a string (used directly)
          - an object with a .qualifier, .name, or .__class__.__name__ attribute
          - None (uses ROOT category)
        """
        cat = self._resolve_category(category)
        formatter = self._get_formatter()
        provider = ConsoleLogger(category=cat, formatter=formatter)
        return ConfigurableLogger(
            config=self.config,
            provider=provider,
            category=cat,
            config_path=self.config_path,
            cache=self.cache,
        )

    def _get_formatter(self) -> Any:
        fmt = "json"
        if self.config.has("logging.format"):
            fmt = self.config.get("logging.format")
        return PlainTextFormatter() if fmt.lower() == "text" else JSONFormatter()

    @staticmethod
    def _resolve_category(category: Any) -> str:
        if isinstance(category, str):
            return category
        if category is None:
            return ""
        return (
            getattr(category, "qualifier", None)
            or getattr(category, "name", None)
            or type(category).__name__
        )

    # ------------------------------------------------------------------
    # Static convenience
    # ------------------------------------------------------------------

    @staticmethod
    def get_logger_static(
        category: Any = None,
        config: Any = None,
        config_path: str | None = None,
        cache: LoggerCategoryCache | None = None,
    ) -> ConfigurableLogger:
        """
        Static factory method — matches JS LoggerFactory.getLogger() signature.
        """
        factory = LoggerFactory(config=config, cache=cache, config_path=config_path)
        return factory.get_logger(category)
