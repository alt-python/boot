"""
config.resolver — Resolver base classes and DelegatingResolver.

Resolvers walk the config tree applying value transformations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable

from config.selector import Selector


class Resolver(ABC):
    """
    Base resolver — provides map_values_deep() for tree walking.
    Subclasses implement resolve().
    """

    @staticmethod
    def is_mapping(value: Any) -> bool:
        return isinstance(value, dict)

    def map_values_deep(self, values: Any, callback: Callable) -> Any:
        if self.is_mapping(values):
            return {k: self.map_values_deep(v, callback) for k, v in values.items()}
        return callback(values)

    @abstractmethod
    def resolve(self, config: Any) -> Any:
        ...


class SelectiveResolver(Resolver):
    """Resolver that processes only values matching its Selector."""

    def __init__(self, selector: Selector) -> None:
        self.selector = selector

    def resolve(self, config: Any) -> Any:  # pragma: no cover
        return config


class DelegatingResolver(Resolver):
    """Chains multiple resolvers, applying each in sequence."""

    def __init__(self, resolvers: list[Resolver]) -> None:
        self.resolvers = resolvers

    def resolve(self, config: Any) -> Any:
        result = config
        for resolver in self.resolvers:
            result = resolver.resolve(result)
        return result
