"""
config.env_property_source — Wraps os.environ as a config source with relaxed binding.

Relaxed binding (Spring conventions):
  MY_APP_PORT       → my.app.port
  DOUBLE__UNDER     → double.under   (double-underscore → dot first)
  Direct key also accessible as-is.
"""

from __future__ import annotations

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

import os
from typing import Any

_NO_DEFAULT = object()


class EnvPropertySource:
    """
    Property source backed by environment variables.

    Mirrors the JS EnvPropertySource class.
    """

    def __init__(self, env: dict | None = None) -> None:
        self._env: dict = env if env is not None else dict(os.environ)
        self._cache: dict | None = None

    def _get_cache(self) -> dict:
        if self._cache is not None:
            return self._cache
        cache: dict = {}
        for key, value in self._env.items():
            cache[key] = value
            # Relaxed form: double-underscore → dot first, then single underscore → dot
            relaxed = key.replace("__", ".").replace("_", ".").lower()
            if relaxed != key:
                cache[relaxed] = value
        self._cache = cache
        return cache

    def has(self, path: str) -> bool:
        return path in self._get_cache()

    def get(self, path: str, default: Any = _NO_DEFAULT) -> Any:
        cache = self._get_cache()
        if path in cache:
            return cache[path]
        if default is not _NO_DEFAULT:
            return default
        return None
