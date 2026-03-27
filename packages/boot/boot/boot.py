"""
boot.boot — Spring-inspired bootstrap for Python applications.
"""

from __future__ import annotations

_root: dict = {}

BANNER_ART = r"""  ____        _ _        _                                _       _    ____  
 / / /   __ _| | |_     (_) __ ___   ____ _ ___  ___ _ __(_)_ __ | |_  \ \ \
/ / /   / _` | | __|____| |/ _` \ \ / / _` / __|/ __| '__| | '_ \| __|  \ \ \
\ \ \  | (_| | | ||_____| | (_| |\ V / (_| \__ \ (__| |  | | |_) | |_   / / /
 \_\_\  \__,_|_|\__|   _/ |\__,_| \_/ \__,_|___/\___|_|  |_| .__/ \__| /_/_/
                       |__/                                  |_|"""


def _build_banner() -> str:
    try:
        from importlib.metadata import version
        ver = version("alt-python-boot-lib")
    except Exception:
        ver = "(dev)"
    return f"{BANNER_ART}\n   alt-python/boot :: {ver}\n"


def print_banner(config=None, logger=None) -> None:
    mode = "console"
    if config is not None and config.has("boot.banner-mode"):
        mode = config.get("boot.banner-mode")
    if mode == "off":
        return
    banner = _build_banner()
    if mode == "log" and logger is not None:
        logger.info(banner)
    else:
        print(banner)


class Boot:
    @staticmethod
    def detect_config(options=None):
        from config import ConfigFactory
        from config.ephemeral_config import EphemeralConfig
        config_arg = options.get("config") if options else None
        if config_arg is not None:
            if callable(getattr(config_arg, "has", None)) and callable(getattr(config_arg, "get", None)):
                return config_arg
            if isinstance(config_arg, dict):
                return ConfigFactory.get_config(EphemeralConfig(config_arg))
            return ConfigFactory.get_config(config_arg)
        return ConfigFactory.get_config()

    @staticmethod
    def boot(options=None):
        from logger import LoggerFactory, LoggerCategoryCache
        global _root
        config = Boot.detect_config(options)
        lf_arg = (options or {}).get("loggerFactory")
        lcc_arg = (options or {}).get("loggerCategoryCache")
        logger_category_cache = lcc_arg or LoggerCategoryCache()
        logger_factory = lf_arg or LoggerFactory(config, logger_category_cache)
        _root.update({
            "config": config,
            "loggerFactory": logger_factory,
            "loggerCategoryCache": logger_category_cache,
        })
        print_banner(config, logger_factory.get_logger("alt_python.boot"))
        if options and options.get("contexts"):
            from cdi import ApplicationContext, Context, Singleton
            root_ctx = Context([
                Singleton({"reference": config, "name": "config"}),
                Singleton({"reference": logger_factory, "name": "loggerFactory"}),
                Singleton({"reference": logger_category_cache, "name": "loggerCategoryCache"}),
            ])
            run_phase = options.get("run", True)
            if isinstance(run_phase, str):
                run_phase = run_phase.lower() != "false"
            app_ctx = ApplicationContext({
                "contexts": [root_ctx] + list(options["contexts"]),
                "config": config,
            })
            app_ctx.start(run=run_phase)
            return app_ctx
        return None

    @staticmethod
    def test(options=None):
        from config.ephemeral_config import EphemeralConfig
        from config.property_source_chain import PropertySourceChain
        from logger import LoggerCategoryCache
        from logger import CachingLoggerFactory
        config = Boot.detect_config(options)
        test_overlay = EphemeralConfig({"boot": {"banner-mode": "off"}})
        test_config = PropertySourceChain([test_overlay, config])
        cache = LoggerCategoryCache()
        caching_lf = CachingLoggerFactory(test_config, cache)
        Boot.boot({"config": test_config, "loggerFactory": caching_lf, "loggerCategoryCache": cache})

    @staticmethod
    def root(name: str, default=None):
        return _root.get(name, default)
