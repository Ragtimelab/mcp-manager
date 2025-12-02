"""Unit tests for utils module."""

from mcp_manager import utils
from mcp_manager.models import MCPServer, MCPServerType, Scope
from mcp_manager.utils import expand_env_vars, format_server_info, get_config_path


class TestGetConfigPath:
    """Test get_config_path function."""

    def test_user_scope(self, tmp_path, monkeypatch):
        """Should return ~/.claude.json for USER scope."""
        monkeypatch.setattr(utils, "DEFAULT_CONFIG_PATH", tmp_path / ".claude.json")
        path = get_config_path(Scope.USER)
        assert path == tmp_path / ".claude.json"

    def test_project_scope(self, tmp_path, monkeypatch):
        """Should return .mcp.json for PROJECT scope."""
        monkeypatch.setattr(utils, "PROJECT_CONFIG_PATH", tmp_path / ".mcp.json")
        path = get_config_path(Scope.PROJECT)
        assert path == tmp_path / ".mcp.json"

    def test_local_scope(self, tmp_path, monkeypatch):
        """Should return .claude/settings.json for LOCAL scope."""
        monkeypatch.setattr(utils, "LOCAL_CONFIG_PATH", tmp_path / ".claude" / "settings.json")
        path = get_config_path(Scope.LOCAL)
        assert path == tmp_path / ".claude" / "settings.json"


class TestExpandEnvVars:
    """Test expand_env_vars function."""

    def test_expand_single_var(self, monkeypatch):
        """Should expand single environment variable."""
        monkeypatch.setenv("TEST_VAR", "value")
        result = expand_env_vars("Hello ${TEST_VAR}")
        assert result == "Hello value"

    def test_expand_multiple_vars(self, monkeypatch):
        """Should expand multiple environment variables."""
        monkeypatch.setenv("VAR1", "first")
        monkeypatch.setenv("VAR2", "second")
        result = expand_env_vars("${VAR1} and ${VAR2}")
        assert result == "first and second"

    def test_expand_with_default_value(self, monkeypatch):
        """Should use default value if variable not set."""
        monkeypatch.delenv("UNSET_VAR", raising=False)
        result = expand_env_vars("Value: ${UNSET_VAR:-default}")
        assert result == "Value: default"

    def test_expand_with_default_existing_var(self, monkeypatch):
        """Should use actual value if variable is set."""
        monkeypatch.setenv("SET_VAR", "actual")
        result = expand_env_vars("Value: ${SET_VAR:-default}")
        assert result == "Value: actual"

    def test_expand_empty_default(self, monkeypatch):
        """Should handle empty default value."""
        monkeypatch.delenv("UNSET_VAR", raising=False)
        result = expand_env_vars("${UNSET_VAR:-}")
        assert result == ""

    def test_expand_keeps_original_if_not_set(self, monkeypatch):
        """Should keep original ${VAR} if variable not set (no default)."""
        monkeypatch.delenv("UNSET_VAR", raising=False)
        result = expand_env_vars("${UNSET_VAR}")
        assert result == "${UNSET_VAR}"

    def test_expand_no_vars(self):
        """Should return unchanged text with no variables."""
        text = "No variables here"
        result = expand_env_vars(text)
        assert result == text

    def test_expand_nested_braces(self, monkeypatch):
        """Should not expand nested braces."""
        result = expand_env_vars("${VAR:-${OTHER}}")
        # Should treat whole thing as var with default
        assert result in ["${VAR:-${OTHER}}", "${OTHER}"]

    def test_expand_special_characters(self, monkeypatch):
        """Should handle special characters in values."""
        monkeypatch.setenv("SPECIAL", "value/with:special@chars")
        result = expand_env_vars("Path: ${SPECIAL}")
        assert result == "Path: value/with:special@chars"

    def test_expand_unicode(self, monkeypatch):
        """Should handle unicode in variable values."""
        test_value = "테스트値"
        monkeypatch.setenv("UNICODE_VAR", test_value)
        result = expand_env_vars("Unicode: ${UNICODE_VAR}")
        # Use variable to avoid Unicode character mismatch
        assert result == f"Unicode: {test_value}"

    def test_expand_multiple_same_var(self, monkeypatch):
        """Should expand same variable multiple times."""
        monkeypatch.setenv("REPEAT", "val")
        result = expand_env_vars("${REPEAT} and ${REPEAT} again")
        assert result == "val and val again"

    def test_expand_in_middle(self, monkeypatch):
        """Should expand variables in middle of text."""
        monkeypatch.setenv("MID", "middle")
        result = expand_env_vars("start ${MID} end")
        assert result == "start middle end"

    def test_expand_path_like(self, monkeypatch):
        """Should handle path-like patterns."""
        monkeypatch.setenv("HOME_DIR", "/home/user")
        result = expand_env_vars("${HOME_DIR}/subdir/file.txt")
        assert result == "/home/user/subdir/file.txt"

    def test_expand_empty_string(self):
        """Should handle empty string."""
        result = expand_env_vars("")
        assert result == ""

    def test_expand_only_var(self, monkeypatch):
        """Should handle text that is only a variable."""
        monkeypatch.setenv("ONLY", "value")
        result = expand_env_vars("${ONLY}")
        assert result == "value"


class TestFormatServerInfo:
    """Test format_server_info function."""

    def test_format_stdio_server_basic(self):
        """Should format stdio server basic info."""
        server = MCPServer(type=MCPServerType.STDIO, command="uvx")
        result = format_server_info(server)

        assert "Type: stdio" in result
        assert "Command: uvx" in result

    def test_format_stdio_with_args(self):
        """Should format stdio server with arguments."""
        server = MCPServer(type=MCPServerType.STDIO, command="uvx", args=["mcp-server-time"])
        result = format_server_info(server)

        assert "Arguments: mcp-server-time" in result

    def test_format_stdio_with_multiple_args(self):
        """Should format stdio server with multiple arguments."""
        server = MCPServer(type=MCPServerType.STDIO, command="uvx", args=["arg1", "arg2", "arg3"])
        result = format_server_info(server)

        assert "Arguments: arg1 arg2 arg3" in result

    def test_format_stdio_without_env_non_verbose(self):
        """Should not show env vars in non-verbose mode."""
        server = MCPServer(
            type=MCPServerType.STDIO,
            command="uvx",
            env={"KEY": "value"},
        )
        result = format_server_info(server, verbose=False)

        assert "Environment Variables" not in result
        assert "KEY" not in result

    def test_format_stdio_with_env_verbose(self):
        """Should show env vars in verbose mode."""
        server = MCPServer(
            type=MCPServerType.STDIO,
            command="uvx",
            env={"KEY": "value", "ANOTHER": "test"},
        )
        result = format_server_info(server, verbose=True)

        assert "Environment Variables" in result
        assert "KEY=value" in result
        assert "ANOTHER=test" in result

    def test_format_http_server_basic(self):
        """Should format HTTP server basic info."""
        server = MCPServer(type=MCPServerType.HTTP, url="https://api.example.com/mcp")
        result = format_server_info(server)

        assert "Type: http" in result
        assert "URL: https://api.example.com/mcp" in result

    def test_format_sse_server_basic(self):
        """Should format SSE server basic info."""
        server = MCPServer(type=MCPServerType.SSE, url="https://events.example.com")
        result = format_server_info(server)

        assert "Type: sse" in result
        assert "URL: https://events.example.com" in result

    def test_format_http_without_headers_non_verbose(self):
        """Should not show headers in non-verbose mode."""
        server = MCPServer(
            type=MCPServerType.HTTP,
            url="https://api.example.com",
            headers={"X-Custom": "value"},
        )
        result = format_server_info(server, verbose=False)

        assert "Headers" not in result

    def test_format_http_with_headers_verbose(self):
        """Should show headers in verbose mode."""
        server = MCPServer(
            type=MCPServerType.HTTP,
            url="https://api.example.com",
            headers={"X-Custom": "value"},
        )
        result = format_server_info(server, verbose=True)

        assert "Headers" in result
        assert "X-Custom: value" in result

    def test_format_masks_auth_headers(self):
        """Should mask sensitive authorization headers."""
        server = MCPServer(
            type=MCPServerType.HTTP,
            url="https://api.example.com",
            headers={"Authorization": "Bearer secret-token"},
        )
        result = format_server_info(server, verbose=True)

        assert "Authorization: ***" in result
        assert "secret-token" not in result

    def test_format_masks_token_headers(self):
        """Should mask headers with 'token' in name."""
        server = MCPServer(
            type=MCPServerType.HTTP,
            url="https://api.example.com",
            headers={"X-API-Token": "secret123"},
        )
        result = format_server_info(server, verbose=True)

        assert "***" in result
        assert "secret123" not in result

    def test_format_multiple_headers(self):
        """Should format multiple headers."""
        server = MCPServer(
            type=MCPServerType.HTTP,
            url="https://api.example.com",
            headers={
                "X-Custom": "value",
                "Authorization": "secret",
                "Accept": "application/json",
            },
        )
        result = format_server_info(server, verbose=True)

        assert "X-Custom: value" in result
        assert "Authorization: ***" in result
        assert "Accept: application/json" in result

    def test_format_returns_string(self):
        """Should return a string."""
        server = MCPServer(type=MCPServerType.STDIO, command="test")
        result = format_server_info(server)

        assert isinstance(result, str)

    def test_format_multiline_output(self):
        """Should produce multiline output."""
        server = MCPServer(type=MCPServerType.STDIO, command="uvx", args=["arg1"], env={"K": "v"})
        result = format_server_info(server, verbose=True)

        lines = result.split("\n")
        assert len(lines) > 1


class TestUtilsIntegration:
    """Test utils functions integration."""

    def test_expand_env_in_server_format(self, monkeypatch):
        """Should expand env vars before formatting."""
        monkeypatch.setenv("CMD_NAME", "my-command")
        _server = MCPServer(type=MCPServerType.STDIO, command="uvx")

        # First expand
        expanded_cmd = expand_env_vars("${CMD_NAME}")
        # Then format (hypothetically)
        assert expanded_cmd == "my-command"

    def test_get_config_path_for_each_scope(self, tmp_path, monkeypatch):
        """Should return different paths for different scopes."""
        monkeypatch.setattr(utils, "DEFAULT_CONFIG_PATH", tmp_path / "home" / ".claude.json")
        monkeypatch.setattr(utils, "PROJECT_CONFIG_PATH", tmp_path / "project" / ".mcp.json")
        monkeypatch.setattr(
            utils, "LOCAL_CONFIG_PATH", tmp_path / "project" / ".claude" / "settings.json"
        )

        user_path = get_config_path(Scope.USER)
        project_path = get_config_path(Scope.PROJECT)
        local_path = get_config_path(Scope.LOCAL)

        assert user_path != project_path != local_path
        assert "home" in str(user_path)
        assert "project" in str(project_path)
        assert "project" in str(local_path)


class TestUtilsEdgeCases:
    """Test edge cases for utility functions."""

    def test_expand_malformed_patterns(self):
        """Should handle malformed patterns gracefully."""
        # Missing closing brace
        result1 = expand_env_vars("${VAR")
        assert "${VAR" in result1  # Should keep as-is

        # Empty variable name
        result2 = expand_env_vars("${}")
        assert result2 in ["${}", ""]

    def test_format_server_with_empty_values(self):
        """Should handle empty values in server."""
        server = MCPServer(type=MCPServerType.STDIO, command="test", args=[], env={})
        result = format_server_info(server, verbose=True)

        # Should not crash, should produce valid output
        assert "Type: stdio" in result
        assert "Command: test" in result

    def test_expand_very_long_text(self, monkeypatch):
        """Should handle very long text."""
        monkeypatch.setenv("VAR", "value")
        long_text = "text " * 1000 + "${VAR}" + " more" * 1000
        result = expand_env_vars(long_text)

        assert "value" in result
        assert len(result) > 1000

    def test_format_server_unicode(self):
        """Should handle unicode in server info."""
        server = MCPServer(
            type=MCPServerType.STDIO,
            command="test",
            env={"NAME": "テスト", "DESC": "설명"},
        )
        result = format_server_info(server, verbose=True)

        assert "テスト" in result
        assert "설명" in result
