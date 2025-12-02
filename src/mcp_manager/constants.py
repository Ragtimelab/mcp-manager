"""Global constants for MCP Manager."""

from pathlib import Path

# Config file paths
DEFAULT_CONFIG_PATH = Path.home() / ".claude.json"
PROJECT_CONFIG_PATH = Path.cwd() / ".mcp.json"
LOCAL_CONFIG_PATH = Path.cwd() / ".claude" / "settings.json"

# Backup configuration
DEFAULT_BACKUP_DIR = Path.home() / ".mcp-manager" / "backups"
DEFAULT_BACKUP_KEEP = 5

# Security: Allowed commands (whitelist)
ALLOWED_COMMANDS = {"uvx", "npx", "node", "python", "python3", "docker"}

# Security: Dangerous environment variables
DANGEROUS_ENV_VARS = {
    "PATH",
    "LD_LIBRARY_PATH",
    "LD_PRELOAD",
    "DYLD_LIBRARY_PATH",
    "DYLD_INSERT_LIBRARIES",
    "PYTHONPATH",
    "NODE_PATH",
}

# Validation patterns
SERVER_NAME_PATTERN = r"^[a-z][a-z0-9_-]{0,63}$"

# Reserved server names
RESERVED_NAMES = {"system", "root", "admin", "config"}

# Timeouts (seconds)
DEFAULT_HEALTH_TIMEOUT = 10
DEFAULT_LOCK_TIMEOUT = 5
