"""Health check functionality for MCP servers."""

# TODO: Implement health checks

import shutil
import subprocess
from enum import Enum

from mcp_manager.constants import DEFAULT_HEALTH_TIMEOUT
from mcp_manager.models import MCPServer, MCPServerType


class HealthStatus(str, Enum):
    """Server health status."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthChecker:
    """Check MCP server health."""

    def __init__(self, timeout: int = DEFAULT_HEALTH_TIMEOUT):
        """Initialize health checker.

        Args:
            timeout: Timeout for health checks in seconds
        """
        self.timeout = timeout

    def check(self, server: MCPServer) -> HealthStatus:
        """Check server health.

        Args:
            server: Server to check

        Returns:
            Health status
        """
        if server.type == MCPServerType.STDIO:
            return self.check_stdio_server(server)
        elif server.type in (MCPServerType.HTTP, MCPServerType.SSE):
            return self.check_http_server(server)
        else:
            return HealthStatus.UNKNOWN

    def check_stdio_server(self, server: MCPServer) -> HealthStatus:
        """Check stdio server health.

        Args:
            server: Stdio server to check

        Returns:
            Health status
        """
        # Check if command exists
        if not server.command:
            return HealthStatus.UNHEALTHY

        if not shutil.which(server.command):
            return HealthStatus.UNHEALTHY

        # Try running with --version
        try:
            subprocess.run(
                [server.command, "--version"],
                timeout=self.timeout,
                capture_output=True,
                check=False,
            )
            return HealthStatus.HEALTHY
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            return HealthStatus.UNHEALTHY

    def check_http_server(self, server: MCPServer) -> HealthStatus:
        """Check HTTP/SSE server health.

        Args:
            server: HTTP/SSE server to check

        Returns:
            Health status
        """
        import urllib.request
        from urllib.error import HTTPError, URLError

        if not server.url:
            return HealthStatus.UNHEALTHY

        try:
            # Create request with headers if provided
            req = urllib.request.Request(server.url)
            if server.headers:
                for key, value in server.headers.items():
                    req.add_header(key, value)

            # Try to open URL with timeout
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                # Check if status code is success (2xx or 3xx)
                if 200 <= response.status < 400:
                    return HealthStatus.HEALTHY
                else:
                    return HealthStatus.UNHEALTHY

        except (HTTPError, URLError, TimeoutError, OSError):
            return HealthStatus.UNHEALTHY
