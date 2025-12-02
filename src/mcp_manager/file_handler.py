"""Safe file I/O operations with atomic writes and locking."""

import os
from pathlib import Path
from typing import IO, Optional

import portalocker

from mcp_manager.exceptions import FileIOError


def atomic_write(path: Path, content: str) -> None:
    """Write file atomically to prevent corruption.

    Uses temp file and atomic rename to ensure either complete write or no change.

    Args:
        path: Target file path
        content: Content to write

    Raises:
        FileIOError: If write fails
    """
    temp_path = path.with_suffix(".tmp")

    try:
        # Write to temp file
        temp_path.write_text(content)

        # Ensure written to disk (durability)
        with open(temp_path, "r+") as f:
            os.fsync(f.fileno())

        # Atomic rename
        temp_path.rename(path)

    except Exception as e:
        # Cleanup temp file on error
        if temp_path.exists():
            temp_path.unlink()
        raise FileIOError(f"Failed to write {path}: {e}") from e


class FileLock:
    """Context manager for file locking.

    Uses portalocker for cross-platform advisory file locking to prevent concurrent
    modifications. Works on Unix/Linux/macOS (fcntl) and Windows (msvcrt).
    """

    def __init__(self, path: Path, exclusive: bool = True):
        """Initialize file lock.

        Args:
            path: Path to lock
            exclusive: If True, acquire exclusive lock (write). If False, shared lock (read).
        """
        self.path = path
        self.exclusive = exclusive
        self.file_handle: Optional[IO[bytes]] = None

    def __enter__(self) -> int:
        """Acquire lock."""
        # Open file for locking
        mode = "r+b" if self.exclusive else "rb"
        flags = portalocker.LOCK_EX if self.exclusive else portalocker.LOCK_SH

        # Open and lock in one step
        self.file_handle = open(self.path, mode)
        portalocker.lock(self.file_handle, flags)

        return self.file_handle.fileno()

    def __exit__(self, *args: object) -> None:
        """Release lock."""
        if self.file_handle is not None:
            portalocker.unlock(self.file_handle)
            self.file_handle.close()


def file_lock(path: Path, exclusive: bool = True) -> FileLock:
    """Create file lock context manager.

    Args:
        path: Path to lock
        exclusive: If True, acquire exclusive lock

    Returns:
        FileLock context manager
    """
    return FileLock(path, exclusive)
