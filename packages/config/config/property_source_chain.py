"""
config.property_source_chain — Layered property source chain.

Sources are queried in priority order (index 0 = highest priority).
First source that has the property wins.
"""

from __future__ import annotations

from typing import Any

_NO_DEFAULT = object()


class PropertySourceChain:
    """
    Ordered list of config sources.  has()/get() queries them in order;
    first source that has the path wins.

    Mirrors the JS PropertySourceChain class.
    """

    def __init__(self, sources: list | None = None) -> None:
        self.sources: list = list(sources) if sources else []

    def add_source(self, source: Any, priority: int | None = None) -> None:
        """
        Add a source.  Lower index = higher priority.
        If priority is omitted, appends at the end (lowest priority).
        """
        if priority is not None:
            self.sources.insert(priority, source)
        else:
            self.sources.append(source)

    def has(self, path: str) -> bool:
        return any(s.has(path) for s in self.sources)

    def get(self, path: str, default: Any = _NO_DEFAULT) -> Any:
        for source in self.sources:
            if source.has(path):
                return source.get(path)
        if default is not _NO_DEFAULT:
            return default
        raise KeyError(f"Config path '{path}' returned no value.")
