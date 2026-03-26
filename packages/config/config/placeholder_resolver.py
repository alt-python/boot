"""
config.placeholder_resolver — Resolves ${path} and ${path:default} placeholders.
"""

from __future__ import annotations

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

from typing import Any

from config.resolver import SelectiveResolver
from config.selector import PlaceholderSelector


class PlaceholderResolver(SelectiveResolver):
    """
    Resolves ${path} and ${path:default} placeholders in config values.

    Supports multiple placeholders in a single string value:
      "Hello ${name}, port is ${server.port}"

    Mirrors the JS PlaceHolderResolver class.
    """

    def __init__(self, selector: PlaceholderSelector | None = None, reference: Any = None) -> None:
        super().__init__(selector or PlaceholderSelector())
        self.reference = reference  # set after construction to avoid circular ref

    def resolve(self, config: Any) -> Any:
        return self.map_values_deep(config, self._resolve_value)

    def _resolve_value(self, value: Any) -> Any:
        if not self.selector.matches(value):
            return value
        try:
            return self._expand_placeholders(value)
        except Exception:
            return value

    def _expand_placeholders(self, template: str) -> str:
        result = ""
        remainder = template

        while True:
            open_idx = remainder.find("${")
            if open_idx == -1:
                result += remainder
                break
            close_idx = remainder.find("}", open_idx)
            if close_idx == -1:
                result += remainder
                break

            result += remainder[:open_idx]
            placeholder = remainder[open_idx + 2 : close_idx]
            remainder = remainder[close_idx + 1 :]

            # Support ${path:default}
            if ":" in placeholder:
                path, default = placeholder.split(":", 1)
                result += str(self.reference.get(path.strip(), default))
            else:
                result += str(self.reference.get(placeholder.strip()))

        return result
