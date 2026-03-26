"""
example-1-2-intro-logger

Introduces alt-python/logger alongside config.

Key concepts:
  - ``from logger import logger_factory`` gives a default LoggerFactory backed by
    the default config
  - Category string mirrors Java's package.ClassName convention — used for level filtering
  - Log format (text/JSON) and level controlled by config
  - Class-level qualifier gives the logger a stable, meaningful category name

Run:
  python main.py                                   # text logs, debug level for this category
  PY_ACTIVE_PROFILES=dev python main.py            # text logs, warn level (debug/info suppressed)
  PY_ACTIVE_PROFILES=json-log python main.py       # JSON log lines
"""

from config import config
from logger import logger_factory

# Get a logger for this module using a qualified category name.
# The category controls which log level config entry applies.
logger = logger_factory.get_logger("alt_python.example_1_2_intro_logger.main")

logger.debug("Config loaded — debug visible when level is debug")
logger.info(f"App: {config.get('app.name')}")
logger.info(f"Log format: {config.get('logging.format', 'text')}")
logger.warn("This is a warning")
logger.error("This is an error")

# Category-specific level filtering
svc_logger = logger_factory.get_logger("alt_python.example_1_2_intro_logger.MyService")
svc_logger.debug("MyService debug — filtered by category level")
svc_logger.info("MyService info — visible at info+")
