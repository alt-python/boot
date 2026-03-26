"""
config.value_resolving_config — Config wrapper that applies the resolver chain at get() time.

After construction, resolved_config holds the fully-resolved dict.
get(path) re-resolves lazily for path-specific access (matches JS behaviour).
"""

from __future__ import annotations

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

from typing import Any

from config.resolver import Resolver

_NO_DEFAULT = object()


class ValueResolvingConfig:
    """
    Wraps a config source and a DelegatingResolver.
    On construction, resolves the full config tree eagerly.
    get(path) resolves the subtree at path.

    Mirrors the JS ValueResolvingConfig class.
    """

    def __init__(
        self,
        config: Any,
        resolver: Resolver,
        path: str | None = None,
    ) -> None:
        self._config = config
        self._resolver = resolver
        self._path = path

        if path is None:
            # Resolve from the whole config object
            raw = self._get_raw_object(config)
        else:
            raw = config.get(path) if config.has(path) else None

        self.resolved_config = resolver.resolve(raw)

    # ------------------------------------------------------------------
    # Config protocol
    # ------------------------------------------------------------------

    def has(self, path: str) -> bool:
        return self._config.has(path)

    def get(self, path: str, default: Any = _NO_DEFAULT) -> Any:
        if default is not _NO_DEFAULT and not self.has(path):
            return default
        # Re-resolve the subtree lazily
        sub = ValueResolvingConfig(self._config, self._resolver, path)
        return sub.resolved_config

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _get_raw_object(config: Any) -> Any:
        """Extract the underlying dict from a config-like object."""
        if isinstance(config, dict):
            return config
        if hasattr(config, "_obj"):
            return config._obj  # EphemeralConfig
        # PropertySourceChain — merge all sources into a single dict
        if hasattr(config, "sources"):
            merged: dict = {}
            for source in reversed(config.sources):
                raw = ValueResolvingConfig._get_raw_object(source)
                if isinstance(raw, dict):
                    merged = _deep_merge(merged, raw)
            return merged
        return {}


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Recursively merge overlay into base (overlay wins on conflict)."""
    result = dict(base)
    for k, v in overlay.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result
