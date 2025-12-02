"""Input validation functions."""

import re
import shutil

from pydantic import HttpUrl
from pydantic import ValidationError as PydanticValidationError

from mcp_manager.constants import (
    ALLOWED_COMMANDS,
    DANGEROUS_ENV_VARS,
    RESERVED_NAMES,
    SERVER_NAME_PATTERN,
)
from mcp_manager.exceptions import (
    InvalidCommandError,
    InvalidServerNameError,
    InvalidURLError,
    SecurityError,
    ValidationError,
)
from mcp_manager.models import MCPServer, MCPServerType


def validate_server_name(name: str) -> bool:
    """Validate server name format.

    Args:
        name: Server name to validate

    Returns:
        True if valid

    Raises:
        InvalidServerNameError: If name is invalid
    """
    # Check pattern
    if not re.match(SERVER_NAME_PATTERN, name):
        raise InvalidServerNameError(
            f"Invalid server name: '{name}'",
            details={
                "name": name,
                "pattern": SERVER_NAME_PATTERN,
                "requirements": "lowercase alphanumeric, start with letter, 1-64 chars",
            },
        )

    # Check reserved names
    if name in RESERVED_NAMES:
        raise ValidationError(
            f"Server name '{name}' is reserved",
            details={"name": name, "reserved": list(RESERVED_NAMES)},
        )

    return True


def validate_command(command: str) -> bool:
    """Validate command exists and is allowed.

    Args:
        command: Command to validate

    Returns:
        True if valid

    Raises:
        InvalidCommandError: If command is not found or not allowed
    """
    # Check whitelist
    if command in ALLOWED_COMMANDS:
        return True

    # Check if exists on system
    if not shutil.which(command):
        raise InvalidCommandError(
            f"Command '{command}' not found",
            details={
                "command": command,
                "allowed": list(ALLOWED_COMMANDS),
                "hint": "Use one of the allowed commands or provide absolute path",
            },
        )

    # TODO: Log warning for non-whitelisted commands
    return True


def validate_url(url: str) -> bool:
    """Validate URL format.

    Args:
        url: URL to validate

    Returns:
        True if valid

    Raises:
        InvalidURLError: If URL is invalid
    """
    try:
        HttpUrl(url)
        return True
    except PydanticValidationError as e:
        raise InvalidURLError(f"Invalid URL: {url}", details={"url": url, "error": str(e)})


def validate_env_vars(env: dict[str, str]) -> bool:
    """Validate environment variables.

    Args:
        env: Environment variables to validate

    Returns:
        True if valid

    Raises:
        SecurityError: If dangerous variables are used
    """
    for key, value in env.items():
        # Check for dangerous environment variables
        if key in DANGEROUS_ENV_VARS:
            # TODO: Add interactive confirmation
            pass

        # Check for shell metacharacters in values
        dangerous_chars = [";", "&", "|", "`", "$", "(", ")"]
        if any(char in value for char in dangerous_chars):
            raise SecurityError(
                f"Shell metacharacter detected in env value: {key}={value}",
                details={"key": key, "value": value},
            )

    return True


def validate_server(server: MCPServer) -> bool:
    """Perform cross-field server validation.

    Args:
        server: Server to validate

    Returns:
        True if valid

    Raises:
        ValidationError: If server is invalid
    """
    # Validate stdio server
    if server.type == MCPServerType.STDIO:
        if not server.command:
            raise ValidationError("stdio servers require 'command' field")
        validate_command(server.command)

    # Validate http/sse server
    if server.type in (MCPServerType.HTTP, MCPServerType.SSE):
        if not server.url:
            raise ValidationError(f"{server.type} servers require 'url' field")
        validate_url(server.url)

    # Validate environment variables
    if server.env:
        validate_env_vars(server.env)

    return True
