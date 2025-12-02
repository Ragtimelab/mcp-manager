"""MCP Manager - CLI tool for managing Model Context Protocol servers."""

__version__ = "0.1.0"
__author__ = "Your Name"
__license__ = "MIT"

from mcp_manager.models import MCPServer, MCPServerType, Config, Scope

__all__ = [
    "__version__",
    "MCPServer",
    "MCPServerType",
    "Config",
    "Scope",
]
