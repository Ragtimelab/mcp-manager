"""Data models for MCP Manager."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MCPServerType(str, Enum):
    """MCP server transport types."""

    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"


class Scope(str, Enum):
    """Configuration scope levels."""

    USER = "user"
    PROJECT = "project"
    LOCAL = "local"


class MCPServer(BaseModel):
    """MCP server configuration."""

    type: MCPServerType
    """Server transport type (stdio, sse, http)"""

    # Stdio-specific fields
    command: Optional[str] = None
    """Executable command (required for stdio)"""

    args: list[str] = Field(default_factory=list)
    """Command-line arguments"""

    env: dict[str, str] = Field(default_factory=dict)
    """Environment variables"""

    # HTTP/SSE-specific fields
    url: Optional[str] = None
    """Server URL (required for http/sse)"""

    headers: dict[str, str] = Field(default_factory=dict)
    """HTTP headers"""

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
    )

    @field_validator("command")
    @classmethod
    def validate_stdio_command(cls, v: Optional[str], info) -> Optional[str]:
        """Validate that stdio servers have command."""
        if info.data.get("type") == MCPServerType.STDIO and not v:
            raise ValueError("stdio servers require 'command' field")
        return v

    @field_validator("url")
    @classmethod
    def validate_http_url(cls, v: Optional[str], info) -> Optional[str]:
        """Validate that http/sse servers have URL."""
        server_type = info.data.get("type")
        if server_type in (MCPServerType.HTTP, MCPServerType.SSE) and not v:
            raise ValueError(f"{server_type} servers require 'url' field")
        return v


class Config(BaseModel):
    """Claude Code configuration (~/.claude.json)."""

    mcpServers: dict[str, MCPServer] = Field(default_factory=dict)
    """MCP server configurations"""

    model_config = ConfigDict(
        # Allow unknown fields (preserve other Claude Code settings)
        extra="allow",
    )


class Backup(BaseModel):
    """Configuration backup."""

    timestamp: datetime = Field(default_factory=datetime.now)
    """Backup creation time"""

    config: Config
    """Backed up configuration"""

    metadata: dict[str, str] = Field(default_factory=dict)
    """Additional metadata (reason, user, etc.)"""

    @property
    def backup_id(self) -> str:
        """Unique backup identifier based on timestamp with microsecond precision."""
        return self.timestamp.strftime("%Y%m%d-%H%M%S-%f")
