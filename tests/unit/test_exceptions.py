"""Unit tests for exceptions module."""

import pytest

from mcp_manager.exceptions import (
    BackupCorruptedError,
    BackupError,
    BackupNotFoundError,
    BackupRestoreError,
    ConfigCorruptedError,
    ConfigError,
    ConfigNotFoundError,
    ConfigPermissionError,
    FileIOError,
    FileLockError,
    FileReadError,
    FileWriteError,
    HealthCheckError,
    InvalidCommandError,
    InvalidServerNameError,
    InvalidServerTypeError,
    InvalidURLError,
    MCPManagerError,
    SecurityError,
    ServerAlreadyExistsError,
    ServerTimeoutError,
    ServerUnreachableError,
    ValidationError,
)


class TestExceptionHierarchy:
    """Test exception class hierarchy."""

    def test_all_exceptions_inherit_from_base(self):
        """All custom exceptions should inherit from MCPManagerError."""
        exception_classes = [
            ConfigError,
            ConfigNotFoundError,
            ConfigCorruptedError,
            ConfigPermissionError,
            ValidationError,
            InvalidServerNameError,
            InvalidServerTypeError,
            InvalidCommandError,
            InvalidURLError,
            ServerAlreadyExistsError,
            BackupError,
            BackupNotFoundError,
            BackupCorruptedError,
            BackupRestoreError,
            FileIOError,
            FileReadError,
            FileWriteError,
            FileLockError,
            SecurityError,
            HealthCheckError,
            ServerUnreachableError,
            ServerTimeoutError,
        ]

        for exc_class in exception_classes:
            assert issubclass(exc_class, MCPManagerError)

    def test_mcpmanager_error_inherits_from_exception(self):
        """Base MCPManagerError should inherit from Exception."""
        assert issubclass(MCPManagerError, Exception)

    def test_config_errors_inherit_from_config_error(self):
        """Config-related errors should inherit from ConfigError."""
        assert issubclass(ConfigNotFoundError, ConfigError)
        assert issubclass(ConfigCorruptedError, ConfigError)
        assert issubclass(ConfigPermissionError, ConfigError)

    def test_validation_errors_inherit_from_validation_error(self):
        """Validation errors should inherit from ValidationError."""
        assert issubclass(InvalidServerNameError, ValidationError)
        assert issubclass(InvalidServerTypeError, ValidationError)
        assert issubclass(InvalidCommandError, ValidationError)
        assert issubclass(InvalidURLError, ValidationError)
        assert issubclass(ServerAlreadyExistsError, ValidationError)

    def test_backup_errors_inherit_from_backup_error(self):
        """Backup errors should inherit from BackupError."""
        assert issubclass(BackupNotFoundError, BackupError)
        assert issubclass(BackupCorruptedError, BackupError)
        assert issubclass(BackupRestoreError, BackupError)

    def test_file_io_errors_inherit_from_file_io_error(self):
        """File I/O errors should inherit from FileIOError."""
        assert issubclass(FileReadError, FileIOError)
        assert issubclass(FileWriteError, FileIOError)
        assert issubclass(FileLockError, FileIOError)

    def test_health_check_errors_inherit_from_health_check_error(self):
        """Health check errors should inherit from HealthCheckError."""
        assert issubclass(ServerUnreachableError, HealthCheckError)
        assert issubclass(ServerTimeoutError, HealthCheckError)


class TestExceptionInitialization:
    """Test exception initialization and attributes."""

    def test_base_exception_with_message_only(self):
        """Base exception should accept message only."""
        exc = MCPManagerError("Test error")
        assert exc.message == "Test error"
        assert exc.details == {}

    def test_base_exception_with_message_and_details(self):
        """Base exception should accept message and details."""
        details = {"file": "/path/to/file", "line": 42}
        exc = MCPManagerError("Test error", details=details)
        assert exc.message == "Test error"
        assert exc.details == details

    def test_config_not_found_error_initialization(self):
        """ConfigNotFoundError should initialize with path details."""
        exc = ConfigNotFoundError("Config not found", details={"path": "/test/path"})
        assert exc.message == "Config not found"
        assert exc.details["path"] == "/test/path"

    def test_invalid_server_name_error_initialization(self):
        """InvalidServerNameError should initialize with name details."""
        exc = InvalidServerNameError("Invalid name", details={"name": "InvalidName"})
        assert exc.message == "Invalid name"
        assert exc.details["name"] == "InvalidName"


class TestExceptionStringRepresentation:
    """Test exception string representation."""

    def test_exception_str_without_details(self):
        """Exception __str__ should show message when no details."""
        exc = MCPManagerError("Test error")
        assert "Test error" in str(exc)

    def test_exception_str_with_details(self):
        """Exception __str__ should include details."""
        details = {"file": "/path/to/file"}
        exc = MCPManagerError("Test error", details=details)
        result = str(exc)
        assert "Test error" in result
        assert "file" in result or "/path/to/file" in result

    def test_exception_repr(self):
        """Exception __repr__ should be informative."""
        exc = MCPManagerError("Test error", details={"key": "value"})
        result = repr(exc)
        assert "MCPManagerError" in result


class TestExceptionRaising:
    """Test exception raising and catching."""

    def test_raise_and_catch_base_exception(self):
        """Should be able to raise and catch base exception."""
        with pytest.raises(MCPManagerError) as exc_info:
            raise MCPManagerError("Test error")
        assert exc_info.value.message == "Test error"

    def test_catch_specific_exception_as_base(self):
        """Should be able to catch specific exception as base type."""
        with pytest.raises(MCPManagerError):
            raise ConfigNotFoundError("Config not found")

    def test_catch_config_error_hierarchy(self):
        """Should be able to catch ConfigNotFoundError as ConfigError."""
        with pytest.raises(ConfigError):
            raise ConfigNotFoundError("Config not found")

    def test_catch_validation_error_hierarchy(self):
        """Should be able to catch InvalidServerNameError as ValidationError."""
        with pytest.raises(ValidationError):
            raise InvalidServerNameError("Invalid name")

    def test_catch_backup_error_hierarchy(self):
        """Should be able to catch BackupNotFoundError as BackupError."""
        with pytest.raises(BackupError):
            raise BackupNotFoundError("Backup not found")


class TestExceptionDetails:
    """Test exception details field."""

    def test_details_default_to_empty_dict(self):
        """Exception details should default to empty dict."""
        exc = MCPManagerError("Test error")
        assert isinstance(exc.details, dict)
        assert len(exc.details) == 0

    def test_details_are_mutable(self):
        """Exception details should be mutable after creation."""
        exc = MCPManagerError("Test error")
        exc.details["key"] = "value"
        assert exc.details["key"] == "value"

    def test_details_accept_various_types(self):
        """Exception details should accept various value types."""
        details = {
            "string": "value",
            "int": 42,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
        }
        exc = MCPManagerError("Test error", details=details)
        assert exc.details == details


class TestSpecificExceptions:
    """Test specific exception types."""

    def test_config_not_found_error_is_distinct(self):
        """ConfigNotFoundError should be distinct from other config errors."""
        exc1 = ConfigNotFoundError("Not found")
        exc2 = ConfigCorruptedError("Corrupted")
        assert type(exc1) is not type(exc2)
        assert isinstance(exc1, ConfigError)
        assert isinstance(exc2, ConfigError)

    def test_validation_errors_are_distinct(self):
        """Different validation errors should be distinct types."""
        exc1 = InvalidServerNameError("Invalid name")
        exc2 = InvalidCommandError("Invalid command")
        exc3 = InvalidURLError("Invalid URL")
        assert type(exc1) is not type(exc2)
        assert type(exc2) is not type(exc3)
        assert type(exc1) is not type(exc3)

    def test_backup_errors_are_distinct(self):
        """Different backup errors should be distinct types."""
        exc1 = BackupNotFoundError("Not found")
        exc2 = BackupCorruptedError("Corrupted")
        assert type(exc1) is not type(exc2)
        assert isinstance(exc1, BackupError)
        assert isinstance(exc2, BackupError)


class TestExceptionUseCases:
    """Test real-world exception use cases."""

    def test_config_not_found_with_path(self):
        """ConfigNotFoundError should work with file path."""
        path = "/home/user/.claude.json"
        exc = ConfigNotFoundError(f"Configuration file not found: {path}", details={"path": path})
        assert path in exc.message
        assert exc.details["path"] == path

    def test_invalid_server_name_with_reason(self):
        """InvalidServerNameError should include validation reason."""
        name = "Invalid-Name-123"
        reason = "Must start with lowercase letter"
        exc = InvalidServerNameError(
            f"Invalid server name: {name}", details={"name": name, "reason": reason}
        )
        assert exc.details["name"] == name
        assert exc.details["reason"] == reason

    def test_server_already_exists_with_name(self):
        """ServerAlreadyExistsError should include server name."""
        name = "existing-server"
        exc = ServerAlreadyExistsError(f"Server '{name}' already exists", details={"name": name})
        assert name in exc.message
        assert exc.details["name"] == name

    def test_file_io_error_with_operation(self):
        """FileIOError should include operation details."""
        exc = FileIOError(
            "Failed to write file",
            details={"operation": "write", "path": "/tmp/test", "error": "EACCES"},
        )
        assert exc.details["operation"] == "write"
        assert exc.details["error"] == "EACCES"
