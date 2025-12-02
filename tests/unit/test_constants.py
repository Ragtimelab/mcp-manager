"""Unit tests for constants module."""

from pathlib import Path

import pytest

from mcp_manager.constants import (
    ALLOWED_COMMANDS,
    DANGEROUS_ENV_VARS,
    DEFAULT_BACKUP_DIR,
    DEFAULT_CONFIG_PATH,
    DEFAULT_HEALTH_TIMEOUT,
    DEFAULT_LOCK_TIMEOUT,
    LOCAL_CONFIG_PATH,
    PROJECT_CONFIG_PATH,
    RESERVED_NAMES,
    SERVER_NAME_PATTERN,
)


class TestConfigPaths:
    """Test configuration path constants."""

    def test_default_config_path_is_claude_json(self):
        """Default config should be ~/.claude.json."""
        assert DEFAULT_CONFIG_PATH == Path.home() / ".claude.json"

    def test_project_config_path_is_mcp_json(self):
        """Project config should be .mcp.json in current directory."""
        assert PROJECT_CONFIG_PATH == Path.cwd() / ".mcp.json"

    def test_local_config_path_is_in_claude_dir(self):
        """Local config should be .claude/settings.json."""
        assert LOCAL_CONFIG_PATH == Path.cwd() / ".claude" / "settings.json"

    def test_default_backup_dir_is_in_home(self):
        """Backup directory should be in ~/.mcp-manager/backups."""
        assert DEFAULT_BACKUP_DIR == Path.home() / ".mcp-manager" / "backups"


class TestSecurityConstants:
    """Test security-related constants."""

    def test_allowed_commands_contains_expected_tools(self):
        """Allowed commands should include common package managers."""
        expected = {"uvx", "npx", "node", "python", "python3", "docker"}
        assert ALLOWED_COMMANDS == expected

    def test_allowed_commands_is_set(self):
        """Allowed commands should be a set for O(1) lookup."""
        assert isinstance(ALLOWED_COMMANDS, set)

    def test_dangerous_env_vars_contains_path_vars(self):
        """Dangerous env vars should include PATH-like variables."""
        dangerous_vars = {"PATH", "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH"}
        assert dangerous_vars.issubset(DANGEROUS_ENV_VARS)

    def test_dangerous_env_vars_is_set(self):
        """Dangerous env vars should be a set for O(1) lookup."""
        assert isinstance(DANGEROUS_ENV_VARS, set)

    def test_reserved_names_contains_system_names(self):
        """Reserved names should include system-related names."""
        system_names = {"system", "root", "admin"}
        assert system_names.issubset(RESERVED_NAMES)

    def test_reserved_names_is_set(self):
        """Reserved names should be a set for O(1) lookup."""
        assert isinstance(RESERVED_NAMES, set)


class TestValidationPatterns:
    """Test validation pattern constants."""

    def test_server_name_pattern_rejects_uppercase(self):
        """Server name pattern should reject uppercase letters."""
        import re

        pattern = re.compile(SERVER_NAME_PATTERN)
        assert not pattern.match("MyServer")
        assert not pattern.match("MYSERVER")

    def test_server_name_pattern_accepts_lowercase(self):
        """Server name pattern should accept lowercase letters."""
        import re

        pattern = re.compile(SERVER_NAME_PATTERN)
        assert pattern.match("myserver")
        assert pattern.match("my-server")
        assert pattern.match("my_server")

    def test_server_name_pattern_requires_letter_start(self):
        """Server name pattern should require starting with a letter."""
        import re

        pattern = re.compile(SERVER_NAME_PATTERN)
        assert not pattern.match("123server")
        assert not pattern.match("-server")
        assert not pattern.match("_server")
        assert pattern.match("s123")

    def test_server_name_pattern_max_length_64(self):
        """Server name pattern should enforce max length of 64 characters."""
        import re

        pattern = re.compile(SERVER_NAME_PATTERN)
        valid_name = "a" * 64
        invalid_name = "a" * 65

        assert pattern.match(valid_name)
        assert not pattern.match(invalid_name)

    def test_server_name_pattern_allows_hyphens_and_underscores(self):
        """Server name pattern should allow hyphens and underscores."""
        import re

        pattern = re.compile(SERVER_NAME_PATTERN)
        assert pattern.match("my-server")
        assert pattern.match("my_server")
        assert pattern.match("my-server-123")
        assert pattern.match("my_server_123")


class TestTimeoutConstants:
    """Test timeout constants."""

    def test_default_health_timeout_is_positive(self):
        """Health check timeout should be positive."""
        assert DEFAULT_HEALTH_TIMEOUT > 0

    def test_default_lock_timeout_is_positive(self):
        """File lock timeout should be positive."""
        assert DEFAULT_LOCK_TIMEOUT > 0

    def test_health_timeout_is_reasonable(self):
        """Health check timeout should be reasonable (not too long)."""
        assert DEFAULT_HEALTH_TIMEOUT <= 30  # 30 seconds max

    def test_lock_timeout_is_reasonable(self):
        """File lock timeout should be reasonable."""
        assert DEFAULT_LOCK_TIMEOUT <= 10  # 10 seconds max
