"""
tests/test_dot_env_parser.py — DotEnvParser tests mirroring the JS DotEnvParser.spec.js
and ProfileConfigLoader .env integration tests.
"""

from __future__ import annotations

import pytest

from config.dot_env_parser import DotEnvParser
from config.profile_config_loader import ProfileConfigLoader


# ---------------------------------------------------------------------------
# Bare KEY=VALUE
# ---------------------------------------------------------------------------

class TestBareKeyValue:
    def test_simple_key_value(self):
        assert DotEnvParser.parse("KEY=value") == {"KEY": "value"}

    def test_multiple_keys(self):
        result = DotEnvParser.parse("FOO=bar\nBAZ=qux")
        assert result["FOO"] == "bar"
        assert result["BAZ"] == "qux"

    def test_empty_value_produces_empty_string(self):
        assert DotEnvParser.parse("KEY=")["KEY"] == ""

    def test_windows_line_endings(self):
        result = DotEnvParser.parse("FOO=bar\r\nBAZ=qux")
        assert result["FOO"] == "bar"
        assert result["BAZ"] == "qux"

    def test_cr_only_line_endings(self):
        result = DotEnvParser.parse("FOO=bar\rBAZ=qux")
        assert result["FOO"] == "bar"
        assert result["BAZ"] == "qux"


# ---------------------------------------------------------------------------
# Export prefix
# ---------------------------------------------------------------------------

class TestExportPrefix:
    def test_strips_export_prefix(self):
        assert DotEnvParser.parse("export KEY=value")["KEY"] == "value"

    def test_strips_export_with_extra_spacing(self):
        assert DotEnvParser.parse("export   KEY=value")["KEY"] == "value"


# ---------------------------------------------------------------------------
# Double-quoted values
# ---------------------------------------------------------------------------

class TestDoubleQuoted:
    def test_strips_double_quotes(self):
        assert DotEnvParser.parse('KEY="hello world"')["KEY"] == "hello world"

    def test_escape_newline(self):
        assert DotEnvParser.parse('KEY="line1\\nline2"')["KEY"] == "line1\nline2"

    def test_escape_tab(self):
        assert DotEnvParser.parse('KEY="col1\\tcol2"')["KEY"] == "col1\tcol2"

    def test_escape_carriage_return(self):
        assert DotEnvParser.parse('KEY="a\\rb"')["KEY"] == "a\rb"

    def test_escape_backslash(self):
        assert DotEnvParser.parse('KEY="back\\\\slash"')["KEY"] == "back\\slash"

    def test_escape_double_quote(self):
        assert DotEnvParser.parse('KEY="say \\"hi\\""')["KEY"] == 'say "hi"'

    def test_escape_dollar(self):
        assert DotEnvParser.parse('KEY="cost \\$5"')["KEY"] == "cost $5"

    def test_ignores_content_after_closing_quote(self):
        assert DotEnvParser.parse('KEY="val" # ignored comment')["KEY"] == "val"

    def test_empty_double_quoted_value(self):
        assert DotEnvParser.parse('KEY=""')["KEY"] == ""


# ---------------------------------------------------------------------------
# Single-quoted values
# ---------------------------------------------------------------------------

class TestSingleQuoted:
    def test_strips_single_quotes(self):
        assert DotEnvParser.parse("KEY='hello world'")["KEY"] == "hello world"

    def test_no_escape_processing(self):
        assert DotEnvParser.parse("KEY='no\\nescape'")["KEY"] == "no\\nescape"

    def test_literal_backslashes_preserved(self):
        assert DotEnvParser.parse("KEY='back\\\\slash'")["KEY"] == "back\\\\slash"

    def test_hash_inside_single_quotes_not_a_comment(self):
        assert DotEnvParser.parse("KEY='val#notcomment'")["KEY"] == "val#notcomment"

    def test_empty_single_quoted_value(self):
        assert DotEnvParser.parse("KEY=''")["KEY"] == ""


# ---------------------------------------------------------------------------
# Inline comments on unquoted values
# ---------------------------------------------------------------------------

class TestInlineComments:
    def test_strips_comment_preceded_by_space(self):
        assert DotEnvParser.parse("KEY=value # this is a comment")["KEY"] == "value"

    def test_strips_comment_preceded_by_tab(self):
        assert DotEnvParser.parse("KEY=value\t# this is a comment")["KEY"] == "value"

    def test_does_not_strip_embedded_hash(self):
        assert DotEnvParser.parse("KEY=val#embedded")["KEY"] == "val#embedded"

    def test_value_that_is_only_a_comment(self):
        assert DotEnvParser.parse("KEY= # just a comment")["KEY"] == ""


# ---------------------------------------------------------------------------
# Comment and blank lines
# ---------------------------------------------------------------------------

class TestCommentsAndBlanks:
    def test_ignores_comment_lines(self):
        result = DotEnvParser.parse("# this is a comment\nKEY=value")
        assert result["KEY"] == "value"
        assert "# this is a comment" not in result

    def test_ignores_blank_lines(self):
        result = DotEnvParser.parse("\n\nKEY=value\n\n")
        assert result["KEY"] == "value"
        assert len(result) == 1

    def test_ignores_lines_without_separator(self):
        result = DotEnvParser.parse("MALFORMED\nKEY=value")
        assert result["KEY"] == "value"
        assert "MALFORMED" not in result


# ---------------------------------------------------------------------------
# Realistic .env content
# ---------------------------------------------------------------------------

class TestRealisticContent:
    def test_typical_application_env(self):
        content = "\n".join([
            "# Application settings",
            "APP_NAME=MyApp",
            "APP_PORT=3000",
            "",
            "# Database",
            "export DATABASE_URL=postgres://localhost:5432/mydb",
            "DB_POOL_SIZE=10",
            "",
            "# Feature flags",
            "ENABLE_CACHE=true",
            'LOG_LEVEL=info # debug in dev',
            "",
            'SECRET_KEY="super secret value with spaces"',
            "LITERAL_VALUE='no\\nescape here'",
        ])
        result = DotEnvParser.parse(content)
        assert result["APP_NAME"] == "MyApp"
        assert result["APP_PORT"] == "3000"
        assert result["DATABASE_URL"] == "postgres://localhost:5432/mydb"
        assert result["DB_POOL_SIZE"] == "10"
        assert result["ENABLE_CACHE"] == "true"
        assert result["LOG_LEVEL"] == "info"
        assert result["SECRET_KEY"] == "super secret value with spaces"
        assert result["LITERAL_VALUE"] == "no\\nescape here"


# ---------------------------------------------------------------------------
# ProfileConfigLoader .env integration
# ---------------------------------------------------------------------------

class TestProfileConfigLoaderDotEnv:
    def test_loads_default_env_file(self, tmp_path):
        (tmp_path / "application.env").write_text("APP_PORT=9000\n")
        chain = ProfileConfigLoader.load(base_path=str(tmp_path))
        # Relaxed binding: APP_PORT → app.port
        assert chain.get("app.port") == "9000"
        # Direct key also accessible
        assert chain.get("APP_PORT") == "9000"

    def test_env_file_lower_priority_than_process_env(self, tmp_path):
        (tmp_path / "application.env").write_text("APP_PORT=9000\n")
        chain = ProfileConfigLoader.load(
            base_path=str(tmp_path),
            env={"APP_PORT": "7777"},
        )
        assert chain.get("APP_PORT") == "7777"

    def test_profile_env_file_overrides_default_env_file(self, tmp_path):
        (tmp_path / "application.env").write_text("APP_PORT=8080\n")
        (tmp_path / "application-dev.env").write_text("APP_PORT=9090\n")
        chain = ProfileConfigLoader.load(
            base_path=str(tmp_path),
            profiles="dev",
        )
        assert chain.get("APP_PORT") == "9090"

    def test_config_dir_env_file_discovered(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "application.env").write_text("DB_HOST=localhost\n")
        chain = ProfileConfigLoader.load(base_path=str(tmp_path))
        assert chain.get("DB_HOST") == "localhost"

    def test_env_file_with_export_prefix(self, tmp_path):
        (tmp_path / "application.env").write_text(
            "export DATABASE_URL=postgres://localhost/mydb\n"
        )
        chain = ProfileConfigLoader.load(base_path=str(tmp_path))
        assert chain.get("DATABASE_URL") == "postgres://localhost/mydb"

    def test_env_file_with_quoted_value(self, tmp_path):
        (tmp_path / "application.env").write_text(
            'SECRET_KEY="my secret key with spaces"\n'
        )
        chain = ProfileConfigLoader.load(base_path=str(tmp_path))
        assert chain.get("SECRET_KEY") == "my secret key with spaces"

    def test_env_file_higher_priority_than_structured_config_file(self, tmp_path):
        """
        .env files sit above structured files in the precedence chain.
        A key in application.env overrides the same relaxed-bound key in application.json.
        """
        # JSON has server.port = 8080; .env has SERVER_PORT=9090 (relaxes to server.port)
        (tmp_path / "application.json").write_text('{"server": {"port": 8080}}')
        (tmp_path / "application.env").write_text("SERVER_PORT=9090\n")
        chain = ProfileConfigLoader.load(base_path=str(tmp_path))
        # .env / relaxed binding: server.port → "9090" (string, higher priority)
        assert chain.get("server.port") == "9090"
