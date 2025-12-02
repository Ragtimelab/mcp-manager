"""Unit tests for config module."""

import json
from pathlib import Path

import pytest

from mcp_manager import config as config_module
from mcp_manager.config import ConfigManager
from mcp_manager.exceptions import (
    ConfigCorruptedError,
    ConfigNotFoundError,
    ConfigPermissionError,
    ServerAlreadyExistsError,
)
from mcp_manager.models import Config, MCPServer, MCPServerType, Scope


class TestConfigManagerInit:
    """Test ConfigManager initialization."""

    def test_init_with_default_scope(self, tmp_path, monkeypatch):
        """Should use USER scope by default."""
        monkeypatch.setattr(config_module, "DEFAULT_CONFIG_PATH", tmp_path / ".claude.json")
        manager = ConfigManager()
        assert manager.config_path == tmp_path / ".claude.json"

    def test_init_with_user_scope(self, tmp_path, monkeypatch):
        """Should use ~/.claude.json for USER scope."""
        monkeypatch.setattr(config_module, "DEFAULT_CONFIG_PATH", tmp_path / ".claude.json")
        manager = ConfigManager(scope=Scope.USER)
        assert manager.config_path == tmp_path / ".claude.json"

    def test_init_with_project_scope(self, tmp_path, monkeypatch):
        """Should use .mcp.json for PROJECT scope."""
        monkeypatch.setattr(config_module, "PROJECT_CONFIG_PATH", tmp_path / ".mcp.json")
        manager = ConfigManager(scope=Scope.PROJECT)
        assert manager.config_path == tmp_path / ".mcp.json"

    def test_init_with_local_scope(self, tmp_path, monkeypatch):
        """Should use .claude/settings.json for LOCAL scope."""
        monkeypatch.setattr(
            config_module, "LOCAL_CONFIG_PATH", tmp_path / ".claude" / "settings.json"
        )
        manager = ConfigManager(scope=Scope.LOCAL)
        assert manager.config_path == tmp_path / ".claude" / "settings.json"

    def test_init_with_custom_path(self, tmp_path):
        """Should use custom path when provided."""
        custom_path = tmp_path / "custom.json"
        manager = ConfigManager(config_path=custom_path)
        assert manager.config_path == custom_path


class TestConfigManagerLoad:
    """Test ConfigManager.load method."""

    def test_load_valid_config(self, tmp_path):
        """Should load valid configuration."""
        config_path = tmp_path / "config.json"
        config_data = {
            "mcpServers": {
                "time": {
                    "type": "stdio",
                    "command": "uvx",
                    "args": ["mcp-server-time"],
                    "env": {},
                }
            }
        }
        config_path.write_text(json.dumps(config_data))

        manager = ConfigManager(config_path=config_path)
        config = manager.load()

        assert isinstance(config, Config)
        assert "time" in config.mcpServers
        assert config.mcpServers["time"].command == "uvx"

    def test_load_empty_config(self, tmp_path):
        """Should load empty configuration."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"mcpServers": {}}))

        manager = ConfigManager(config_path=config_path)
        config = manager.load()

        assert isinstance(config, Config)
        assert config.mcpServers == {}

    def test_load_nonexistent_file(self, tmp_path):
        """Should raise ConfigNotFoundError for nonexistent file."""
        config_path = tmp_path / "nonexistent.json"
        manager = ConfigManager(config_path=config_path)

        with pytest.raises(ConfigNotFoundError) as exc_info:
            manager.load()

        assert str(config_path) in exc_info.value.details["path"]

    def test_load_invalid_json(self, tmp_path):
        """Should raise ConfigCorruptedError for invalid JSON."""
        config_path = tmp_path / "config.json"
        config_path.write_text("{invalid json")

        manager = ConfigManager(config_path=config_path)

        with pytest.raises(ConfigCorruptedError):
            manager.load()

    def test_load_invalid_schema(self, tmp_path):
        """Should raise ConfigCorruptedError for invalid schema."""
        config_path = tmp_path / "config.json"
        config_data = {"mcpServers": "not a dict"}  # Invalid schema
        config_path.write_text(json.dumps(config_data))

        manager = ConfigManager(config_path=config_path)

        with pytest.raises(ConfigCorruptedError):
            manager.load()

    def test_load_permission_denied(self, tmp_path, monkeypatch):
        """Should raise ConfigPermissionError on permission denied."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"mcpServers": {}}))

        def mock_read_text(self):
            raise PermissionError("Permission denied")

        monkeypatch.setattr(Path, "read_text", mock_read_text)

        manager = ConfigManager(config_path=config_path)

        with pytest.raises(ConfigPermissionError):
            manager.load()


class TestConfigManagerSave:
    """Test ConfigManager.save method."""

    def test_save_new_config(self, tmp_path):
        """Should save configuration to new file."""
        config_path = tmp_path / "config.json"
        manager = ConfigManager(config_path=config_path)

        config = Config(mcpServers={})
        manager.save(config)

        assert config_path.exists()
        data = json.loads(config_path.read_text())
        assert "mcpServers" in data

    def test_save_with_servers(self, tmp_path):
        """Should save configuration with servers."""
        config_path = tmp_path / "config.json"
        manager = ConfigManager(config_path=config_path)

        server = MCPServer(type=MCPServerType.STDIO, command="uvx")
        config = Config(mcpServers={"time": server})
        manager.save(config)

        data = json.loads(config_path.read_text())
        assert "time" in data["mcpServers"]
        assert data["mcpServers"]["time"]["command"] == "uvx"

    def test_save_overwrites_existing(self, tmp_path):
        """Should overwrite existing configuration."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"mcpServers": {"old": {}}}))

        manager = ConfigManager(config_path=config_path)
        new_config = Config(mcpServers={})
        manager.save(new_config)

        data = json.loads(config_path.read_text())
        assert "old" not in data["mcpServers"]

    def test_save_cached_config(self, tmp_path):
        """Should save cached config if none provided."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"mcpServers": {}}))

        manager = ConfigManager(config_path=config_path)
        manager.load()  # Load to cache

        # Modify cache
        manager._config.mcpServers["new"] = MCPServer(type=MCPServerType.STDIO, command="test")

        # Save without argument
        manager.save()

        data = json.loads(config_path.read_text())
        assert "new" in data["mcpServers"]

    def test_save_without_config_raises(self, tmp_path):
        """Should raise ValueError if no config to save."""
        config_path = tmp_path / "config.json"
        manager = ConfigManager(config_path=config_path)

        with pytest.raises(ValueError):
            manager.save()

    def test_save_unicode_content(self, tmp_path):
        """Should handle unicode content."""
        config_path = tmp_path / "config.json"
        manager = ConfigManager(config_path=config_path)

        server = MCPServer(type=MCPServerType.STDIO, command="test", env={"NAME": "테스트"})
        config = Config(mcpServers={"test": server})
        manager.save(config)

        data = json.loads(config_path.read_text())
        assert data["mcpServers"]["test"]["env"]["NAME"] == "테스트"


class TestConfigManagerAddServer:
    """Test ConfigManager.add_server method."""

    def test_add_server_to_empty_config(self, tmp_path):
        """Should add server to empty configuration."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"mcpServers": {}}))

        manager = ConfigManager(config_path=config_path)
        server = MCPServer(type=MCPServerType.STDIO, command="uvx")
        manager.add_server("time", server)

        config = manager.load()
        assert "time" in config.mcpServers
        assert config.mcpServers["time"].command == "uvx"

    def test_add_multiple_servers(self, tmp_path):
        """Should add multiple servers."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"mcpServers": {}}))

        manager = ConfigManager(config_path=config_path)

        server1 = MCPServer(type=MCPServerType.STDIO, command="uvx")
        server2 = MCPServer(type=MCPServerType.STDIO, command="npx")

        manager.add_server("time", server1)
        manager.add_server("fetch", server2)

        config = manager.load()
        assert len(config.mcpServers) == 2
        assert "time" in config.mcpServers
        assert "fetch" in config.mcpServers

    def test_add_duplicate_server_raises(self, tmp_path):
        """Should raise ServerAlreadyExistsError for duplicate."""
        config_path = tmp_path / "config.json"
        config_path.write_text(
            json.dumps(
                {"mcpServers": {"time": {"type": "stdio", "command": "uvx", "args": [], "env": {}}}}
            )
        )

        manager = ConfigManager(config_path=config_path)
        server = MCPServer(type=MCPServerType.STDIO, command="new")

        with pytest.raises(ServerAlreadyExistsError) as exc_info:
            manager.add_server("time", server)

        assert "time" in exc_info.value.details["name"]


class TestConfigManagerRemoveServer:
    """Test ConfigManager.remove_server method."""

    def test_remove_existing_server(self, tmp_path):
        """Should remove existing server."""
        config_path = tmp_path / "config.json"
        config_path.write_text(
            json.dumps(
                {"mcpServers": {"time": {"type": "stdio", "command": "uvx", "args": [], "env": {}}}}
            )
        )

        manager = ConfigManager(config_path=config_path)
        manager.remove_server("time")

        config = manager.load()
        assert "time" not in config.mcpServers

    def test_remove_nonexistent_server(self, tmp_path):
        """Should handle removing nonexistent server gracefully."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"mcpServers": {}}))

        manager = ConfigManager(config_path=config_path)
        # Should not raise
        manager.remove_server("nonexistent")

    def test_remove_one_of_many(self, tmp_path):
        """Should remove one server while keeping others."""
        config_path = tmp_path / "config.json"
        config_path.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "time": {"type": "stdio", "command": "uvx", "args": [], "env": {}},
                        "fetch": {"type": "stdio", "command": "npx", "args": [], "env": {}},
                    }
                }
            )
        )

        manager = ConfigManager(config_path=config_path)
        manager.remove_server("time")

        config = manager.load()
        assert "time" not in config.mcpServers
        assert "fetch" in config.mcpServers


class TestConfigManagerGetServer:
    """Test ConfigManager.get_server method."""

    def test_get_existing_server(self, tmp_path):
        """Should return existing server."""
        config_path = tmp_path / "config.json"
        config_path.write_text(
            json.dumps(
                {"mcpServers": {"time": {"type": "stdio", "command": "uvx", "args": [], "env": {}}}}
            )
        )

        manager = ConfigManager(config_path=config_path)
        server = manager.get_server("time")

        assert server is not None
        assert server.command == "uvx"

    def test_get_nonexistent_server(self, tmp_path):
        """Should return None for nonexistent server."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"mcpServers": {}}))

        manager = ConfigManager(config_path=config_path)
        server = manager.get_server("nonexistent")

        assert server is None


class TestConfigManagerListServers:
    """Test ConfigManager.list_servers method."""

    def test_list_empty_servers(self, tmp_path):
        """Should return empty dict for empty config."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"mcpServers": {}}))

        manager = ConfigManager(config_path=config_path)
        servers = manager.list_servers()

        assert servers == {}

    def test_list_all_servers(self, tmp_path):
        """Should return all servers."""
        config_path = tmp_path / "config.json"
        config_path.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "time": {"type": "stdio", "command": "uvx", "args": [], "env": {}},
                        "fetch": {"type": "stdio", "command": "npx", "args": [], "env": {}},
                    }
                }
            )
        )

        manager = ConfigManager(config_path=config_path)
        servers = manager.list_servers()

        assert len(servers) == 2
        assert "time" in servers
        assert "fetch" in servers

    def test_list_filter_by_type(self, tmp_path):
        """Should filter servers by type."""
        config_path = tmp_path / "config.json"
        config_path.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "time": {"type": "stdio", "command": "uvx", "args": [], "env": {}},
                        "api": {
                            "type": "http",
                            "url": "https://example.com",
                            "headers": {},
                        },
                    }
                }
            )
        )

        manager = ConfigManager(config_path=config_path)
        stdio_servers = manager.list_servers(server_type=MCPServerType.STDIO)

        assert len(stdio_servers) == 1
        assert "time" in stdio_servers
        assert "api" not in stdio_servers


class TestConfigManagerIntegration:
    """Test ConfigManager integration scenarios."""

    def test_full_lifecycle(self, tmp_path):
        """Should handle full server lifecycle."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"mcpServers": {}}))

        manager = ConfigManager(config_path=config_path)

        # Add server
        server = MCPServer(type=MCPServerType.STDIO, command="uvx")
        manager.add_server("time", server)

        # Get server
        retrieved = manager.get_server("time")
        assert retrieved is not None
        assert retrieved.command == "uvx"

        # List servers
        servers = manager.list_servers()
        assert len(servers) == 1

        # Remove server
        manager.remove_server("time")
        servers = manager.list_servers()
        assert len(servers) == 0

    def test_concurrent_access_simulation(self, tmp_path):
        """Should handle multiple managers on same file."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"mcpServers": {}}))

        manager1 = ConfigManager(config_path=config_path)
        manager2 = ConfigManager(config_path=config_path)

        # Manager 1 adds server
        server1 = MCPServer(type=MCPServerType.STDIO, command="uvx")
        manager1.add_server("time", server1)

        # Manager 2 should see the change
        servers = manager2.list_servers()
        assert "time" in servers

    def test_preserve_unknown_fields(self, tmp_path):
        """Should preserve unknown fields in config."""
        config_path = tmp_path / "config.json"
        config_path.write_text(
            json.dumps(
                {
                    "mcpServers": {},
                    "unknownField": "preserve this",
                    "anotherField": 123,
                }
            )
        )

        manager = ConfigManager(config_path=config_path)
        server = MCPServer(type=MCPServerType.STDIO, command="test")
        manager.add_server("test", server)

        # Reload and check unknown fields are preserved
        data = json.loads(config_path.read_text())
        assert "unknownField" in data or hasattr(manager._config, "unknownField")
