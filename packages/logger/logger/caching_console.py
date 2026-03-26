"""
logger.caching_console — In-memory log capture for tests.

Replaces the stdlib logger with a list accumulator so test code can
assert on what was logged without depending on stdout.
"""

from __future__ import annotations

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

from typing import Any


class CachingConsole:
    """
    In-memory log store.  Passed to ConsoleLogger in place of a stdlib logger.

    Exposes .messages for inspection in tests.

    Mirrors the JS CachingConsole class.
    """

    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []

    def isEnabledFor(self, level: int) -> bool:  # noqa: N802 — matches stdlib Logger API
        return True

    def log(self, level: int, message: str, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        self.messages.append((level, message))

    def clear(self) -> None:
        self.messages.clear()
