"""
logger.logger_level — Log level constants.

Level ordering mirrors the JS LoggerLevel (fatal=0, debug=5, higher = more verbose).
Python's stdlib uses the inverse (DEBUG=10, CRITICAL=50, higher = more severe).

We define our own ENUMS dict for the is_*_enabled() comparisons (lower = more
severe, same as JS), AND map each level to the corresponding stdlib int so
ConsoleLogger can pass the right level to the underlying stdlib logger.

JS → Python stdlib mapping:
  fatal   → CRITICAL  (50)
  error   → ERROR     (40)
  warn    → WARNING   (30)
  info    → INFO      (20)
  verbose → 15  (custom, between DEBUG and INFO)
  debug   → DEBUG     (10)
"""

from __future__ import annotations

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

import logging

# Register the custom VERBOSE level so stdlib logging knows about it
VERBOSE_INT = 15
logging.addLevelName(VERBOSE_INT, "VERBOSE")


class LoggerLevel:
    """
    Level constants for the alt-python logger.

    ENUMS: name → severity int (fatal=0, debug=5) — used for is_*_enabled() comparisons.
    STDLIB: name → Python stdlib logging int — used when emitting via stdlib.
    """

    FATAL = "fatal"
    ERROR = "error"
    WARN = "warn"
    INFO = "info"
    VERBOSE = "verbose"
    DEBUG = "debug"

    # Severity order: lower number = more severe (same as JS)
    ENUMS: dict[str, int] = {
        "fatal": 0,
        "error": 1,
        "warn": 2,
        "info": 3,
        "verbose": 4,
        "debug": 5,
    }

    # Maps to Python stdlib logging level ints
    STDLIB: dict[str, int] = {
        "fatal": logging.CRITICAL,
        "error": logging.ERROR,
        "warn": logging.WARNING,
        "info": logging.INFO,
        "verbose": VERBOSE_INT,
        "debug": logging.DEBUG,
    }

    @staticmethod
    def from_stdlib(stdlib_level: int) -> str:
        """Convert a stdlib logging int back to a LoggerLevel name."""
        for name, val in LoggerLevel.STDLIB.items():
            if val == stdlib_level:
                return name
        return LoggerLevel.INFO
