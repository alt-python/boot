"""
logger.configurable_logger — Logger that reads its level from config.

Config path convention (dot-separated, Spring-aligned):
  logging.level./     → root logger level  (equivalent to JS 'logging.level./')
  logging.level.com.example     → level for 'com.example' category prefix
  logging.level.com.example.MyService → level for exact category

The lookup walks the category's dot-separated segments, taking the most-specific
level found.  Results are cached in LoggerCategoryCache.

Key design difference from JS:
  JS uses slash-separated category names (com/example/MyService) and a path-style
  config key (logging.level./com/example).
  Python uses dot-separated names (com.example.MyService) and config key
  logging.level.com.example.MyService.

  Root level is stored at config key: logging.level./  (slash = root marker,
  same as JS convention, kept for config-file compatibility).
"""

from __future__ import annotations

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

from typing import Any

from logger.delegating_logger import DelegatingLogger
from logger.logger import Logger
from logger.logger_category_cache import LoggerCategoryCache
from logger.logger_level import LoggerLevel


class ConfigurableLogger(DelegatingLogger):
    """
    Logger whose level is driven by config.

    Mirrors the JS ConfigurableLogger class.
    """

    DEFAULT_CONFIG_PATH = "logging.level"

    def __init__(
        self,
        config: Any,
        provider: Logger,
        category: str | None = None,
        config_path: str | None = None,
        cache: LoggerCategoryCache | None = None,
    ) -> None:
        super().__init__(provider)
        if config is None:
            raise ValueError("config is required")
        if cache is None:
            raise ValueError("cache is required")
        self.config = config
        self.category = category or Logger.DEFAULT_CATEGORY
        self.provider.category = self.category
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.cache = cache

        # Apply level from config immediately
        level = self.get_logger_level(
            self.category, self.config_path, self.config, self.cache
        )
        self.provider.set_level(level)

    @staticmethod
    def get_logger_level(
        category: str,
        config_path: str,
        config: Any,
        cache: LoggerCategoryCache,
    ) -> str:
        """
        Walk the category's dot-segments looking for the most-specific level in config.

        Config key structure:
          {config_path}./            → root level  (e.g. logging.level./)
          {config_path}.com          → level for top-level 'com' prefix
          {config_path}.com.example  → level for 'com.example' prefix

        The root slash marker keeps parity with the JS config file convention.
        """
        path = config_path or ConfigurableLogger.DEFAULT_CONFIG_PATH
        level = LoggerLevel.INFO

        # Check root level: e.g. logging.level./
        root_key = f"{path}./"
        cached = cache.get(root_key)
        if cached:
            level = cached
        elif config.has(root_key):
            val = config.get(root_key)
            if isinstance(val, str) and val in LoggerLevel.ENUMS:
                level = val
                cache.put(root_key, level)

        # Walk category segments
        segments = (category or "").split(".")
        path_step = path
        for i, seg in enumerate(segments):
            if not seg:
                continue
            path_step = f"{path_step}.{seg}" if i > 0 or path_step == path else f"{path}.{seg}"
            cached = cache.get(path_step)
            if cached:
                level = cached
            elif config.has(path_step):
                val = config.get(path_step)
                # Only apply string values — nested dicts mean there are more-specific
                # level entries under this prefix; the loop will eventually reach them.
                if isinstance(val, str) and val in LoggerLevel.ENUMS:
                    level = val
                    cache.put(path_step, level)

        return level
