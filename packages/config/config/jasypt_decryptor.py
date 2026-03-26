"""
config.jasypt_decryptor — Resolves jasypt-encrypted values in the config tree.

Supports two forms:
  enc.<base64>          (PrefixSelector)
  ENC(<base64>)         (ParenthesisSelector)

Password comes from PY_CONFIG_PASSPHRASE env var or defaults to 'changeit'.
"""

from __future__ import annotations

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

import os
from typing import Any

from config.resolver import SelectiveResolver
from config.selector import PrefixSelector, ParenthesisSelector


class JasyptDecryptor(SelectiveResolver):
    """
    Resolves encrypted config values using pysypt.

    Mirrors the JS JasyptDecryptor class.
    """

    def __init__(
        self,
        selector: PrefixSelector | ParenthesisSelector | None = None,
        password: str | None = None,
    ) -> None:
        super().__init__(selector or PrefixSelector("enc."))
        self.password = password or os.environ.get("PY_CONFIG_PASSPHRASE", "changeit")
        self._jasypt: Any = None

    def _get_jasypt(self) -> Any:
        if self._jasypt is None:
            from pysypt import Jasypt  # lazy import to avoid circular dependency
            self._jasypt = Jasypt()
        return self._jasypt

    def resolve(self, config: Any) -> Any:
        return self.map_values_deep(config, self._resolve_value)

    def _resolve_value(self, value: Any) -> Any:
        if not self.selector.matches(value):
            return value
        try:
            selected = self.selector.resolve_value(value)
            return self._get_jasypt().decrypt(selected, self.password)
        except Exception:
            return value
