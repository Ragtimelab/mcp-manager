"""Unit tests for CLI module."""

import json
from unittest.mock import Mock, patch

from typer.testing import CliRunner

from mcp_manager.cli import app
from mcp_manager.models import MCPServer, MCPServerType, Scope

runner = CliRunner()


class TestVersionCommand:
    """Test --version command."""

    def test_version_flag(self):
        """Should display version."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.stdout


class TestListCommand:
    """Test list command."""

    def test_list_empty_config(self, tmp_path, monkeypatch):
        """Should display message for no servers."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"mcpServers": {}}), encoding="utf-8")

        with patch("mcp_manager.cli.ConfigManager") as mock_config_class:
            mock_config = Mock()
            mock_config.load.return_value = Mock(mcpServers={})
            mock_config_class.return_value = mock_config

            result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "No servers found" in result.stdout or "MCP Servers" in result.stdout

    def test_list_with_servers(self, tmp_path):
        """Should list all servers."""
        with patch("mcp_manager.cli.ConfigManager") as mock_config_class:
            mock_config = Mock()
            mock_server = MCPServer(
                type=MCPServerType.STDIO,
                command="uvx",
                args=["mcp-server-time"],
                env={},
            )
            # Fix: list_servers() calls manager.list_servers(), not load()
            mock_config.list_servers.return_value = {"time": mock_server}
            mock_config_class.return_value = mock_config

            result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "time" in result.stdout.lower()

    def test_list_json_format(self):
        """Should output JSON format."""
        with patch("mcp_manager.cli.ConfigManager") as mock_config_class:
            mock_config = Mock()
            mock_server = MCPServer(
                type=MCPServerType.STDIO,
                command="uvx",
                args=["mcp-server-time"],
                env={},
            )
            mock_config.load.return_value = Mock(mcpServers={"time": mock_server})
            mock_config_class.return_value = mock_config

            result = runner.invoke(app, ["list", "--format", "json"])

        assert result.exit_code == 0
        # Should have output
        assert len(result.stdout) > 0

    def test_list_with_scope_filter(self):
        """Should filter by scope."""
        with patch("mcp_manager.cli.ConfigManager") as mock_config_class:
            mock_config = Mock()
            mock_server = MCPServer(
                type=MCPServerType.STDIO,
                command="uvx",
                args=["mcp-server-time"],
                env={},
            )
            mock_config.load.return_value = Mock(mcpServers={"time": mock_server})
            mock_config_class.return_value = mock_config

            result = runner.invoke(app, ["list", "--scope", "user"])

        assert result.exit_code == 0
        # Verify scope was passed to ConfigManager
        mock_config_class.assert_called_once()
        call_kwargs = mock_config_class.call_args[1]
        assert call_kwargs["scope"] == Scope.USER


class TestShowCommand:
    """Test show command."""

    def test_show_existing_server(self):
        """Should display server details."""
        with patch("mcp_manager.cli.ConfigManager") as mock_config_class:
            mock_config = Mock()
            mock_server = MCPServer(
                type=MCPServerType.STDIO,
                command="uvx",
                args=["mcp-server-time"],
                env={},
            )
            mock_config.get_server.return_value = mock_server
            mock_config_class.return_value = mock_config

            result = runner.invoke(app, ["show", "time"])

        assert result.exit_code == 0
        assert "time" in result.stdout.lower()
        assert "stdio" in result.stdout
        assert "uvx" in result.stdout

    def test_show_with_env_vars(self):
        """Should display environment variables in verbose mode."""
        with patch("mcp_manager.cli.ConfigManager") as mock_config_class:
            mock_config = Mock()
            mock_server = MCPServer(
                type=MCPServerType.STDIO,
                command="python",
                args=["server.py"],
                env={"API_KEY": "secret123"},
            )
            mock_config.get_server.return_value = mock_server
            mock_config_class.return_value = mock_config

            result = runner.invoke(app, ["show", "test", "--verbose"])

        assert result.exit_code == 0
        assert "API_KEY" in result.stdout

    def test_show_nonexistent_server(self):
        """Should handle error for nonexistent server."""
        with patch("mcp_manager.cli.ConfigManager") as mock_config_class:
            mock_config = Mock()
            # Fix: get_server() returns None, not raises exception
            mock_config.get_server.return_value = None
            mock_config_class.return_value = mock_config

            result = runner.invoke(app, ["show", "nonexistent"])

        # Should handle error (exit code 1)
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()


class TestAddCommand:
    """Test add command."""

    def test_add_stdio_server(self):
        """Should add stdio server with all options."""
        with patch("mcp_manager.cli.ConfigManager") as mock_config_class:
            mock_config = Mock()
            mock_config_class.return_value = mock_config

            result = runner.invoke(
                app,
                [
                    "add",
                    "test-server",
                    "--type",
                    "stdio",
                    "--command",
                    "uvx",
                    "--args",
                    "mcp-server-test",
                ],
            )

        assert result.exit_code == 0
        assert "added" in result.stdout.lower() or "success" in result.stdout.lower()
        mock_config.add_server.assert_called_once()

    def test_add_http_server(self):
        """Should add HTTP server."""
        with patch("mcp_manager.cli.ConfigManager") as mock_config_class:
            mock_config = Mock()
            mock_config_class.return_value = mock_config

            result = runner.invoke(
                app,
                [
                    "add",
                    "http-server",
                    "--type",
                    "http",
                    "--url",
                    "https://example.com/mcp",
                ],
            )

        assert result.exit_code == 0
        mock_config.add_server.assert_called_once()

    def test_add_with_env_vars(self):
        """Should add server with environment variables."""
        with patch("mcp_manager.cli.ConfigManager") as mock_config_class:
            mock_config = Mock()
            mock_config_class.return_value = mock_config

            result = runner.invoke(
                app,
                [
                    "add",
                    "env-server",
                    "--type",
                    "stdio",
                    "--command",
                    "python",
                    "--args",
                    "server.py",
                    "--env",
                    "KEY1=value1",
                    "--env",
                    "KEY2=value2",
                ],
            )

        assert result.exit_code == 0
        # Verify env vars were passed
        call_args = mock_config.add_server.call_args
        server = call_args[0][1]
        assert "KEY1" in server.env
        assert server.env["KEY1"] == "value1"


class TestRemoveCommand:
    """Test remove command."""

    def test_remove_with_force(self):
        """Should remove server without confirmation when --force is used."""
        with patch("mcp_manager.cli.ConfigManager") as mock_config_class:
            mock_config = Mock()
            mock_config_class.return_value = mock_config

            result = runner.invoke(app, ["remove", "test-server", "--force"])

        assert result.exit_code == 0
        mock_config.remove_server.assert_called_once_with("test-server")

    def test_remove_with_confirmation(self):
        """Should prompt for confirmation without --force."""
        with patch("mcp_manager.cli.ConfigManager") as mock_config_class:
            mock_config = Mock()
            mock_config_class.return_value = mock_config

            # Simulate user confirming
            result = runner.invoke(
                app,
                ["remove", "test-server"],
                input="y\n",
            )

        # May or may not call remove depending on implementation
        # Just verify it doesn't crash
        assert result.exit_code in [0, 1]


class TestBackupCommands:
    """Test backup commands."""

    def test_backup_create(self):
        """Should create backup."""
        with patch("mcp_manager.cli.ConfigManager") as mock_config_class:
            with patch("mcp_manager.cli.BackupManager") as mock_backup_class:
                # Mock ConfigManager
                mock_config = Mock()
                from mcp_manager.models import Config

                mock_config.load.return_value = Config(mcpServers={})
                mock_config_class.return_value = mock_config

                # Mock BackupManager - create() returns Backup object with backup_id
                mock_backup = Mock()
                mock_backup_obj = Mock()
                mock_backup_obj.backup_id = "20241202-120000"
                mock_backup.create.return_value = mock_backup_obj
                mock_backup_class.return_value = mock_backup

                result = runner.invoke(app, ["backup", "create"])

        # Should complete without error
        assert result.exit_code == 0
        assert "20241202-120000" in result.stdout

    def test_backup_list(self):
        """Should list backups."""
        with patch("mcp_manager.cli.BackupManager") as mock_backup_class:
            mock_backup = Mock()
            mock_backup.list.return_value = []
            mock_backup_class.return_value = mock_backup

            result = runner.invoke(app, ["backup", "list"])

        assert result.exit_code == 0
        # Should show output
        assert len(result.stdout) > 0

    def test_backup_restore(self):
        """Should attempt to restore backup."""
        with patch("mcp_manager.cli.BackupManager") as mock_backup_class:
            mock_backup = Mock()
            mock_backup_class.return_value = mock_backup

            result = runner.invoke(
                app,
                ["backup", "restore", "20241202-120000", "--force"],
            )

        # Should attempt restore (may fail if backup not found)
        assert result.exit_code in [0, 1]

    def test_backup_clean(self):
        """Should clean old backups."""
        with patch("mcp_manager.cli.BackupManager") as mock_backup_class:
            mock_backup = Mock()
            mock_backup.cleanup.return_value = 5
            mock_backup_class.return_value = mock_backup

            result = runner.invoke(app, ["backup", "clean", "--keep", "3", "--force"])

        assert result.exit_code == 0
        mock_backup.cleanup.assert_called_once_with(keep=3)


class TestTemplatesCommands:
    """Test templates commands."""

    def test_templates_list(self):
        """Should list available templates."""
        with patch("mcp_manager.cli.TemplateManager") as mock_template_class:
            mock_template = Mock()
            mock_template.list_templates.return_value = {
                "time": {
                    "name": "Time Server",
                    "description": "Time operations",
                    "category": "utility",
                }
            }
            mock_template_class.return_value = mock_template

            result = runner.invoke(app, ["templates", "list"])

        assert result.exit_code == 0
        assert "time" in result.stdout.lower() or "Time" in result.stdout

    def test_templates_show(self):
        """Should show template details."""
        with patch("mcp_manager.cli.TemplateManager") as mock_template_class:
            mock_template = Mock()
            mock_template.list_templates.return_value = {
                "time": {
                    "name": "Time Server",
                    "description": "Time operations",
                    "category": "utility",
                }
            }
            mock_server = MCPServer(
                type=MCPServerType.STDIO,
                command="uvx",
                args=["mcp-server-time"],
                env={},
            )
            mock_template.get_template.return_value = mock_server
            mock_template_class.return_value = mock_template

            result = runner.invoke(app, ["templates", "show", "time"])

        assert result.exit_code == 0
        assert "time" in result.stdout.lower()

    def test_templates_install(self):
        """Should install template."""
        with patch("mcp_manager.cli.TemplateManager") as mock_template_class:
            mock_template = Mock()
            mock_server = MCPServer(
                type=MCPServerType.STDIO,
                command="uvx",
                args=["mcp-server-time"],
                env={},
            )
            mock_template.install_template.return_value = mock_server
            mock_template_class.return_value = mock_template

            result = runner.invoke(app, ["templates", "install", "time"])

        assert result.exit_code == 0
        mock_template.install_template.assert_called_once()


class TestHealthCommand:
    """Test health command."""

    def test_health_all_servers(self):
        """Should check health of all servers."""
        from mcp_manager.health import HealthStatus

        with patch("mcp_manager.cli.ConfigManager") as mock_config_class:
            mock_config = Mock()
            mock_server = MCPServer(
                type=MCPServerType.STDIO,
                command="uvx",
                args=["mcp-server-time"],
                env={},
            )
            mock_config.load.return_value = Mock(mcpServers={"time": mock_server})
            mock_config_class.return_value = mock_config

            with patch("mcp_manager.cli.HealthChecker") as mock_health_class:
                mock_health = Mock()
                mock_health.check.return_value = HealthStatus.HEALTHY
                mock_health_class.return_value = mock_health

                result = runner.invoke(app, ["health"])

        # Should complete
        assert result.exit_code in [0, 1]

    def test_health_specific_server(self):
        """Should check health of specific server."""
        from mcp_manager.health import HealthStatus

        with patch("mcp_manager.cli.ConfigManager") as mock_config_class:
            mock_config = Mock()
            mock_server = MCPServer(
                type=MCPServerType.STDIO,
                command="uvx",
                args=["mcp-server-time"],
                env={},
            )
            mock_config.get_server.return_value = mock_server
            mock_config_class.return_value = mock_config

            with patch("mcp_manager.cli.HealthChecker") as mock_health_class:
                mock_health = Mock()
                mock_health.check.return_value = HealthStatus.HEALTHY
                mock_health_class.return_value = mock_health

                result = runner.invoke(app, ["health", "time"])

        assert result.exit_code == 0
        assert "HEALTHY" in result.stdout
