"""Unit tests for templates module."""

import json
from unittest.mock import Mock, patch

import pytest

from mcp_manager.exceptions import ServerAlreadyExistsError
from mcp_manager.models import MCPServer, MCPServerType, Scope
from mcp_manager.templates import (
    TemplateCorruptedError,
    TemplateManager,
    TemplateNotFoundError,
)


class TestTemplateManagerInit:
    """Test TemplateManager initialization."""

    def test_init_with_default_dir(self, tmp_path):
        """Should use default template directory."""
        manager = TemplateManager()
        # Default is src/mcp_manager/templates/
        assert manager.template_dir.name == "templates"

    def test_init_with_custom_dir(self, tmp_path):
        """Should use custom template directory."""
        custom_dir = tmp_path / "custom_templates"
        custom_dir.mkdir()
        manager = TemplateManager(template_dir=custom_dir)
        assert manager.template_dir == custom_dir


class TestTemplateManagerListTemplates:
    """Test TemplateManager.list_templates method."""

    def test_list_templates_empty_dir(self, tmp_path):
        """Should return empty dict for empty directory."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        manager = TemplateManager(template_dir=template_dir)

        templates = manager.list_templates()
        assert templates == {}

    def test_list_templates_nonexistent_dir(self, tmp_path):
        """Should return empty dict for nonexistent directory."""
        template_dir = tmp_path / "nonexistent"
        manager = TemplateManager(template_dir=template_dir)

        templates = manager.list_templates()
        assert templates == {}

    def test_list_templates_valid(self, tmp_path):
        """Should list valid templates."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        # Create valid template
        template_file = template_dir / "time.json"
        template_data = {
            "name": "Time Server",
            "description": "MCP server for time operations",
            "author": "Example",
            "category": "utility",
            "notes": "Some notes",
            "server": {
                "type": "stdio",
                "command": "uvx",
                "args": ["mcp-server-time"],
                "env": {},
            },
        }
        template_file.write_text(json.dumps(template_data), encoding="utf-8")

        manager = TemplateManager(template_dir=template_dir)
        templates = manager.list_templates()

        assert "time" in templates
        assert templates["time"]["name"] == "Time Server"
        assert templates["time"]["description"] == "MCP server for time operations"
        assert templates["time"]["author"] == "Example"
        assert templates["time"]["category"] == "utility"
        assert templates["time"]["notes"] == "Some notes"

    def test_list_templates_skip_corrupted(self, tmp_path):
        """Should skip corrupted templates."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        # Create valid template
        valid_file = template_dir / "valid.json"
        valid_file.write_text(
            json.dumps({"name": "Valid", "description": "Valid template"}),
            encoding="utf-8",
        )

        # Create corrupted template
        corrupted_file = template_dir / "corrupted.json"
        corrupted_file.write_text("invalid json{", encoding="utf-8")

        manager = TemplateManager(template_dir=template_dir)
        templates = manager.list_templates()

        assert "valid" in templates
        assert "corrupted" not in templates


class TestTemplateManagerGetTemplate:
    """Test TemplateManager.get_template method."""

    def test_get_template_not_found(self, tmp_path):
        """Should raise TemplateNotFoundError for nonexistent template."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        manager = TemplateManager(template_dir=template_dir)

        with pytest.raises(TemplateNotFoundError) as exc_info:
            manager.get_template("nonexistent")

        assert "nonexistent" in str(exc_info.value)

    def test_get_template_valid(self, tmp_path):
        """Should return MCPServer for valid template."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        template_file = template_dir / "time.json"
        template_data = {
            "name": "Time Server",
            "description": "Time operations",
            "server": {
                "type": "stdio",
                "command": "uvx",
                "args": ["mcp-server-time"],
                "env": {},
            },
        }
        template_file.write_text(json.dumps(template_data), encoding="utf-8")

        manager = TemplateManager(template_dir=template_dir)
        server = manager.get_template("time")

        assert isinstance(server, MCPServer)
        assert server.type == MCPServerType.STDIO
        assert server.command == "uvx"
        assert server.args == ["mcp-server-time"]

    def test_get_template_invalid_json(self, tmp_path):
        """Should raise TemplateCorruptedError for invalid JSON."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        template_file = template_dir / "corrupted.json"
        template_file.write_text("invalid json{", encoding="utf-8")

        manager = TemplateManager(template_dir=template_dir)

        with pytest.raises(TemplateCorruptedError) as exc_info:
            manager.get_template("corrupted")

        assert "invalid JSON" in str(exc_info.value)

    def test_get_template_missing_server_field(self, tmp_path):
        """Should raise TemplateCorruptedError if 'server' field missing."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        template_file = template_dir / "incomplete.json"
        template_data = {"name": "Incomplete", "description": "No server field"}
        template_file.write_text(json.dumps(template_data), encoding="utf-8")

        manager = TemplateManager(template_dir=template_dir)

        with pytest.raises(TemplateCorruptedError) as exc_info:
            manager.get_template("incomplete")

        assert "missing 'server' field" in str(exc_info.value)

    def test_get_template_invalid_schema(self, tmp_path):
        """Should raise TemplateCorruptedError for invalid server schema."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        template_file = template_dir / "invalid.json"
        template_data = {
            "server": {
                "type": "invalid_type",  # Invalid type
                "command": "test",
            }
        }
        template_file.write_text(json.dumps(template_data), encoding="utf-8")

        manager = TemplateManager(template_dir=template_dir)

        with pytest.raises(TemplateCorruptedError) as exc_info:
            manager.get_template("invalid")

        assert "invalid schema" in str(exc_info.value)


class TestTemplateManagerInstallTemplate:
    """Test TemplateManager.install_template method."""

    def test_install_template_success(self, tmp_path):
        """Should install template successfully."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        template_file = template_dir / "time.json"
        template_data = {
            "server": {
                "type": "stdio",
                "command": "uvx",
                "args": ["mcp-server-time"],
                "env": {},
            }
        }
        template_file.write_text(json.dumps(template_data), encoding="utf-8")

        manager = TemplateManager(template_dir=template_dir)

        # Mock ConfigManager
        with patch("mcp_manager.templates.ConfigManager") as mock_config_class:
            mock_config_instance = Mock()
            mock_config_class.return_value = mock_config_instance

            server = manager.install_template("time")

            # Verify ConfigManager was called correctly
            mock_config_class.assert_called_once_with(scope=Scope.USER)
            mock_config_instance.add_server.assert_called_once()

            # Verify returned server
            assert isinstance(server, MCPServer)
            assert server.command == "uvx"

    def test_install_template_with_custom_name(self, tmp_path):
        """Should install template with custom name."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        template_file = template_dir / "time.json"
        template_data = {
            "server": {
                "type": "stdio",
                "command": "uvx",
                "args": ["mcp-server-time"],
                "env": {},
            }
        }
        template_file.write_text(json.dumps(template_data), encoding="utf-8")

        manager = TemplateManager(template_dir=template_dir)

        with patch("mcp_manager.templates.ConfigManager") as mock_config_class:
            mock_config_instance = Mock()
            mock_config_class.return_value = mock_config_instance

            manager.install_template("time", server_name="my-time")

            # Verify custom name was used
            call_args = mock_config_instance.add_server.call_args
            assert call_args[0][0] == "my-time"

    def test_install_template_custom_scope(self, tmp_path):
        """Should install template to custom scope."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        template_file = template_dir / "time.json"
        template_data = {
            "server": {
                "type": "stdio",
                "command": "uvx",
                "args": ["mcp-server-time"],
                "env": {},
            }
        }
        template_file.write_text(json.dumps(template_data), encoding="utf-8")

        manager = TemplateManager(template_dir=template_dir)

        with patch("mcp_manager.templates.ConfigManager") as mock_config_class:
            mock_config_instance = Mock()
            mock_config_class.return_value = mock_config_instance

            manager.install_template("time", scope=Scope.PROJECT)

            # Verify scope was used
            mock_config_class.assert_called_once_with(scope=Scope.PROJECT)

    def test_install_template_not_found(self, tmp_path):
        """Should raise TemplateNotFoundError for nonexistent template."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        manager = TemplateManager(template_dir=template_dir)

        with pytest.raises(TemplateNotFoundError):
            manager.install_template("nonexistent")

    def test_install_template_already_exists(self, tmp_path):
        """Should raise ServerAlreadyExistsError if server exists."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        template_file = template_dir / "time.json"
        template_data = {
            "server": {
                "type": "stdio",
                "command": "uvx",
                "args": ["mcp-server-time"],
                "env": {},
            }
        }
        template_file.write_text(json.dumps(template_data), encoding="utf-8")

        manager = TemplateManager(template_dir=template_dir)

        with patch("mcp_manager.templates.ConfigManager") as mock_config_class:
            mock_config_instance = Mock()
            mock_config_instance.add_server.side_effect = ServerAlreadyExistsError(
                "Server already exists",
                details={"name": "time"},
            )
            mock_config_class.return_value = mock_config_instance

            with pytest.raises(ServerAlreadyExistsError):
                manager.install_template("time")
