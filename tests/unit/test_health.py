"""Unit tests for health module."""

import subprocess
from unittest.mock import Mock, patch

from mcp_manager.health import HealthChecker, HealthStatus
from mcp_manager.models import MCPServer, MCPServerType


class TestHealthCheckerInit:
    """Test HealthChecker initialization."""

    def test_init(self):
        """Should initialize successfully."""
        checker = HealthChecker()
        assert checker is not None


class TestHealthCheckerCheckStdio:
    """Test HealthChecker.check_stdio_server method."""

    def test_check_stdio_command_not_found(self):
        """Should return UNHEALTHY if command not found."""
        checker = HealthChecker()
        server = MCPServer(
            type=MCPServerType.STDIO,
            command="nonexistent-command-xyz",
            args=["--version"],
            env={},
        )

        with patch("shutil.which", return_value=None):
            status = checker.check_stdio_server(server)

        assert status == HealthStatus.UNHEALTHY

    def test_check_stdio_command_exists(self):
        """Should return HEALTHY if command exists and runs."""
        checker = HealthChecker()
        server = MCPServer(
            type=MCPServerType.STDIO,
            command="python",
            args=["--version"],
            env={},
        )

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Python 3.10.0"

        with patch("shutil.which", return_value="/usr/bin/python"):
            with patch("subprocess.run", return_value=mock_result):
                status = checker.check_stdio_server(server)

        assert status == HealthStatus.HEALTHY

    def test_check_stdio_command_fails(self):
        """Should return UNHEALTHY if command fails."""
        checker = HealthChecker()
        server = MCPServer(
            type=MCPServerType.STDIO,
            command="python",
            args=["--nonexistent-flag"],
            env={},
        )

        with patch("shutil.which", return_value="/usr/bin/python"):
            with patch(
                "subprocess.run",
                side_effect=subprocess.TimeoutExpired("python", 5),
            ):
                status = checker.check_stdio_server(server)

        assert status == HealthStatus.UNHEALTHY

    def test_check_stdio_subprocess_error(self):
        """Should return UNHEALTHY on subprocess error."""
        checker = HealthChecker()
        server = MCPServer(
            type=MCPServerType.STDIO,
            command="python",
            args=["--version"],
            env={},
        )

        with patch("shutil.which", return_value="/usr/bin/python"):
            with patch(
                "subprocess.run",
                side_effect=subprocess.SubprocessError("Error"),
            ):
                status = checker.check_stdio_server(server)

        assert status == HealthStatus.UNHEALTHY


class TestHealthCheckerCheckHttp:
    """Test HealthChecker.check_http_server method."""

    def test_check_http_success(self):
        """Should return HEALTHY if HTTP request succeeds."""
        checker = HealthChecker()
        server = MCPServer(
            type=MCPServerType.HTTP,
            url="https://example.com/mcp",
            headers={"Authorization": "Bearer token"},
        )

        mock_response = Mock()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_response.status = 200

        with patch("urllib.request.urlopen", return_value=mock_response):
            status = checker.check_http_server(server)

        assert status == HealthStatus.HEALTHY

    def test_check_http_redirect(self):
        """Should return HEALTHY for 3xx redirects."""
        checker = HealthChecker()
        server = MCPServer(
            type=MCPServerType.HTTP,
            url="https://example.com/mcp",
            headers={},
        )

        mock_response = Mock()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_response.status = 301

        with patch("urllib.request.urlopen", return_value=mock_response):
            status = checker.check_http_server(server)

        assert status == HealthStatus.HEALTHY

    def test_check_http_not_found(self):
        """Should return UNHEALTHY for 404."""
        checker = HealthChecker()
        server = MCPServer(
            type=MCPServerType.HTTP,
            url="https://example.com/mcp",
            headers={},
        )

        from urllib.error import HTTPError

        with patch(
            "urllib.request.urlopen",
            side_effect=HTTPError("url", 404, "Not Found", {}, None),
        ):
            status = checker.check_http_server(server)

        assert status == HealthStatus.UNHEALTHY

    def test_check_http_network_error(self):
        """Should return UNHEALTHY on network error."""
        checker = HealthChecker()
        server = MCPServer(
            type=MCPServerType.HTTP,
            url="https://example.com/mcp",
            headers={},
        )

        from urllib.error import URLError

        with patch(
            "urllib.request.urlopen",
            side_effect=URLError("Connection failed"),
        ):
            status = checker.check_http_server(server)

        assert status == HealthStatus.UNHEALTHY

    def test_check_http_timeout(self):
        """Should return UNHEALTHY on timeout."""
        checker = HealthChecker()
        server = MCPServer(
            type=MCPServerType.HTTP,
            url="https://example.com/mcp",
            headers={},
        )

        import socket

        with patch(
            "urllib.request.urlopen",
            side_effect=socket.timeout("Timeout"),
        ):
            status = checker.check_http_server(server)

        assert status == HealthStatus.UNHEALTHY


class TestHealthCheckerCheck:
    """Test HealthChecker.check method."""

    def test_check_stdio_server(self):
        """Should dispatch to check_stdio_server."""
        checker = HealthChecker()
        server = MCPServer(
            type=MCPServerType.STDIO,
            command="python",
            args=["--version"],
            env={},
        )

        with patch.object(
            checker,
            "check_stdio_server",
            return_value=HealthStatus.HEALTHY,
        ) as mock_check:
            status = checker.check(server)

        mock_check.assert_called_once_with(server)
        assert status == HealthStatus.HEALTHY

    def test_check_http_server(self):
        """Should dispatch to check_http_server."""
        checker = HealthChecker()
        server = MCPServer(
            type=MCPServerType.HTTP,
            url="https://example.com/mcp",
            headers={},
        )

        with patch.object(
            checker,
            "check_http_server",
            return_value=HealthStatus.HEALTHY,
        ) as mock_check:
            status = checker.check(server)

        mock_check.assert_called_once_with(server)
        assert status == HealthStatus.HEALTHY

    def test_check_sse_server(self):
        """Should check SSE servers using HTTP check."""
        checker = HealthChecker()
        server = MCPServer(
            type=MCPServerType.SSE,
            url="https://example.com/mcp",
            headers={},
        )

        with patch.object(
            checker,
            "check_http_server",
            return_value=HealthStatus.HEALTHY,
        ) as mock_check:
            status = checker.check(server)

        mock_check.assert_called_once_with(server)
        assert status == HealthStatus.HEALTHY
