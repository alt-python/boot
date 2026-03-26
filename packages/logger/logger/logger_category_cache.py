"""
logger.logger_category_cache — Simple dict cache for resolved logger levels.
"""

from __future__ import annotations

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

from typing import Any


class LoggerCategoryCache:
    """
    Caches the resolved log level string for each category path.

    Mirrors the JS LoggerCategoryCache class.
    """

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._cache.get(key)

    def put(self, key: str, level: str) -> None:
        self._cache[key] = level
