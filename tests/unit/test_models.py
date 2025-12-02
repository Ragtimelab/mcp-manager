"""Unit tests for models module."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from mcp_manager.models import Backup, Config, MCPServer, MCPServerType, Scope


class TestEnums:
    """Test enum definitions."""

    def test_mcp_server_type_values(self):
        """MCPServerType should have correct values."""
        assert MCPServerType.STDIO == "stdio"
        assert MCPServerType.SSE == "sse"
        assert MCPServerType.HTTP == "http"

    def test_mcp_server_type_is_string_enum(self):
        """MCPServerType should be string enum."""
        assert isinstance(MCPServerType.STDIO, str)
        assert isinstance(MCPServerType.SSE, str)
        assert isinstance(MCPServerType.HTTP, str)

    def test_scope_values(self):
        """Scope should have correct values."""
        assert Scope.USER == "user"
        assert Scope.PROJECT == "project"
        assert Scope.LOCAL == "local"

    def test_scope_is_string_enum(self):
        """Scope should be string enum."""
        assert isinstance(Scope.USER, str)
        assert isinstance(Scope.PROJECT, str)
        assert isinstance(Scope.LOCAL, str)


class TestMCPServerModel:
    """Test MCPServer model."""

    def test_create_stdio_server(self):
        """Should create valid stdio server."""
        server = MCPServer(
            type=MCPServerType.STDIO,
            command="uvx",
            args=["mcp-server-time"],
            env={"TZ": "UTC"},
        )
        assert server.type == "stdio"
        assert server.command == "uvx"
        assert server.args == ["mcp-server-time"]
        assert server.env == {"TZ": "UTC"}
        assert server.url is None
        assert server.headers == {}

    def test_create_http_server(self):
        """Should create valid HTTP server."""
        server = MCPServer(
            type=MCPServerType.HTTP,
            url="https://api.example.com/mcp",
            headers={"Authorization": "Bearer token"},
        )
        assert server.type == "http"
        assert server.url == "https://api.example.com/mcp"
        assert server.headers == {"Authorization": "Bearer token"}
        assert server.command is None
        assert server.args == []
        assert server.env == {}

    def test_create_sse_server(self):
        """Should create valid SSE server."""
        server = MCPServer(
            type=MCPServerType.SSE, url="https://events.example.com/mcp"
        )
        assert server.type == "sse"
        assert server.url == "https://events.example.com/mcp"

    def test_stdio_requires_command(self):
        """Stdio server should require command field."""
        with pytest.raises(ValidationError) as exc_info:
            MCPServer(type=MCPServerType.STDIO, command=None)

        errors = str(exc_info.value).lower()
        assert "command" in errors or "stdio" in errors

    def test_http_requires_url(self):
        """HTTP server should require url field."""
        with pytest.raises(ValidationError) as exc_info:
            MCPServer(type=MCPServerType.HTTP, url=None)

        errors = str(exc_info.value).lower()
        assert "url" in errors or "http" in errors

    def test_sse_requires_url(self):
        """SSE server should require url field."""
        with pytest.raises(ValidationError) as exc_info:
            MCPServer(type=MCPServerType.SSE, url=None)

        errors = str(exc_info.value).lower()
        assert "url" in errors or "sse" in errors

    def test_default_values(self):
        """Should have correct default values."""
        server = MCPServer(type=MCPServerType.STDIO, command="test")
        assert server.args == []
        assert server.env == {}
        assert server.url is None
        assert server.headers == {}

    def test_enum_values_in_output(self):
        """Should use enum values in model output."""
        server = MCPServer(type=MCPServerType.STDIO, command="test")
        data = server.model_dump()
        assert data["type"] == "stdio"
        assert isinstance(data["type"], str)

    def test_model_serialization(self):
        """Should serialize to JSON-compatible dict."""
        server = MCPServer(
            type=MCPServerType.STDIO,
            command="uvx",
            args=["mcp-server-time"],
            env={"KEY": "value"},
        )
        data = server.model_dump(mode="json")
        assert data == {
            "type": "stdio",
            "command": "uvx",
            "args": ["mcp-server-time"],
            "env": {"KEY": "value"},
            "url": None,
            "headers": {},
        }

    def test_model_deserialization(self):
        """Should deserialize from dict."""
        data = {
            "type": "stdio",
            "command": "uvx",
            "args": ["mcp-server-time"],
            "env": {"KEY": "value"},
        }
        server = MCPServer(**data)
        assert server.type == "stdio"
        assert server.command == "uvx"
        assert server.args == ["mcp-server-time"]
        assert server.env == {"KEY": "value"}

    def test_validate_assignment(self):
        """Should validate on field assignment."""
        server = MCPServer(type=MCPServerType.STDIO, command="test")
        # This should work since validate_assignment is enabled
        server.env = {"NEW": "value"}
        assert server.env == {"NEW": "value"}


class TestConfigModel:
    """Test Config model."""

    def test_create_empty_config(self):
        """Should create empty config."""
        config = Config()
        assert config.mcpServers == {}

    def test_create_config_with_servers(self):
        """Should create config with servers."""
        config = Config(
            mcpServers={
                "time": MCPServer(
                    type=MCPServerType.STDIO,
                    command="uvx",
                    args=["mcp-server-time"],
                ),
                "fetch": MCPServer(
                    type=MCPServerType.STDIO,
                    command="uvx",
                    args=["mcp-server-fetch"],
                ),
            }
        )
        assert len(config.mcpServers) == 2
        assert "time" in config.mcpServers
        assert "fetch" in config.mcpServers

    def test_config_allows_extra_fields(self):
        """Config should preserve unknown fields."""
        data = {
            "mcpServers": {},
            "unknownField": "preserved",
            "anotherField": 123,
        }
        config = Config(**data)
        # Pydantic v2 stores extra fields separately
        assert hasattr(config, "unknownField") or "unknownField" in config.model_extra

    def test_config_serialization(self):
        """Should serialize config with servers."""
        config = Config(
            mcpServers={
                "time": MCPServer(
                    type=MCPServerType.STDIO,
                    command="uvx",
                    args=["mcp-server-time"],
                )
            }
        )
        data = config.model_dump(mode="json")
        assert "mcpServers" in data
        assert "time" in data["mcpServers"]
        assert data["mcpServers"]["time"]["type"] == "stdio"

    def test_config_deserialization(self):
        """Should deserialize config from dict."""
        data = {
            "mcpServers": {
                "time": {
                    "type": "stdio",
                    "command": "uvx",
                    "args": ["mcp-server-time"],
                    "env": {},
                }
            }
        }
        config = Config(**data)
        assert "time" in config.mcpServers
        assert isinstance(config.mcpServers["time"], MCPServer)
        assert config.mcpServers["time"].command == "uvx"


class TestBackupModel:
    """Test Backup model."""

    def test_create_backup(self):
        """Should create backup with config."""
        config = Config(mcpServers={})
        backup = Backup(config=config)
        assert backup.config == config
        assert isinstance(backup.timestamp, datetime)
        assert backup.metadata == {}

    def test_backup_with_metadata(self):
        """Should create backup with metadata."""
        config = Config()
        metadata = {"reason": "manual backup", "user": "testuser"}
        backup = Backup(config=config, metadata=metadata)
        assert backup.metadata == metadata

    def test_backup_id_format(self):
        """Backup ID should be formatted timestamp."""
        config = Config()
        timestamp = datetime(2024, 12, 2, 14, 30, 45)
        backup = Backup(config=config, timestamp=timestamp)
        assert backup.backup_id == "20241202-143045"

    def test_backup_id_is_property(self):
        """Backup ID should be read-only property."""
        config = Config()
        backup = Backup(config=config)
        # Should not be in model fields
        assert "backup_id" not in backup.model_dump()
        # But should be accessible
        assert isinstance(backup.backup_id, str)
        assert len(backup.backup_id) == 15  # YYYYMMDD-HHMMSS

    def test_backup_default_timestamp(self):
        """Backup should default to current time."""
        before = datetime.now()
        backup = Backup(config=Config())
        after = datetime.now()
        assert before <= backup.timestamp <= after

    def test_backup_serialization(self):
        """Should serialize backup to dict."""
        config = Config(mcpServers={})
        timestamp = datetime(2024, 12, 2, 14, 30, 45)
        backup = Backup(config=config, timestamp=timestamp, metadata={"key": "value"})
        data = backup.model_dump(mode="json")
        assert "config" in data
        assert "timestamp" in data
        assert "metadata" in data
        assert data["metadata"] == {"key": "value"}

    def test_backup_deserialization(self):
        """Should deserialize backup from dict."""
        data = {
            "timestamp": "2024-12-02T14:30:45",
            "config": {"mcpServers": {}},
            "metadata": {"reason": "test"},
        }
        backup = Backup(**data)
        assert isinstance(backup.config, Config)
        assert backup.metadata == {"reason": "test"}


class TestModelIntegration:
    """Test models working together."""

    def test_full_config_roundtrip(self):
        """Should serialize and deserialize full config."""
        original = Config(
            mcpServers={
                "time": MCPServer(
                    type=MCPServerType.STDIO,
                    command="uvx",
                    args=["mcp-server-time"],
                    env={"TZ": "UTC"},
                ),
                "api": MCPServer(
                    type=MCPServerType.HTTP,
                    url="https://api.example.com/mcp",
                    headers={"Auth": "token"},
                ),
            }
        )

        # Serialize
        data = original.model_dump(mode="json")

        # Deserialize
        restored = Config(**data)

        # Verify
        assert len(restored.mcpServers) == 2
        assert restored.mcpServers["time"].command == "uvx"
        assert restored.mcpServers["api"].url == "https://api.example.com/mcp"

    def test_backup_with_full_config(self):
        """Should backup config with multiple servers."""
        config = Config(
            mcpServers={
                "server1": MCPServer(type=MCPServerType.STDIO, command="cmd1"),
                "server2": MCPServer(type=MCPServerType.STDIO, command="cmd2"),
            }
        )
        backup = Backup(config=config, metadata={"reason": "test"})

        assert len(backup.config.mcpServers) == 2
        assert "server1" in backup.config.mcpServers
        assert "server2" in backup.config.mcpServers

    def test_empty_to_full_config(self):
        """Should handle empty to full config transition."""
        config = Config()
        assert config.mcpServers == {}

        config.mcpServers["new"] = MCPServer(
            type=MCPServerType.STDIO, command="test"
        )
        assert len(config.mcpServers) == 1
        assert "new" in config.mcpServers


class TestModelEdgeCases:
    """Test edge cases and error handling."""

    def test_invalid_server_type(self):
        """Should reject invalid server type."""
        with pytest.raises(ValidationError):
            MCPServer(type="invalid", command="test")

    def test_server_with_both_command_and_url(self):
        """Should allow server with both command and url (even if unusual)."""
        # This is technically valid per the model, just unusual
        server = MCPServer(
            type=MCPServerType.STDIO, command="test", url="http://example.com"
        )
        assert server.command == "test"
        assert server.url == "http://example.com"

    def test_empty_args_and_env(self):
        """Should handle empty args and env."""
        server = MCPServer(type=MCPServerType.STDIO, command="test", args=[], env={})
        assert server.args == []
        assert server.env == {}

    def test_unicode_in_fields(self):
        """Should handle unicode characters."""
        server = MCPServer(
            type=MCPServerType.STDIO,
            command="test",
            env={"KEY": "값", "NAME": "テスト"},
        )
        assert server.env["KEY"] == "값"
        assert server.env["NAME"] == "テスト"

    def test_large_number_of_servers(self):
        """Should handle many servers."""
        servers = {
            f"server{i}": MCPServer(type=MCPServerType.STDIO, command=f"cmd{i}")
            for i in range(100)
        }
        config = Config(mcpServers=servers)
        assert len(config.mcpServers) == 100
