"""Configuration management for MCP servers."""

import json
from pathlib import Path
from typing import Optional

from pydantic import ValidationError as PydanticValidationError

from mcp_manager.constants import (
    DEFAULT_CONFIG_PATH,
    LOCAL_CONFIG_PATH,
    PROJECT_CONFIG_PATH,
)
from mcp_manager.exceptions import (
    ConfigCorruptedError,
    ConfigNotFoundError,
    ConfigPermissionError,
    ServerAlreadyExistsError,
)
from mcp_manager.file_handler import atomic_write
from mcp_manager.models import Config, MCPServer, MCPServerType, Scope


class ConfigManager:
    """Manage MCP server configuration files."""

    def __init__(self, config_path: Optional[Path] = None, scope: Scope = Scope.USER):
        """Initialize configuration manager.

        Args:
            config_path: Custom config path (overrides scope)
            scope: Configuration scope (user/project/local)
        """
        if config_path:
            self.config_path = config_path
        else:
            self.config_path = self._get_config_path(scope)

        self._config: Optional[Config] = None

    @staticmethod
    def _get_config_path(scope: Scope) -> Path:
        """Get config file path based on scope.

        Args:
            scope: Configuration scope

        Returns:
            Path to config file
        """
        if scope == Scope.USER:
            return DEFAULT_CONFIG_PATH
        elif scope == Scope.PROJECT:
            return PROJECT_CONFIG_PATH
        else:  # Scope.LOCAL
            return LOCAL_CONFIG_PATH

    def load(self) -> Config:
        """Load configuration from file.

        Returns:
            Loaded configuration

        Raises:
            ConfigNotFoundError: If config file not found
            ConfigPermissionError: If permission denied
            ConfigCorruptedError: If config is invalid
        """
        try:
            data = self.config_path.read_text(encoding="utf-8")
        except FileNotFoundError as e:
            raise ConfigNotFoundError(
                f"Configuration file not found: {self.config_path}",
                details={"path": str(self.config_path)},
            ) from e
        except PermissionError as e:
            raise ConfigPermissionError(
                f"Permission denied: cannot read {self.config_path}",
                details={"path": str(self.config_path), "operation": "read"},
            ) from e

        try:
            json_data = json.loads(data)
        except json.JSONDecodeError as e:
            raise ConfigCorruptedError(
                f"Invalid JSON in config file: {e}",
                details={"path": str(self.config_path), "error": str(e)},
            ) from e

        try:
            config = Config.model_validate(json_data)
            self._config = config
            return config
        except PydanticValidationError as e:
            raise ConfigCorruptedError(
                f"Configuration schema validation failed: {e}",
                details={"path": str(self.config_path), "error": str(e)},
            ) from e

    def save(self, config: Optional[Config] = None) -> None:
        """Save configuration to file.

        Args:
            config: Configuration to save (uses cached if None)

        Raises:
            ConfigPermissionError: If permission denied
        """
        if config is None:
            if self._config is None:
                raise ValueError("No config to save")
            config = self._config

        try:
            # Serialize to JSON
            json_str = json.dumps(config.model_dump(mode="json"), indent=2, ensure_ascii=False)

            # Write atomically
            atomic_write(self.config_path, json_str + "\n")

            # Update cache
            self._config = config

        except PermissionError as e:
            raise ConfigPermissionError(
                f"Permission denied: cannot write {self.config_path}",
                details={"path": str(self.config_path), "operation": "write"},
            ) from e

    def add_server(self, name: str, server: MCPServer) -> None:
        """Add a new server to configuration.

        Args:
            name: Server name
            server: Server configuration

        Raises:
            ServerAlreadyExistsError: If server already exists
        """
        config = self.load()

        if name in config.mcpServers:
            raise ServerAlreadyExistsError(
                f"Server '{name}' already exists",
                details={"name": name, "scope": "user"},
            )

        config.mcpServers[name] = server
        self.save(config)

    def remove_server(self, name: str) -> None:
        """Remove server from configuration.

        Args:
            name: Server name
        """
        config = self.load()

        if name in config.mcpServers:
            del config.mcpServers[name]
            self.save(config)

    def get_server(self, name: str) -> Optional[MCPServer]:
        """Get server by name.

        Args:
            name: Server name

        Returns:
            Server configuration or None if not found
        """
        config = self.load()
        return config.mcpServers.get(name)

    def list_servers(
        self,
        scope: Optional[Scope] = None,
        server_type: Optional[MCPServerType] = None,
    ) -> dict[str, MCPServer]:
        """List servers with optional filters.

        Args:
            scope: Filter by scope (not yet implemented)
            server_type: Filter by server type

        Returns:
            Dictionary of server name to server configuration
        """
        config = self.load()
        servers = config.mcpServers

        # Filter by type if specified
        if server_type:
            servers = {
                name: server for name, server in servers.items() if server.type == server_type
            }

        return servers
