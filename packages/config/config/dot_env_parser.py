"""
config.dot_env_parser — .env file parser.

Supports the standard .env format used by dotenv and compatible tools:
  KEY=VALUE                           bare value
  export KEY=VALUE                    'export' prefix stripped
  KEY="double quoted"                 double quotes stripped, escape sequences processed
  KEY='single quoted'                 single quotes stripped, no escape processing
  KEY=value # inline comment          inline comment stripped (unquoted values only)
  KEY=                                empty string value
  # comment line                      ignored
  blank lines                         ignored

Keys are kept verbatim (e.g. MY_APP_PORT).
Relaxed binding (MY_APP_PORT → my.app.port) is handled downstream by EnvPropertySource.

Out of scope for v1:
  - Multiline values (backslash-continuation or newlines inside double quotes)
  - Variable interpolation ($VAR or ${VAR})
"""

from __future__ import annotations

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]


class DotEnvParser:
    """
    Parse .env files into a flat key → value dict.

    Mirrors the JS DotEnvParser class.
    """

    @staticmethod
    def parse(text: str) -> dict[str, str]:
        """
        Parse a .env string into a flat key→value object.

        Parameters
        ----------
        text : str
            Raw .env file content.

        Returns
        -------
        dict[str, str]
            Flat plain dict {KEY: 'value', ...}
        """
        result: dict[str, str] = {}
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

        for raw_line in lines:
            line = raw_line.strip()

            # Skip blank lines and comment lines
            if not line or line.startswith("#"):
                continue

            # Strip optional 'export ' prefix
            if line.startswith("export "):
                line = line[7:].lstrip()

            # Find the first '=' separator
            eq_idx = line.find("=")
            if eq_idx == -1:
                # No separator — skip malformed line
                continue

            key = line[:eq_idx].strip()
            if not key:
                continue

            raw_value = line[eq_idx + 1 :]
            result[key] = DotEnvParser._parse_value(raw_value)

        return result

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_value(raw: str) -> str:
        trimmed = raw.lstrip()

        if trimmed.startswith('"'):
            return DotEnvParser._parse_double_quoted(trimmed)
        if trimmed.startswith("'"):
            return DotEnvParser._parse_single_quoted(trimmed)
        return DotEnvParser._parse_unquoted(raw)

    @staticmethod
    def _parse_double_quoted(raw: str) -> str:
        """Strip double quotes and process escape sequences."""
        # raw starts with "
        i = 1
        value = ""
        while i < len(raw):
            ch = raw[i]
            if ch == "\\" and i + 1 < len(raw):
                value += DotEnvParser._unescape(raw[i + 1])
                i += 2
                continue
            if ch == '"':
                # Closing quote — ignore anything after
                break
            value += ch
            i += 1
        return value

    @staticmethod
    def _parse_single_quoted(raw: str) -> str:
        """Strip single quotes, no escape processing."""
        # raw starts with '
        close_idx = raw.find("'", 1)
        if close_idx == -1:
            # Unclosed quote — return everything after the opening quote
            return raw[1:]
        return raw[1:close_idx]

    @staticmethod
    def _parse_unquoted(raw: str) -> str:
        """Strip inline comment (first # preceded by whitespace) and trailing whitespace."""
        i = 0
        while i < len(raw):
            ch = raw[i]
            if ch == "#":
                if i == 0 or raw[i - 1] in (" ", "\t"):
                    return raw[:i].rstrip()
            i += 1
        return raw.rstrip()

    @staticmethod
    def _unescape(ch: str) -> str:
        return {
            "n": "\n",
            "t": "\t",
            "r": "\r",
            "\\": "\\",
            '"': '"',
            "'": "'",
            "$": "$",
        }.get(ch, ch)
