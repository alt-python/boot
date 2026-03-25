"""
config.properties_parser — Java .properties file parser.

Supports:
  - key=value, key:value, key value separators
  - # and ! comments; blank lines skipped
  - backslash line continuation
  - dotted keys → nested dicts: a.b.c=1 → {'a': {'b': {'c': '1'}}}
  - array notation: a.b[0]=x, a.b[1]=y → {'a': {'b': ['x', 'y']}}
  - array of objects: a.b[0].x=1, a.b[0].y=2 → {'a': {'b': [{'x': '1', 'y': '2'}]}}
  - Unicode escapes: \\uXXXX
  - Standard escapes: \\n, \\t, \\r, \\\\, \\=, \\:
"""

from __future__ import annotations

import re


class PropertiesParser:
    """
    Parser for Java .properties files.

    Mirrors the JS PropertiesParser class.
    """

    @staticmethod
    def parse(text: str) -> dict:
        lines = PropertiesParser._join_continuation_lines(text)
        flat: dict = {}

        for line in lines:
            trimmed = line.strip()
            if not trimmed or trimmed.startswith("#") or trimmed.startswith("!"):
                continue
            key, value = PropertiesParser._parse_line(trimmed)
            if key is not None:
                flat[key] = value

        return PropertiesParser._unflatten(flat)

    # ------------------------------------------------------------------
    # Line joining
    # ------------------------------------------------------------------

    @staticmethod
    def _join_continuation_lines(text: str) -> list[str]:
        raw = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        result: list[str] = []
        current = ""
        trim_next = False

        for line in raw:
            trailing = 0
            for ch in reversed(line):
                if ch == "\\":
                    trailing += 1
                else:
                    break
            if trailing % 2 == 1:
                current += line[:-1]
                # leading whitespace of continuation stripped per .properties spec
                trim_next = True
            else:
                if trim_next:
                    line = line.lstrip()
                    trim_next = False
                current += line
                result.append(current)
                current = ""
        if current:
            result.append(current)
        return result

    # ------------------------------------------------------------------
    # Line parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_line(line: str) -> tuple[str | None, str | None]:
        i = 0
        n = len(line)
        key = ""

        # Skip leading whitespace
        while i < n and line[i] in (" ", "\t"):
            i += 1

        # Read key
        while i < n:
            ch = line[i]
            if ch == "\\" and i + 1 < n:
                key += PropertiesParser._unescape(line[i + 1])
                i += 2
                continue
            if ch in ("=", ":"):
                i += 1
                break
            if ch in (" ", "\t"):
                # whitespace separator: skip whitespace, then optional = or :
                while i < n and line[i] in (" ", "\t"):
                    i += 1
                if i < n and line[i] in ("=", ":"):
                    i += 1
                break
            key += ch
            i += 1

        if not key:
            return None, None

        # Skip leading whitespace in value
        while i < n and line[i] in (" ", "\t"):
            i += 1

        # Read value
        value = ""
        while i < n:
            ch = line[i]
            if ch == "\\" and i + 1 < n:
                if line[i + 1] == "u" and i + 5 < n:
                    hex_str = line[i + 2 : i + 6]
                    if re.match(r"^[0-9a-fA-F]{4}$", hex_str):
                        value += chr(int(hex_str, 16))
                        i += 6
                        continue
                value += PropertiesParser._unescape(line[i + 1])
                i += 2
                continue
            value += ch
            i += 1

        return key, value

    @staticmethod
    def _unescape(ch: str) -> str:
        return {
            "n": "\n",
            "t": "\t",
            "r": "\r",
            "\\": "\\",
            "=": "=",
            ":": ":",
            " ": " ",
        }.get(ch, ch)

    # ------------------------------------------------------------------
    # Unflatten
    # ------------------------------------------------------------------

    @staticmethod
    def _unflatten(flat: dict) -> dict:
        root: dict = {}
        for dotted_key, value in flat.items():
            segments = PropertiesParser._parse_key_path(dotted_key)
            current: Any = root

            for i, seg in enumerate(segments):
                is_last = i == len(segments) - 1
                key_part = seg["key"]
                idx = seg.get("index")

                if idx is not None:
                    # Array segment
                    if key_part not in current:
                        current[key_part] = []
                    arr = current[key_part]
                    if is_last:
                        # Extend list if needed
                        while len(arr) <= idx:
                            arr.append(None)
                        arr[idx] = value
                    else:
                        while len(arr) <= idx:
                            arr.append(None)
                        if arr[idx] is None:
                            arr[idx] = {}
                        current = arr[idx]
                else:
                    if is_last:
                        current[key_part] = value
                    else:
                        if key_part not in current:
                            current[key_part] = {}
                        current = current[key_part]

        return root

    @staticmethod
    def _parse_key_path(dotted_key: str) -> list[dict]:
        segments = []
        for part in dotted_key.split("."):
            m = re.match(r"^([^\[]+)\[(\d+)\]$", part)
            if m:
                segments.append({"key": m.group(1), "index": int(m.group(2))})
            else:
                segments.append({"key": part})
        return segments


# type alias used inside _unflatten
Any = object
