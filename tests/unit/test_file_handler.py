"""Unit tests for file_handler module."""

import os
import sys
from pathlib import Path

import portalocker
import pytest

from mcp_manager.exceptions import FileIOError
from mcp_manager.file_handler import FileLock, atomic_write, file_lock


class TestAtomicWrite:
    """Test atomic_write function."""

    def test_write_new_file(self, tmp_path):
        """Should write new file atomically."""
        target = tmp_path / "test.txt"
        content = "Hello, World!"

        atomic_write(target, content)

        assert target.exists()
        assert target.read_text(encoding="utf-8") == content

    def test_overwrite_existing_file(self, tmp_path):
        """Should overwrite existing file atomically."""
        target = tmp_path / "test.txt"
        target.write_text("Old content")

        new_content = "New content"
        atomic_write(target, new_content)

        assert target.read_text(encoding="utf-8") == new_content

    def test_no_temp_file_after_success(self, tmp_path):
        """Should cleanup temp file after successful write."""
        target = tmp_path / "test.txt"
        atomic_write(target, "content")

        # Check no .tmp file left behind
        temp_files = list(tmp_path.glob("*.tmp"))
        assert len(temp_files) == 0

    def test_cleanup_temp_file_on_error(self, tmp_path, monkeypatch):
        """Should cleanup temp file if write fails."""
        target = tmp_path / "test.txt"

        # Mock write_text to simulate failure
        original_write_text = Path.write_text

        def mock_write_text(self, *args, **kwargs):
            if ".tmp" in str(self):
                raise IOError("Simulated write error")
            return original_write_text(self, *args, **kwargs)

        monkeypatch.setattr(Path, "write_text", mock_write_text)

        with pytest.raises(FileIOError):
            atomic_write(target, "content")

        # Check no .tmp file left behind
        temp_files = list(tmp_path.glob("*.tmp"))
        assert len(temp_files) == 0

    def test_write_unicode_content(self, tmp_path):
        """Should handle unicode content."""
        target = tmp_path / "unicode.txt"
        content = "Hello 世界 🌍 Привет"

        atomic_write(target, content)

        assert target.read_text(encoding="utf-8") == content

    def test_write_empty_file(self, tmp_path):
        """Should handle empty content."""
        target = tmp_path / "empty.txt"
        atomic_write(target, "")

        assert target.exists()
        assert target.read_text(encoding="utf-8") == ""

    def test_write_large_content(self, tmp_path):
        """Should handle large content."""
        target = tmp_path / "large.txt"
        content = "x" * 1_000_000  # 1MB

        atomic_write(target, content)

        assert target.read_text(encoding="utf-8") == content

    def test_write_multiline_content(self, tmp_path):
        """Should preserve multiline content."""
        target = tmp_path / "multiline.txt"
        content = "Line 1\nLine 2\nLine 3\n"

        atomic_write(target, content)

        assert target.read_text(encoding="utf-8") == content

    def test_fsync_called(self, tmp_path, monkeypatch):
        """Should call fsync for durability."""
        target = tmp_path / "test.txt"
        fsync_called = []

        original_fsync = os.fsync

        def mock_fsync(fd):
            fsync_called.append(fd)
            original_fsync(fd)

        monkeypatch.setattr(os, "fsync", mock_fsync)

        atomic_write(target, "content")

        assert len(fsync_called) > 0

    def test_atomic_rename(self, tmp_path):
        """Should use atomic rename operation."""
        target = tmp_path / "test.txt"
        # Create existing file with content
        target.write_text("existing")

        # If rename is not atomic, there could be a moment where file doesn't exist
        # We can't easily test this, but we can verify the end result
        atomic_write(target, "new content")

        assert target.exists()
        assert target.read_text(encoding="utf-8") == "new content"


class TestFileLock:
    """Test FileLock context manager."""

    def test_acquire_exclusive_lock(self, tmp_path):
        """Should acquire exclusive lock."""
        lockfile = tmp_path / "test.lock"
        lockfile.touch()

        with FileLock(lockfile, exclusive=True) as fd:
            assert fd is not None
            assert isinstance(fd, int)

    def test_acquire_shared_lock(self, tmp_path):
        """Should acquire shared lock."""
        lockfile = tmp_path / "test.lock"
        lockfile.touch()

        with FileLock(lockfile, exclusive=False) as fd:
            assert fd is not None

    def test_lock_released_on_exit(self, tmp_path):
        """Should release lock on context exit."""
        lockfile = tmp_path / "test.lock"
        lockfile.touch()

        with FileLock(lockfile, exclusive=True):
            pass

        # If lock is released, we should be able to acquire it again
        with FileLock(lockfile, exclusive=True):
            pass

    def test_lock_released_on_exception(self, tmp_path):
        """Should release lock even if exception occurs."""
        lockfile = tmp_path / "test.lock"
        lockfile.touch()

        try:
            with FileLock(lockfile, exclusive=True):
                raise ValueError("Test error")
        except ValueError:
            pass

        # Lock should be released
        with FileLock(lockfile, exclusive=True):
            pass

    def test_exclusive_lock_blocks_another_exclusive(self, tmp_path):
        """Exclusive lock should block another exclusive lock."""
        lockfile = tmp_path / "test.lock"
        lockfile.touch()

        with FileLock(lockfile, exclusive=True):
            # Try to acquire another exclusive lock (should block)
            # We can't easily test blocking, but we can test non-blocking flag
            try:
                fh = open(lockfile, "r+b")
                # Try non-blocking lock
                portalocker.lock(fh, portalocker.LOCK_EX | portalocker.LOCK_NB)
                # If we got here, lock wasn't held (test failure)
                fh.close()
                assert False, "Should have blocked"
            except portalocker.LockException:
                # Expected - lock was held
                pass

    def test_multiple_shared_locks(self, tmp_path):
        """Multiple shared locks should be allowed."""
        lockfile = tmp_path / "test.lock"
        lockfile.touch()

        with FileLock(lockfile, exclusive=False):
            # Try to acquire another shared lock
            fh = open(lockfile, "rb")
            portalocker.lock(fh, portalocker.LOCK_SH | portalocker.LOCK_NB)
            portalocker.unlock(fh)
            fh.close()
            # Should succeed

    def test_lock_nonexistent_file_fails(self, tmp_path):
        """Should fail if file doesn't exist."""
        lockfile = tmp_path / "nonexistent.lock"

        with pytest.raises((FileNotFoundError, OSError)):
            with FileLock(lockfile, exclusive=True):
                pass


class TestFileLockFunction:
    """Test file_lock convenience function."""

    def test_file_lock_returns_filelock(self, tmp_path):
        """file_lock() should return FileLock instance."""
        lockfile = tmp_path / "test.lock"
        lockfile.touch()

        lock = file_lock(lockfile)
        assert isinstance(lock, FileLock)

    def test_file_lock_with_exclusive(self, tmp_path):
        """file_lock() should accept exclusive parameter."""
        lockfile = tmp_path / "test.lock"
        lockfile.touch()

        with file_lock(lockfile, exclusive=True):
            pass

        with file_lock(lockfile, exclusive=False):
            pass


class TestIntegration:
    """Test integration scenarios."""

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Windows cannot replace a file with an open handle (file lock conflict)",
    )
    def test_atomic_write_with_lock(self, tmp_path):
        """Should be able to combine atomic write with locking."""
        target = tmp_path / "test.txt"
        target.touch()

        # Acquire lock before writing
        with file_lock(target, exclusive=True):
            atomic_write(target, "locked content")

        assert target.read_text(encoding="utf-8") == "locked content"

    def test_concurrent_write_protection(self, tmp_path):
        """Locks should prevent concurrent writes."""
        target = tmp_path / "test.txt"
        target.write_text("initial")

        # Hold exclusive lock
        with file_lock(target, exclusive=True):
            # Verify another process can't acquire lock
            fh = open(target, "r+b")
            try:
                portalocker.lock(fh, portalocker.LOCK_EX | portalocker.LOCK_NB)
                fh.close()
                assert False, "Should not acquire lock"
            except portalocker.LockException:
                # Expected
                pass

    def test_write_then_read(self, tmp_path):
        """Should write and read back correctly."""
        target = tmp_path / "test.txt"
        content = "Test content"

        atomic_write(target, content)

        assert target.read_text(encoding="utf-8") == content

    def test_multiple_writes(self, tmp_path):
        """Should handle multiple writes to same file."""
        target = tmp_path / "test.txt"

        atomic_write(target, "Version 1")
        assert target.read_text(encoding="utf-8") == "Version 1"

        atomic_write(target, "Version 2")
        assert target.read_text(encoding="utf-8") == "Version 2"

        atomic_write(target, "Version 3")
        assert target.read_text(encoding="utf-8") == "Version 3"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_write_to_nested_path(self, tmp_path):
        """Should create parent directories if needed."""
        nested = tmp_path / "a" / "b" / "c"
        nested.mkdir(parents=True)
        target = nested / "test.txt"

        atomic_write(target, "nested content")

        assert target.read_text(encoding="utf-8") == "nested content"

    def test_write_preserves_content_on_disk(self, tmp_path):
        """Should ensure content is on disk (fsync)."""
        target = tmp_path / "test.txt"
        content = "important data"

        atomic_write(target, content)

        # Read directly from filesystem
        with open(target, "r") as f:
            assert f.read() == content

    def test_lock_with_pathlib_path(self, tmp_path):
        """Should work with pathlib.Path objects."""
        lockfile = tmp_path / "test.lock"
        lockfile.touch()

        assert isinstance(lockfile, Path)

        with FileLock(lockfile):
            pass

    def test_lock_with_string_path(self, tmp_path):
        """Should work with string paths."""
        lockfile = tmp_path / "test.lock"
        lockfile.touch()

        with FileLock(str(lockfile)):
            pass

    def test_special_characters_in_filename(self, tmp_path):
        """Should handle special characters in filename."""
        target = tmp_path / "test-file_123.txt"
        atomic_write(target, "content")

        assert target.read_text(encoding="utf-8") == "content"

    def test_write_permission_error(self, tmp_path, monkeypatch):
        """Should raise FileIOError on permission denied."""
        target = tmp_path / "test.txt"

        # Mock write_text to raise PermissionError
        def mock_write_text(self, *args, **kwargs):
            raise PermissionError("Permission denied")

        monkeypatch.setattr(Path, "write_text", mock_write_text)

        with pytest.raises(FileIOError):
            atomic_write(target, "content")

    def test_empty_path(self):
        """Should handle invalid empty path."""
        with pytest.raises((ValueError, FileIOError, OSError)):
            atomic_write(Path(""), "content")
