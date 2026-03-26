"""
config.selector — Base and concrete selector classes.

Selectors decide which config values should be processed by a resolver.
"""

from __future__ import annotations

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

from abc import ABC, abstractmethod


class Selector(ABC):
    """Base selector — subclasses implement matches() and optionally resolve_value()."""

    @abstractmethod
    def matches(self, value: object) -> bool:
        ...

    def resolve_value(self, value: str) -> str:
        return value


class PrefixSelector(Selector):
    """
    Selects string values that start with a given prefix.
    resolve_value() strips all occurrences of the prefix.

    e.g. PrefixSelector('enc.') matches 'enc.abc' and returns 'abc'.
    """

    def __init__(self, prefix: str) -> None:
        self.prefix = prefix

    def matches(self, value: object) -> bool:
        return isinstance(value, str) and value.startswith(self.prefix)

    def resolve_value(self, value: str) -> str:
        return value.replace(self.prefix, "")


class ParenthesisSelector(Selector):
    """
    Selects values wrapped in PREFIX(...) notation.
    e.g. ParenthesisSelector('ENC') matches 'ENC(ciphertext)' and returns 'ciphertext'.
    """

    def __init__(self, prefix: str) -> None:
        self.prefix = prefix

    def matches(self, value: object) -> bool:
        if not isinstance(value, str):
            return False
        low = value.lower()
        pfx = self.prefix.lower()
        return low.startswith(f"{pfx}(") and value.endswith(")")

    def resolve_value(self, value: str) -> str:
        return value[len(self.prefix) + 1 : -1]


class PlaceholderSelector(Selector):
    """Selects string values containing ${...} placeholder syntax."""

    def matches(self, value: object) -> bool:
        if not isinstance(value, str):
            return False
        open_idx = value.find("${")
        close_idx = value.find("}")
        return open_idx != -1 and close_idx != -1 and open_idx < close_idx
