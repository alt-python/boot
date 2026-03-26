"""
common — shared utilities for the alt-python/boot packages.

Provides:
  is_empty(*args)       — True if any argument is None or an empty/whitespace string
  is_plain_object(val)  — True if val is a plain dict (not a class instance, list, etc.)
"""

from __future__ import annotations

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

from typing import Any


def is_empty(*args: Any) -> bool:
    """
    Return True if any argument is None or an empty / whitespace-only string.

    Mirrors the JS isEmpty() utility used across the alt-javascript packages.
    """
    for obj in args:
        if obj is None:
            return True
        if isinstance(obj, str) and obj.strip() == "":
            return True
    return False


def is_plain_object(value: Any) -> bool:
    """
    Return True if value is a plain dict.

    In Python, a plain object maps to dict; class instances are excluded.
    Mirrors JS isPlainObject() from @alt-javascript/common.
    """
    return isinstance(value, dict)


__all__ = ["is_empty", "is_plain_object"]
