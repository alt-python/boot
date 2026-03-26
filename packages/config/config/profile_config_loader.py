"""
config.profile_config_loader — Spring Boot-style profile-aware config file loader.

Precedence (highest → lowest):
  1. Programmatic overrides (passed as dict)
  2. Environment variables (with relaxed binding)
  3. Profile-specific .env files: application-{profile}.env
     (later profiles override earlier ones)
  4. Default .env file: application.env
  5. Profile-specific files: application-{profile}.{properties,yaml,yml,json}
     (later profiles override earlier ones)
  6. Default files: application.{properties,yaml,yml,json}
  7. Fallback config (explicit dict or config-like object)

File search locations (in order): config/, cwd
.env files are treated as environment variable sources — relaxed binding applies.
PY_ACTIVE_PROFILES: comma-separated list of active profiles.
"""

from __future__ import annotations

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

import json
import os
from pathlib import Path
from typing import Any

from config.ephemeral_config import EphemeralConfig
from config.env_property_source import EnvPropertySource
from config.property_source_chain import PropertySourceChain
from config.properties_parser import PropertiesParser
from config.dot_env_parser import DotEnvParser


class ProfileConfigLoader:
    FORMATS = [".properties", ".yaml", ".yml", ".json"]
    SEARCH_DIRS = ["config", "."]

    @staticmethod
    def load(
        overrides: dict | None = None,
        fallback: Any = None,
        base_path: str | None = None,
        profiles: str | None = None,
        env: dict | None = None,
        name: str = "application",
    ) -> PropertySourceChain:
        """
        Load config with Spring-aligned precedence.

        Parameters
        ----------
        overrides : dict, optional
            Programmatic overrides (highest priority).
        fallback : dict or config-like, optional
            Fallback config (lowest priority).
        base_path : str, optional
            Base directory for file discovery (default: cwd).
        profiles : str, optional
            Comma-separated profile names (default: PY_ACTIVE_PROFILES env var).
        env : dict, optional
            Environment variables to use (default: os.environ).
        name : str
            Config file base name (default: 'application').
        """
        _env = env if env is not None else dict(os.environ)
        _base = Path(base_path) if base_path else Path.cwd()
        _profiles_str = profiles or _env.get("PY_ACTIVE_PROFILES", "")
        _profiles = [p.strip() for p in _profiles_str.split(",") if p.strip()]

        sources: list = []

        # 1. Programmatic overrides
        if overrides:
            sources.append(EphemeralConfig(overrides))

        # 2. Environment variables
        sources.append(EnvPropertySource(_env))

        # 3. Profile-specific .env files (later profiles = higher priority, so reverse)
        for profile in reversed(_profiles):
            sources.extend(ProfileConfigLoader._load_env_files(_base, f"{name}-{profile}"))

        # 4. Default .env file
        sources.extend(ProfileConfigLoader._load_env_files(_base, name))

        # 5. Profile-specific config files (later profiles = higher priority, so reverse)
        for profile in reversed(_profiles):
            profile_sources = ProfileConfigLoader._load_files(_base, f"{name}-{profile}")
            sources.extend(profile_sources)

        # 6. Default application files
        sources.extend(ProfileConfigLoader._load_files(_base, name))

        # 5. Fallback
        if fallback is not None:
            if hasattr(fallback, "has") and hasattr(fallback, "get"):
                sources.append(fallback)
            else:
                sources.append(EphemeralConfig(fallback))

        return PropertySourceChain(sources)

    @staticmethod
    def _load_env_files(base_path: Path, base_name: str) -> list:
        """
        Discover and load .env files for a given base name across search directories.
        Returns a list of EnvPropertySource instances (one per file found).

        Parsed with DotEnvParser — keys kept verbatim (UPPER_SNAKE_CASE).
        Relaxed binding (MY_APP_PORT → my.app.port) is applied by EnvPropertySource.
        """
        sources: list = []
        for search_dir in ProfileConfigLoader.SEARCH_DIRS:
            file_path = base_path / search_dir / f"{base_name}.env"
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                parsed = DotEnvParser.parse(content)
                sources.append(EnvPropertySource(parsed))
        return sources

    @staticmethod
    def _load_files(base_path: Path, base_name: str) -> list:
        sources: list = []
        for search_dir in ProfileConfigLoader.SEARCH_DIRS:
            for ext in ProfileConfigLoader.FORMATS:
                file_path = base_path / search_dir / f"{base_name}{ext}"
                data = ProfileConfigLoader._load_file(file_path, ext)
                if data is not None:
                    sources.append(EphemeralConfig(data))
        return sources

    @staticmethod
    def _load_file(file_path: Path, ext: str) -> dict | None:
        if not file_path.exists():
            return None
        content = file_path.read_text(encoding="utf-8")
        if ext == ".json":
            return json.loads(content)
        if ext in (".yaml", ".yml"):
            return ProfileConfigLoader._load_yaml(content)
        if ext == ".properties":
            return PropertiesParser.parse(content)
        return None

    _yaml_parser: Any = None

    @staticmethod
    def set_yaml_parser(parser: Any) -> None:
        ProfileConfigLoader._yaml_parser = parser

    @staticmethod
    def _load_yaml(content: str) -> dict:
        if ProfileConfigLoader._yaml_parser is not None:
            return ProfileConfigLoader._yaml_parser.safe_load(content)
        try:
            import yaml  # type: ignore[import]
            ProfileConfigLoader._yaml_parser = yaml
            return yaml.safe_load(content)
        except ImportError:
            raise ImportError(
                "YAML config files require PyYAML. Install it: pip install PyYAML"
            )
