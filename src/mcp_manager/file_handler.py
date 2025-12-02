"""Safe file I/O operations with atomic writes and locking."""

import fcntl
import os
from pathlib import Path
from typing import Optional

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

    Uses fcntl.flock for advisory file locking to prevent concurrent modifications.
    """

    def __init__(self, path: Path, exclusive: bool = True):
        """Initialize file lock.

        Args:
            path: Path to lock
            exclusive: If True, acquire exclusive lock (write). If False, shared lock (read).
        """
        self.path = path
        self.mode = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
        self.fd: Optional[int] = None

    def __enter__(self) -> int:
        """Acquire lock."""
        # Open file
        flags = os.O_RDWR if self.mode == fcntl.LOCK_EX else os.O_RDONLY
        self.fd = os.open(self.path, flags)

        # Acquire lock
        fcntl.flock(self.fd, self.mode)
        return self.fd

    def __exit__(self, *args: object) -> None:
        """Release lock."""
        if self.fd is not None:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            os.close(self.fd)


def file_lock(path: Path, exclusive: bool = True) -> FileLock:
    """Create file lock context manager.

    Args:
        path: Path to lock
        exclusive: If True, acquire exclusive lock

    Returns:
        FileLock context manager
    """
    return FileLock(path, exclusive)
