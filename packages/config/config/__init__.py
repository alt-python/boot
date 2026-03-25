"""
config — Spring-inspired profile-aware config for Python.

Quick start::

    from config import config

    name = config.get('app.name')
    port = config.get('server.port', 8080)

    # Load with explicit base path or overrides
    from config import ConfigFactory
    cfg = ConfigFactory.get_config()

Profile-aware file discovery (PY_ACTIVE_PROFILES env var):
  application.properties / application.yaml / application.json / application.env
  application-{profile}.properties / etc.

Transparent value resolution:
  ${path}           → placeholder substitution
  enc.<b64>         → jasypt PBE decryption
  ENC(<b64>)        → jasypt PBE decryption (Spring-style)
"""

from config.ephemeral_config import EphemeralConfig
from config.property_source_chain import PropertySourceChain
from config.env_property_source import EnvPropertySource
from config.properties_parser import PropertiesParser
from config.dot_env_parser import DotEnvParser
from config.profile_config_loader import ProfileConfigLoader
from config.selector import Selector, PrefixSelector, ParenthesisSelector, PlaceholderSelector
from config.resolver import Resolver, SelectiveResolver, DelegatingResolver
from config.placeholder_resolver import PlaceholderResolver
from config.jasypt_decryptor import JasyptDecryptor
from config.value_resolving_config import ValueResolvingConfig
from config.config_factory import ConfigFactory

# Module-level singleton backed by ProfileConfigLoader — zero setup required.
config = ConfigFactory.get_config()

__all__ = [
    "EphemeralConfig",
    "PropertySourceChain",
    "EnvPropertySource",
    "PropertiesParser",
    "DotEnvParser",
    "ProfileConfigLoader",
    "Selector",
    "PrefixSelector",
    "ParenthesisSelector",
    "PlaceholderSelector",
    "Resolver",
    "SelectiveResolver",
    "DelegatingResolver",
    "PlaceholderResolver",
    "JasyptDecryptor",
    "ValueResolvingConfig",
    "ConfigFactory",
    "config",
]
