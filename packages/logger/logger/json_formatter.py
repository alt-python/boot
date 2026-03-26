"""
logger.json_formatter — Formats log entries as JSON strings.
"""

from __future__ import annotations

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

import json
from datetime import datetime
from typing import Any

from common import is_plain_object


class JSONFormatter:
    """
    Formats log entries as JSON strings.

    Output: {"level": ..., "message": ..., "timestamp": ..., "category": ..., [meta fields]}

    Mirrors the JS JSONFormatter class.
    """

    def format(
        self,
        timestamp: datetime,
        category: str,
        level: str,
        message: str,
        meta: Any = None,
    ) -> str:
        record: dict[str, Any] = {
            "level": level,
            "message": message,
            "timestamp": timestamp.isoformat(),
            "category": category,
        }
        if is_plain_object(meta):
            record.update(meta)
        elif meta is not None:
            record["meta"] = meta
        return json.dumps(record)
