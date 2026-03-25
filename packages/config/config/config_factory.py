"""
config.config_factory — Wires the full config stack.

get_config() produces a ValueResolvingConfig that:
  - reads from ProfileConfigLoader (file-backed PropertySourceChain)
  - applies placeholder resolution (${path})
  - applies jasypt decryption (enc.<base64> and ENC(<base64>))

The module-level `config` singleton is usable with no setup.
"""

from __future__ import annotations

from typing import Any

from config.profile_config_loader import ProfileConfigLoader
from config.value_resolving_config import ValueResolvingConfig
from config.placeholder_resolver import PlaceholderResolver
from config.jasypt_decryptor import JasyptDecryptor
from config.resolver import DelegatingResolver
from config.selector import PrefixSelector, ParenthesisSelector, PlaceholderSelector


class ConfigFactory:
    """
    Builds a fully-wired config stack.

    Mirrors the JS ConfigFactory class.
    """

    @staticmethod
    def get_config(
        config: Any = None,
        resolver: Any = None,
        password: str | None = None,
    ) -> ValueResolvingConfig:
        """
        Build a ValueResolvingConfig with the full resolver chain.

        Parameters
        ----------
        config :
            Override the backing config source (default: ProfileConfigLoader.load()).
        resolver :
            Override the resolver chain.
        password :
            Jasypt decryption password (default: NODE_CONFIG_PASSPHRASE env var or 'changeit').
        """
        placeholder_resolver = PlaceholderResolver(PlaceholderSelector())
        jasypt_prefix = JasyptDecryptor(PrefixSelector("enc."), password)
        jasypt_parens = JasyptDecryptor(ParenthesisSelector("ENC"), password)

        delegating_resolver = resolver or DelegatingResolver(
            [placeholder_resolver, jasypt_prefix, jasypt_parens]
        )

        backing = config if config is not None else ProfileConfigLoader.load()
        value_resolving = ValueResolvingConfig(backing, delegating_resolver)

        # Wire the reference so placeholder resolver can call back into the config
        placeholder_resolver.reference = value_resolving
        return value_resolving

    @staticmethod
    def load_config(**kwargs: Any) -> Any:
        """Convenience alias for ProfileConfigLoader.load()."""
        return ProfileConfigLoader.load(**kwargs)
