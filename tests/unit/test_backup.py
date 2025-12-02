"""Unit tests for backup module."""

import json

import pytest

from mcp_manager import backup as backup_module
from mcp_manager.backup import BackupManager
from mcp_manager.exceptions import (
    BackupCorruptedError,
    BackupNotFoundError,
)
from mcp_manager.models import Backup, Config, MCPServer, MCPServerType


class TestBackupManagerInit:
    """Test BackupManager initialization."""

    def test_init_with_default_dir(self, tmp_path, monkeypatch):
        """Should use default backup directory."""
        monkeypatch.setattr(backup_module, 'DEFAULT_BACKUP_DIR', tmp_path / ".mcp-manager" / "backups")
        manager = BackupManager()
        assert manager.backup_dir == tmp_path / ".mcp-manager" / "backups"

    def test_init_with_custom_dir(self, tmp_path):
        """Should use custom backup directory."""
        custom_dir = tmp_path / "custom"
        manager = BackupManager(backup_dir=custom_dir)
        assert manager.backup_dir == custom_dir

    def test_init_creates_directory(self, tmp_path):
        """Should create backup directory if not exists."""
        backup_dir = tmp_path / "backups"
        assert not backup_dir.exists()

        BackupManager(backup_dir=backup_dir)
        assert backup_dir.exists()


class TestBackupManagerCreate:
    """Test BackupManager.create method."""

    def test_create_simple_backup(self, tmp_path):
        """Should create backup of configuration."""
        manager = BackupManager(backup_dir=tmp_path)
        config = Config(mcpServers={})

        backup = manager.create(config)

        assert isinstance(backup, Backup)
        assert backup.config == config
        assert backup.timestamp is not None

    def test_create_backup_with_reason(self, tmp_path):
        """Should create backup with reason metadata."""
        manager = BackupManager(backup_dir=tmp_path)
        config = Config(mcpServers={})

        backup = manager.create(config, reason="Manual backup")

        assert backup.metadata["reason"] == "Manual backup"

    def test_create_backup_with_name(self, tmp_path):
        """Should create backup with custom name."""
        manager = BackupManager(backup_dir=tmp_path)
        config = Config(mcpServers={})

        backup = manager.create(config, name="pre-update")

        assert backup.metadata["name"] == "pre-update"

    def test_create_saves_to_file(self, tmp_path):
        """Should save backup to file."""
        manager = BackupManager(backup_dir=tmp_path)
        config = Config(mcpServers={})

        backup = manager.create(config)

        backup_file = tmp_path / f"{backup.backup_id}.json"
        assert backup_file.exists()

    def test_create_backup_with_servers(self, tmp_path):
        """Should backup configuration with servers."""
        manager = BackupManager(backup_dir=tmp_path)
        server = MCPServer(type=MCPServerType.STDIO, command="uvx")
        config = Config(mcpServers={"time": server})

        backup = manager.create(config)

        assert "time" in backup.config.mcpServers

    def test_backup_id_format(self, tmp_path):
        """Backup ID should be formatted timestamp with microseconds."""
        manager = BackupManager(backup_dir=tmp_path)
        config = Config(mcpServers={})

        backup = manager.create(config)

        # Should match YYYYMMDD-HHMMSS-mmmmmm format (22 characters)
        assert len(backup.backup_id) == 22
        assert backup.backup_id.count("-") == 2  # Two dashes


class TestBackupManagerList:
    """Test BackupManager.list method."""

    def test_list_empty_directory(self, tmp_path):
        """Should return empty list for no backups."""
        manager = BackupManager(backup_dir=tmp_path)
        backups = manager.list()
        assert backups == []

    def test_list_single_backup(self, tmp_path):
        """Should list single backup."""
        manager = BackupManager(backup_dir=tmp_path)
        config = Config(mcpServers={})
        manager.create(config)

        backups = manager.list()

        assert len(backups) == 1
        assert isinstance(backups[0], Backup)

    def test_list_multiple_backups(self, tmp_path):
        """Should list multiple backups."""
        manager = BackupManager(backup_dir=tmp_path)
        config = Config(mcpServers={})

        # Create 3 backups
        manager.create(config, name="backup1")
        manager.create(config, name="backup2")
        manager.create(config, name="backup3")

        backups = manager.list()

        assert len(backups) == 3

    def test_list_sorted_by_timestamp(self, tmp_path):
        """Should sort backups by timestamp (newest first)."""
        manager = BackupManager(backup_dir=tmp_path)
        config = Config(mcpServers={})

        _backup1 = manager.create(config, name="first")
        _backup2 = manager.create(config, name="second")
        _backup3 = manager.create(config, name="third")

        backups = manager.list()

        # Newest should be first
        assert backups[0].timestamp >= backups[1].timestamp >= backups[2].timestamp
        assert backups[0].metadata["name"] == "third"

    def test_list_with_limit(self, tmp_path):
        """Should respect limit parameter."""
        manager = BackupManager(backup_dir=tmp_path)
        config = Config(mcpServers={})

        # Create 10 backups
        for i in range(10):
            manager.create(config, name=f"backup{i}")

        backups = manager.list(limit=3)

        assert len(backups) == 3

    def test_list_skips_corrupted_backups(self, tmp_path):
        """Should skip corrupted backup files."""
        manager = BackupManager(backup_dir=tmp_path)
        config = Config(mcpServers={})

        # Create valid backup
        manager.create(config)

        # Create corrupted backup file
        corrupted = tmp_path / "corrupted.json"
        corrupted.write_text("{invalid json")

        backups = manager.list()

        # Should return only the valid backup
        assert len(backups) == 1


class TestBackupManagerRestore:
    """Test BackupManager.restore method."""

    def test_restore_existing_backup(self, tmp_path):
        """Should restore configuration from backup."""
        manager = BackupManager(backup_dir=tmp_path)
        original_config = Config(mcpServers={})
        backup = manager.create(original_config)

        restored_config = manager.restore(backup.backup_id)

        assert isinstance(restored_config, Config)
        assert restored_config.mcpServers == original_config.mcpServers

    def test_restore_backup_with_servers(self, tmp_path):
        """Should restore servers correctly."""
        manager = BackupManager(backup_dir=tmp_path)
        server = MCPServer(type=MCPServerType.STDIO, command="uvx")
        original_config = Config(mcpServers={"time": server})
        backup = manager.create(original_config)

        restored_config = manager.restore(backup.backup_id)

        assert "time" in restored_config.mcpServers
        assert restored_config.mcpServers["time"].command == "uvx"

    def test_restore_nonexistent_backup(self, tmp_path):
        """Should raise BackupNotFoundError for nonexistent backup."""
        manager = BackupManager(backup_dir=tmp_path)

        with pytest.raises(BackupNotFoundError) as exc_info:
            manager.restore("nonexistent-backup-id")

        assert "nonexistent-backup-id" in exc_info.value.details["backup_id"]

    def test_restore_corrupted_backup(self, tmp_path):
        """Should raise BackupCorruptedError for corrupted backup."""
        manager = BackupManager(backup_dir=tmp_path)

        # Create corrupted backup file
        backup_path = tmp_path / "20241202-120000.json"
        backup_path.write_text("{invalid json")

        with pytest.raises(BackupCorruptedError):
            manager.restore("20241202-120000")

    def test_restore_invalid_schema(self, tmp_path):
        """Should raise BackupCorruptedError for invalid schema."""
        manager = BackupManager(backup_dir=tmp_path)

        # Create backup with invalid schema
        backup_path = tmp_path / "20241202-120000.json"
        backup_path.write_text(json.dumps({"invalid": "schema"}))

        with pytest.raises(BackupCorruptedError):
            manager.restore("20241202-120000")


class TestBackupManagerCleanup:
    """Test BackupManager.cleanup method."""

    def test_cleanup_keeps_recent_backups(self, tmp_path):
        """Should keep specified number of recent backups."""
        manager = BackupManager(backup_dir=tmp_path)
        config = Config(mcpServers={})

        # Create 10 backups
        for i in range(10):
            manager.create(config, name=f"backup{i}")

        deleted = manager.cleanup(keep=5)

        assert deleted == 5
        remaining = manager.list(limit=100)
        assert len(remaining) == 5

    def test_cleanup_empty_directory(self, tmp_path):
        """Should handle empty directory."""
        manager = BackupManager(backup_dir=tmp_path)

        deleted = manager.cleanup(keep=5)

        assert deleted == 0

    def test_cleanup_fewer_than_keep(self, tmp_path):
        """Should not delete if fewer backups than keep."""
        manager = BackupManager(backup_dir=tmp_path)
        config = Config(mcpServers={})

        # Create 3 backups
        for i in range(3):
            manager.create(config)

        deleted = manager.cleanup(keep=5)

        assert deleted == 0
        backups = manager.list()
        assert len(backups) == 3

    def test_cleanup_keeps_newest(self, tmp_path):
        """Should keep newest backups."""
        manager = BackupManager(backup_dir=tmp_path)
        config = Config(mcpServers={})

        # Create backups with distinct names
        _oldest = manager.create(config, name="oldest")
        _middle = manager.create(config, name="middle")
        _newest = manager.create(config, name="newest")

        manager.cleanup(keep=2)

        backups = manager.list()
        names = [b.metadata.get("name") for b in backups]

        assert len(backups) == 2
        assert "newest" in names
        assert "middle" in names
        assert "oldest" not in names

    def test_cleanup_zero_keep(self, tmp_path):
        """Should delete all backups if keep=0."""
        manager = BackupManager(backup_dir=tmp_path)
        config = Config(mcpServers={})

        for i in range(5):
            manager.create(config)

        deleted = manager.cleanup(keep=0)

        assert deleted == 5
        backups = manager.list()
        assert len(backups) == 0


class TestBackupManagerIntegration:
    """Test BackupManager integration scenarios."""

    def test_full_lifecycle(self, tmp_path):
        """Should handle full backup lifecycle."""
        manager = BackupManager(backup_dir=tmp_path)
        server = MCPServer(type=MCPServerType.STDIO, command="uvx")
        config = Config(mcpServers={"time": server})

        # Create backup
        backup = manager.create(config, reason="Test backup")
        assert backup is not None

        # List backups
        backups = manager.list()
        assert len(backups) == 1

        # Restore backup
        restored = manager.restore(backup.backup_id)
        assert "time" in restored.mcpServers

        # Cleanup
        deleted = manager.cleanup(keep=0)
        assert deleted == 1

    def test_multiple_backups_same_config(self, tmp_path):
        """Should create multiple backups of same config."""
        manager = BackupManager(backup_dir=tmp_path)
        config = Config(mcpServers={})

        backup1 = manager.create(config, name="v1")
        backup2 = manager.create(config, name="v2")
        backup3 = manager.create(config, name="v3")

        assert backup1.backup_id != backup2.backup_id != backup3.backup_id

        backups = manager.list()
        assert len(backups) == 3

    def test_backup_preserves_metadata(self, tmp_path):
        """Should preserve metadata through save/load cycle."""
        manager = BackupManager(backup_dir=tmp_path)
        config = Config(mcpServers={})

        _backup = manager.create(
            config, name="important", reason="Before major update"
        )

        backups = manager.list()
        loaded = backups[0]

        assert loaded.metadata["name"] == "important"
        assert loaded.metadata["reason"] == "Before major update"

    def test_restore_different_configs(self, tmp_path):
        """Should restore correct configuration for each backup."""
        manager = BackupManager(backup_dir=tmp_path)

        config1 = Config(mcpServers={"time": MCPServer(type=MCPServerType.STDIO, command="uvx")})
        config2 = Config(mcpServers={"fetch": MCPServer(type=MCPServerType.STDIO, command="npx")})

        backup1 = manager.create(config1, name="time-only")
        backup2 = manager.create(config2, name="fetch-only")

        restored1 = manager.restore(backup1.backup_id)
        restored2 = manager.restore(backup2.backup_id)

        assert "time" in restored1.mcpServers
        assert "time" not in restored2.mcpServers
        assert "fetch" in restored2.mcpServers
        assert "fetch" not in restored1.mcpServers


class TestBackupManagerEdgeCases:
    """Test edge cases and error conditions."""

    def test_backup_empty_config(self, tmp_path):
        """Should backup empty configuration."""
        manager = BackupManager(backup_dir=tmp_path)
        config = Config(mcpServers={})

        backup = manager.create(config)

        assert backup.config.mcpServers == {}

    def test_backup_large_config(self, tmp_path):
        """Should backup large configuration."""
        manager = BackupManager(backup_dir=tmp_path)
        servers = {
            f"server{i}": MCPServer(type=MCPServerType.STDIO, command=f"cmd{i}")
            for i in range(100)
        }
        config = Config(mcpServers=servers)

        backup = manager.create(config)

        assert len(backup.config.mcpServers) == 100

    def test_backup_unicode_content(self, tmp_path):
        """Should handle unicode content."""
        manager = BackupManager(backup_dir=tmp_path)
        server = MCPServer(
            type=MCPServerType.STDIO,
            command="test",
            env={"NAME": "테스트", "VALUE": "値"},
        )
        config = Config(mcpServers={"test": server})

        backup = manager.create(config)
        restored = manager.restore(backup.backup_id)

        assert restored.mcpServers["test"].env["NAME"] == "테스트"
        assert restored.mcpServers["test"].env["VALUE"] == "値"

    def test_cleanup_with_invalid_backups(self, tmp_path):
        """Should handle cleanup with invalid backup files."""
        manager = BackupManager(backup_dir=tmp_path)
        config = Config(mcpServers={})

        # Create valid backups
        for i in range(5):
            manager.create(config)

        # Create invalid file
        (tmp_path / "invalid.json").write_text("not json")

        deleted = manager.cleanup(keep=2)

        # Should delete 3 valid backups (keep 2)
        assert deleted == 3
