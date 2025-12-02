"""Utility functions for MCP Manager."""

import os
import re
import unicodedata
from pathlib import Path

from mcp_manager.constants import (
    DEFAULT_CONFIG_PATH,
    LOCAL_CONFIG_PATH,
    PROJECT_CONFIG_PATH,
)
from mcp_manager.models import MCPServer, Scope


def get_config_path(scope: Scope) -> Path:
    """Get configuration file path for scope.

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


def expand_env_vars(text: str) -> str:
    """Expand environment variables in text.

    Supports two formats:
    - ${VAR}: Expands to environment variable value
    - ${VAR:-default}: Uses default if variable not set

    Args:
        text: Text containing ${VAR} patterns

    Returns:
        Text with expanded variables
    """

    def replace(match):
        var_expr = match.group(1)

        # Check for default value syntax
        if ":-" in var_expr:
            var, default = var_expr.split(":-", 1)
            return os.getenv(var, default)
        else:
            value = os.getenv(var_expr)
            if value is None:
                # Keep original if not found
                return match.group(0)
            return value

    # Pattern: ${...}
    pattern = r"\$\{([^}]+)\}"
    result = re.sub(pattern, replace, text)

    # Normalize to NFC for consistent Unicode representation across platforms
    # (macOS uses NFD for environment variables, NFC is standard elsewhere)
    return unicodedata.normalize('NFC', result)


def format_server_info(server: MCPServer, verbose: bool = False) -> str:
    """Format server configuration for display.

    Args:
        server: Server to format
        verbose: Include all details

    Returns:
        Formatted server info
    """
    lines = []
    lines.append(f"Type: {server.type}")

    if server.type == "stdio":
        lines.append(f"Command: {server.command}")
        if server.args:
            lines.append(f"Arguments: {' '.join(server.args)}")
        if server.env and verbose:
            lines.append("Environment Variables:")
            for key, value in server.env.items():
                lines.append(f"  {key}={value}")
    else:  # http or sse
        lines.append(f"URL: {server.url}")
        if server.headers and verbose:
            lines.append("Headers:")
            for key, value in server.headers.items():
                # Mask sensitive headers
                if "auth" in key.lower() or "token" in key.lower():
                    value = "***"
                lines.append(f"  {key}: {value}")

    return "\n".join(lines)
