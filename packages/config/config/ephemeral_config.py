"""
config.ephemeral_config — Lightweight config backed by a plain Python dict.

Supports dot-notation paths (e.g. 'a.b.c') and falsy values (0, False, '').
"""

from __future__ import annotations

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

from typing import Any

_NO_DEFAULT = object()
_UNSET = object()


class EphemeralConfig:
    """
    Wraps a plain dict providing has(path) / get(path, default) access
    with dot-notation path traversal.

    Mirrors the JS EphemeralConfig class.
    """

    def __init__(self, obj: dict | None = None) -> None:
        self._obj: dict = obj if obj is not None else {}

    def get(self, path: str, default: Any = _NO_DEFAULT) -> Any:
        value = self._resolve(path)
        if value is not _UNSET:
            return value
        if default is not _NO_DEFAULT:
            return default
        raise KeyError(f"Config path '{path}' not found.")

    def has(self, path: str) -> bool:
        return self._resolve(path) is not _UNSET

    def _resolve(self, path: str) -> Any:
        # Try flat key first (allows dotted literal keys, e.g. 'a.b' as a single key)
        if path in self._obj:
            return self._obj[path]

        # Traverse dot-separated path
        steps = path.split(".")
        node: Any = self._obj
        for step in steps:
            if not isinstance(node, dict) or step not in node:
                return _UNSET
            node = node[step]
        return node
