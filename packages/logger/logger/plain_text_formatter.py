"""
logger.plain_text_formatter — Formats log entries as plain text.
"""

from __future__ import annotations

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

from datetime import datetime
from typing import Any


class PlainTextFormatter:
    """
    Formats log entries as plain text.

    Output: timestamp:category:level:message[meta]

    Mirrors the JS PlainTextFormatter class.
    """

    def format(
        self,
        timestamp: datetime,
        category: str,
        level: str,
        message: str,
        meta: Any = None,
    ) -> str:
        suffix = str(meta) if meta is not None else ""
        return f"{timestamp.isoformat()}:{category}:{level}:{message}{suffix}"
