"""Custom exceptions for MCP Manager."""

from typing import Optional


class MCPManagerError(Exception):
    """Base exception for all MCP Manager errors."""

    def __init__(self, message: str, details: Optional[dict] = None):
        """Initialize exception.

        Args:
            message: Error message
            details: Additional details about the error
        """
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def __str__(self) -> str:
        """String representation with details."""
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


# Configuration errors
class ConfigError(MCPManagerError):
    """Configuration-related errors."""


class ConfigNotFoundError(ConfigError):
    """Configuration file not found."""


class ConfigCorruptedError(ConfigError):
    """Configuration file is corrupted or invalid."""


class ConfigPermissionError(ConfigError):
    """Permission denied for configuration file."""


# Validation errors
class ValidationError(MCPManagerError):
    """Input validation errors."""


class InvalidServerNameError(ValidationError):
    """Server name doesn't match required pattern."""


class InvalidServerTypeError(ValidationError):
    """Invalid server type."""


class InvalidCommandError(ValidationError):
    """Command not found or not allowed."""


class InvalidURLError(ValidationError):
    """Invalid URL format."""


class ServerAlreadyExistsError(ValidationError):
    """Server with this name already exists."""


# Backup errors
class BackupError(MCPManagerError):
    """Backup operation errors."""


class BackupNotFoundError(BackupError):
    """Backup not found."""


class BackupCorruptedError(BackupError):
    """Backup file is corrupted."""


class BackupRestoreError(BackupError):
    """Failed to restore from backup."""


# File I/O errors
class FileIOError(MCPManagerError):
    """File I/O operation errors."""


class FileReadError(FileIOError):
    """Failed to read file."""


class FileWriteError(FileIOError):
    """Failed to write file."""


class FileLockError(FileIOError):
    """Failed to acquire file lock."""


# Security errors
class SecurityError(MCPManagerError):
    """Security-related errors."""


# Health check errors
class HealthCheckError(MCPManagerError):
    """Health check errors."""


class ServerUnreachableError(HealthCheckError):
    """Server is unreachable."""


class ServerTimeoutError(HealthCheckError):
    """Server health check timed out."""
