"""Backup and restore functionality for MCP configurations."""

import json
from pathlib import Path
from typing import Optional

from pydantic import ValidationError as PydanticValidationError

from mcp_manager.constants import DEFAULT_BACKUP_DIR
from mcp_manager.exceptions import (
    BackupCorruptedError,
    BackupNotFoundError,
    BackupRestoreError,
)
from mcp_manager.file_handler import atomic_write
from mcp_manager.models import Backup, Config


class BackupManager:
    """Manage configuration backups."""

    def __init__(self, backup_dir: Optional[Path] = None):
        """Initialize backup manager.

        Args:
            backup_dir: Custom backup directory (uses default if None)
        """
        self.backup_dir = backup_dir or DEFAULT_BACKUP_DIR
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        config: Config,
        name: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Backup:
        """Create a new backup.

        Args:
            config: Configuration to backup
            name: Optional backup name (uses timestamp if None)
            reason: Optional reason for backup

        Returns:
            Created backup object
        """
        # Create backup object
        metadata = {}
        if reason:
            metadata["reason"] = reason
        if name:
            metadata["name"] = name

        backup = Backup(config=config, metadata=metadata)

        # Save to file
        backup_path = self._get_backup_path(backup.backup_id)
        json_str = json.dumps(backup.model_dump(mode="json"), indent=2, ensure_ascii=False)
        atomic_write(backup_path, json_str + "\n")

        return backup

    def list(self, limit: int = 10) -> list[Backup]:
        """List available backups.

        Args:
            limit: Maximum number of backups to return

        Returns:
            List of backup objects, sorted by timestamp (newest first)
        """
        backups = []

        for backup_file in self.backup_dir.glob("*.json"):
            try:
                data = json.loads(backup_file.read_text(encoding="utf-8"))
                backup = Backup.model_validate(data)
                backups.append(backup)
            except (json.JSONDecodeError, PydanticValidationError):
                # Skip corrupted backups
                continue

        # Sort by timestamp (newest first)
        backups.sort(key=lambda b: b.timestamp, reverse=True)

        return backups[:limit]

    def restore(self, backup_id: str) -> Config:
        """Restore configuration from backup.

        Args:
            backup_id: Backup identifier

        Returns:
            Restored configuration

        Raises:
            BackupNotFoundError: If backup not found
            BackupCorruptedError: If backup is corrupted
            BackupRestoreError: If restore fails
        """
        backup_path = self._get_backup_path(backup_id)

        if not backup_path.exists():
            raise BackupNotFoundError(
                f"Backup not found: {backup_id}",
                details={"backup_id": backup_id, "path": str(backup_path)},
            )

        try:
            data = json.loads(backup_path.read_text(encoding="utf-8"))
            backup = Backup.model_validate(data)
            return backup.config
        except json.JSONDecodeError as e:
            raise BackupCorruptedError(
                f"Backup is corrupted: {e}",
                details={"backup_id": backup_id, "error": str(e)},
            ) from e
        except PydanticValidationError as e:
            raise BackupCorruptedError(
                f"Backup schema validation failed: {e}",
                details={"backup_id": backup_id, "error": str(e)},
            ) from e
        except Exception as e:
            raise BackupRestoreError(
                f"Failed to restore backup: {e}",
                details={"backup_id": backup_id, "error": str(e)},
            ) from e

    def cleanup(self, keep: int = 5, older_than: Optional[str] = None) -> int:
        """Remove old backups.

        Args:
            keep: Number of recent backups to keep
            older_than: Remove backups older than this (e.g., '7d', '1m')

        Returns:
            Number of backups deleted
        """
        backups = self.list(limit=1000)  # Get all backups

        # Keep only N most recent
        backups_to_delete = backups[keep:]

        deleted_count = 0
        for backup in backups_to_delete:
            backup_path = self._get_backup_path(backup.backup_id)
            if backup_path.exists():
                backup_path.unlink()
                deleted_count += 1

        return deleted_count

    def _get_backup_path(self, backup_id: str) -> Path:
        """Get backup file path.

        Args:
            backup_id: Backup identifier

        Returns:
            Path to backup file
        """
        return self.backup_dir / f"{backup_id}.json"
