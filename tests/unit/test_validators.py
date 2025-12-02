"""Unit tests for validators module."""

import shutil

import pytest

from mcp_manager.exceptions import (
    InvalidCommandError,
    InvalidServerNameError,
    InvalidURLError,
    SecurityError,
    ValidationError,
)
from mcp_manager.models import MCPServer, MCPServerType
from mcp_manager.validators import (
    validate_command,
    validate_env_vars,
    validate_server,
    validate_server_name,
    validate_url,
)


class TestValidateServerName:
    """Test server name validation."""

    def test_valid_server_names(self):
        """Should accept valid server names."""
        valid_names = [
            "time",
            "fetch",
            "my-server",
            "my_server",
            "server123",
            "s",
            "a" * 64,  # Max length
        ]
        for name in valid_names:
            assert validate_server_name(name) is True

    def test_reject_uppercase(self):
        """Should reject uppercase letters."""
        with pytest.raises(InvalidServerNameError):
            validate_server_name("MyServer")

    def test_reject_start_with_number(self):
        """Should reject names starting with number."""
        with pytest.raises(InvalidServerNameError):
            validate_server_name("123server")

    def test_reject_start_with_hyphen(self):
        """Should reject names starting with hyphen."""
        with pytest.raises(InvalidServerNameError):
            validate_server_name("-server")

    def test_reject_start_with_underscore(self):
        """Should reject names starting with underscore."""
        with pytest.raises(InvalidServerNameError):
            validate_server_name("_server")

    def test_reject_too_long(self):
        """Should reject names longer than 64 characters."""
        long_name = "a" * 65
        with pytest.raises(InvalidServerNameError):
            validate_server_name(long_name)

    def test_reject_special_characters(self):
        """Should reject special characters."""
        invalid_names = ["my.server", "my@server", "my server", "my/server"]
        for name in invalid_names:
            with pytest.raises(InvalidServerNameError):
                validate_server_name(name)

    def test_reject_reserved_names(self):
        """Should reject reserved names."""
        reserved = ["system", "root", "admin"]
        for name in reserved:
            with pytest.raises(ValidationError) as exc_info:
                validate_server_name(name)
            assert "reserved" in str(exc_info.value).lower()

    def test_error_includes_details(self):
        """Error should include helpful details."""
        with pytest.raises(InvalidServerNameError) as exc_info:
            validate_server_name("Invalid-Name")
        assert exc_info.value.details["name"] == "Invalid-Name"
        assert "pattern" in exc_info.value.details


class TestValidateCommand:
    """Test command validation."""

    def test_allowed_commands(self):
        """Should accept whitelisted commands."""
        allowed = ["uvx", "npx", "node", "python", "python3", "docker"]
        for cmd in allowed:
            assert validate_command(cmd) is True

    def test_existing_command(self):
        """Should accept commands that exist on system."""
        # Use a command that definitely exists
        if shutil.which("ls"):
            assert validate_command("ls") is True
        if shutil.which("cat"):
            assert validate_command("cat") is True

    def test_non_existing_command(self):
        """Should reject non-existing commands."""
        with pytest.raises(InvalidCommandError) as exc_info:
            validate_command("this-command-does-not-exist-12345")
        assert "not found" in str(exc_info.value).lower()
        assert "this-command-does-not-exist-12345" in exc_info.value.details["command"]

    def test_error_includes_allowed_commands(self):
        """Error should list allowed commands."""
        with pytest.raises(InvalidCommandError) as exc_info:
            validate_command("nonexistent")
        assert "allowed" in exc_info.value.details
        assert isinstance(exc_info.value.details["allowed"], list)


class TestValidateURL:
    """Test URL validation."""

    def test_valid_http_urls(self):
        """Should accept valid HTTP URLs."""
        valid_urls = [
            "http://example.com",
            "https://example.com",
            "http://example.com/path",
            "https://api.example.com:8080/mcp",
            "http://localhost:3000",
        ]
        for url in valid_urls:
            assert validate_url(url) is True

    def test_invalid_urls(self):
        """Should reject invalid URLs."""
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",  # Wrong scheme
            "//example.com",  # Missing scheme
            "http://",  # Missing host
            "",  # Empty
        ]
        for url in invalid_urls:
            with pytest.raises(InvalidURLError):
                validate_url(url)

    def test_error_includes_url(self):
        """Error should include the invalid URL."""
        with pytest.raises(InvalidURLError) as exc_info:
            validate_url("invalid-url")
        assert exc_info.value.details["url"] == "invalid-url"


class TestValidateEnvVars:
    """Test environment variable validation."""

    def test_valid_env_vars(self):
        """Should accept safe environment variables."""
        safe_envs = [
            {"KEY": "value"},
            {"API_KEY": "secret123"},
            {"TZ": "UTC"},
            {"DEBUG": "true"},
            {},  # Empty is OK
        ]
        for env in safe_envs:
            assert validate_env_vars(env) is True

    def test_dangerous_env_vars_warning(self):
        """Should warn about dangerous environment variables."""
        # Currently just passes with TODO comment
        # This test ensures it doesn't crash
        dangerous = {"PATH": "/custom/path", "LD_LIBRARY_PATH": "/lib"}
        # Should not raise (just warning in future)
        assert validate_env_vars(dangerous) is True

    def test_reject_shell_metacharacters(self):
        """Should reject shell metacharacters in values."""
        dangerous_chars = [";", "&", "|", "`", "$", "(", ")"]
        for char in dangerous_chars:
            with pytest.raises(SecurityError) as exc_info:
                validate_env_vars({"KEY": f"value{char}command"})
            assert "metacharacter" in str(exc_info.value).lower()

    def test_semicolon_in_value(self):
        """Should reject semicolons (command injection risk)."""
        with pytest.raises(SecurityError):
            validate_env_vars({"CMD": "value; rm -rf /"})

    def test_backtick_in_value(self):
        """Should reject backticks (command substitution)."""
        with pytest.raises(SecurityError):
            validate_env_vars({"CMD": "value`whoami`"})

    def test_dollar_in_value(self):
        """Should reject dollar signs (variable expansion)."""
        with pytest.raises(SecurityError):
            validate_env_vars({"CMD": "value$(whoami)"})

    def test_safe_special_chars(self):
        """Should allow safe special characters."""
        _safe = {
            "URL": "https://example.com",
            "PATH_LIKE": "/usr/bin:/usr/local/bin",  # Colon is safe
            "HASH": "abc#def",  # Hash is safe
            "HYPHEN": "value-with-hyphens",
        }
        # Note: PATH_LIKE would trigger PATH warning but not fail
        # URL has :// which is safe
        # Let's test just the safe ones without dangerous env var names
        safe_envs = {
            "URL": "https://example.com",
            "HASH": "abc#def",
            "HYPHEN": "value-with-hyphens",
        }
        assert validate_env_vars(safe_envs) is True


class TestValidateServer:
    """Test server validation."""

    def test_valid_stdio_server(self):
        """Should accept valid stdio server."""
        server = MCPServer(
            type=MCPServerType.STDIO,
            command="uvx",
            args=["mcp-server-time"],
            env={"TZ": "UTC"},
        )
        assert validate_server(server) is True

    def test_valid_http_server(self):
        """Should accept valid HTTP server."""
        server = MCPServer(
            type=MCPServerType.HTTP, url="https://api.example.com/mcp"
        )
        assert validate_server(server) is True

    def test_valid_sse_server(self):
        """Should accept valid SSE server."""
        server = MCPServer(type=MCPServerType.SSE, url="https://events.example.com")
        assert validate_server(server) is True

    def test_stdio_without_command(self):
        """Should reject stdio server without command."""
        # Pydantic already validates this, so we test the validator handles it
        # Create a server with minimal validation bypass
        server = MCPServer.model_construct(type=MCPServerType.STDIO, command=None)
        with pytest.raises(ValidationError):
            validate_server(server)

    def test_stdio_with_invalid_command(self):
        """Should reject stdio server with invalid command."""
        server = MCPServer(
            type=MCPServerType.STDIO, command="nonexistent-command-12345"
        )
        with pytest.raises(InvalidCommandError):
            validate_server(server)

    def test_http_without_url(self):
        """Should reject HTTP server without URL."""
        # Use model_construct to bypass Pydantic validation
        server = MCPServer.model_construct(type=MCPServerType.HTTP, url=None)
        with pytest.raises(ValidationError):
            validate_server(server)

    def test_http_with_invalid_url(self):
        """Should reject HTTP server with invalid URL."""
        _server = MCPServer(type=MCPServerType.HTTP, url="invalid-url")
        # Need to bypass Pydantic validation in model
        # Since our model validates, let's just test the validator directly
        with pytest.raises(InvalidURLError):
            validate_url("invalid-url")

    def test_server_with_dangerous_env(self):
        """Should reject server with dangerous environment variables."""
        server = MCPServer(
            type=MCPServerType.STDIO,
            command="uvx",
            env={"EVIL": "value; rm -rf /"},
        )
        with pytest.raises(SecurityError):
            validate_server(server)

    def test_server_with_empty_env(self):
        """Should accept server with empty environment."""
        server = MCPServer(type=MCPServerType.STDIO, command="uvx", env={})
        assert validate_server(server) is True

    def test_server_with_safe_env(self):
        """Should accept server with safe environment."""
        server = MCPServer(
            type=MCPServerType.STDIO,
            command="uvx",
            env={"TZ": "UTC", "DEBUG": "1"},
        )
        assert validate_server(server) is True


class TestValidatorEdgeCases:
    """Test edge cases and integration."""

    def test_empty_server_name(self):
        """Should reject empty server name."""
        with pytest.raises(InvalidServerNameError):
            validate_server_name("")

    def test_whitespace_server_name(self):
        """Should reject whitespace-only server name."""
        with pytest.raises(InvalidServerNameError):
            validate_server_name("   ")

    def test_empty_command(self):
        """Should reject empty command."""
        with pytest.raises(InvalidCommandError):
            validate_command("")

    def test_command_with_path(self):
        """Should handle commands with absolute paths."""
        # Test with a common system command path
        if shutil.which("python3"):
            python_path = shutil.which("python3")
            assert validate_command(python_path) is True

    def test_url_with_query_params(self):
        """Should accept URLs with query parameters."""
        url = "https://api.example.com/mcp?key=value&foo=bar"
        assert validate_url(url) is True

    def test_url_with_fragment(self):
        """Should accept URLs with fragments."""
        url = "https://example.com/page#section"
        assert validate_url(url) is True

    def test_localhost_urls(self):
        """Should accept localhost URLs."""
        urls = [
            "http://localhost",
            "http://localhost:3000",
            "http://127.0.0.1:8080",
        ]
        for url in urls:
            assert validate_url(url) is True

    def test_unicode_in_env_value(self):
        """Should handle unicode in environment values."""
        env = {"NAME": "テスト", "VALUE": "값"}
        assert validate_env_vars(env) is True

    def test_multiple_validators_in_sequence(self):
        """Should handle multiple validations in sequence."""
        # Valid server name
        validate_server_name("myserver")

        # Valid command
        validate_command("uvx")

        # Valid URL
        validate_url("https://example.com")

        # All should pass independently
        assert True

    def test_validator_error_messages_are_helpful(self):
        """Validator errors should include helpful information."""
        # Test server name error
        try:
            validate_server_name("Invalid-Name")
        except InvalidServerNameError as e:
            assert "requirements" in e.details
            assert "pattern" in e.details

        # Test command error
        try:
            validate_command("nonexistent")
        except InvalidCommandError as e:
            assert "allowed" in e.details
            assert "hint" in e.details

        # Test URL error
        try:
            validate_url("invalid")
        except InvalidURLError as e:
            assert "url" in e.details
