# API Reference

## Overview

`mcpm` (MCP Manager)는 Model Context Protocol 서버를 관리하는 CLI 도구입니다. 모든 명령어는 Typer 기반으로 구현되며 Rich를 사용한 시각적 출력을 제공합니다.

## Command Tree

```
mcpm [OPTIONS] COMMAND [ARGS]...

Commands:
  list      List all MCP servers
  show      Show detailed server information
  add       Add a new MCP server
  remove    Remove an MCP server
  edit      Edit server configuration
  enable    Enable a disabled server
  disable   Disable a server
  backup    Manage configuration backups
  export    Export server configuration
  import    Import server configuration
  health    Check server health
  validate  Validate configuration
  migrate   Migrate server between scopes
  templates Manage server templates
  doctor    Diagnose configuration issues
  version   Show version information
```

---

## Global Options

모든 명령어에서 사용 가능한 옵션:

```bash
--help          Show help message
--version       Show version and exit
--config PATH   Use alternative config file
--verbose       Enable verbose output
--quiet         Suppress non-error output
--no-color      Disable colored output
```

---

## Commands

### `list`

모든 MCP 서버를 나열합니다.

**Synopsis:**
```bash
mcpm list [OPTIONS]
```

**Options:**
```bash
--scope TEXT        Filter by scope [user|project|local]
--format TEXT       Output format [table|json|tree]  [default: table]
--status TEXT       Filter by status [active|inactive|error]
--type TEXT         Filter by type [stdio|sse|http]
```

**Examples:**
```bash
# List all servers in table format
mcpm list

# List only user-level servers
mcpm list --scope user

# List as JSON
mcpm list --format json

# List only stdio servers
mcpm list --type stdio

# List inactive servers
mcpm list --status inactive
```

**Output (table format):**
```
┏━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Name      ┃ Scope ┃ Type         ┃ Command/URL          ┃ Status  ┃
┡━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ time      │ user  │ stdio        │ uvx mcp-server-time  │ ✓ active│
│ fetch     │ user  │ stdio        │ uvx mcp-server-fetch │ ✓ active│
│ github    │ proj  │ http         │ https://api.github...│ ✓ active│
└───────────┴───────┴──────────────┴──────────────────────┴─────────┘
```

**Output (json format):**
```json
{
  "servers": [
    {
      "name": "time",
      "scope": "user",
      "type": "stdio",
      "command": "uvx",
      "args": ["mcp-server-time"],
      "status": "active"
    }
  ]
}
```

**Exit Codes:**
- `0`: Success
- `1`: Error (e.g., config not found)

---

### `show`

특정 서버의 상세 정보를 표시합니다.

**Synopsis:**
```bash
mcpm show NAME [OPTIONS]
```

**Arguments:**
```bash
NAME    Server name (required)
```

**Options:**
```bash
--verbose    Show all details including env vars
--json       Output as JSON
```

**Examples:**
```bash
# Show server info
mcpm show time

# Show with all details
mcpm show time --verbose

# Output as JSON
mcpm show time --json
```

**Output:**
```
Server: time
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Type:       stdio
Scope:      user
Command:    uvx
Arguments:  mcp-server-time
Env Vars:   (none)
Status:     ✓ Active
Config Path: ~/.claude.json
```

**Exit Codes:**
- `0`: Success
- `1`: Server not found
- `2`: Invalid server name

---

### `add`

새 MCP 서버를 추가합니다.

**Synopsis:**
```bash
mcpm add NAME [OPTIONS]
```

**Arguments:**
```bash
NAME    Server name (required)
```

**Options:**
```bash
--type TEXT         Server type [stdio|sse|http]  [required]
--scope TEXT        Configuration scope [user|project|local]  [default: user]
--command TEXT      Command to run (stdio only)
--args TEXT         Command arguments (can be specified multiple times)
--env TEXT          Environment variables (KEY=VALUE format, multiple)
--url TEXT          Server URL (http/sse only)
--header TEXT       HTTP headers (KEY=VALUE format, multiple)
--interactive       Interactive mode
--dry-run           Show what would be done without making changes
--backup            Create backup before adding
```

**Examples:**
```bash
# Interactive mode (recommended for first-time users)
mcpm add my-server --interactive

# Add stdio server (non-interactive)
mcpm add time --type stdio --command uvx --args mcp-server-time

# Add stdio server with multiple args
mcpm add db --type stdio --command npx --args -y --args @bytebase/dbhub

# Add stdio server with env vars
mcpm add custom --type stdio --command python \
  --args /path/to/server.py \
  --env DB_URL=localhost:5432 \
  --env NODE_ENV=production

# Add HTTP server
mcpm add github --type http --url https://api.githubcopilot.com/mcp/

# Add HTTP server with authentication
mcpm add sentry --type http \
  --url https://mcp.sentry.dev/mcp \
  --header "Authorization=Bearer ${SENTRY_TOKEN}"

# Add to project scope
mcpm add shared-db --type stdio --scope project \
  --command npx --args @bytebase/dbhub

# Dry run (preview)
mcpm add test --type stdio --command uvx --dry-run

# Add with auto backup
mcpm add critical --type stdio --command uvx --backup
```

**Interactive Mode Flow:**
```
What is the server name? time
Select server type:
  1. stdio (Local process)
  2. http (Remote HTTP server)
  3. sse (Server-Sent Events)
> 1

Command to run: uvx
Command arguments (comma-separated): mcp-server-time
Environment variables (KEY=VALUE, comma-separated): [Enter for none]

Configuration Preview:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Name:    time
Type:    stdio
Command: uvx mcp-server-time
Scope:   user

Add this server? [Y/n]: y

✓ Server 'time' added successfully!
```

**Exit Codes:**
- `0`: Success
- `1`: Server already exists
- `2`: Validation error
- `3`: Permission error

---

### `remove`

MCP 서버를 삭제합니다.

**Synopsis:**
```bash
mcpm remove NAME [OPTIONS]
```

**Arguments:**
```bash
NAME    Server name (required)
```

**Options:**
```bash
--scope TEXT    Scope to remove from [user|project|local]
--force         Skip confirmation
--backup        Create backup before removing
```

**Examples:**
```bash
# Remove server (with confirmation)
mcpm remove time

# Remove without confirmation
mcpm remove time --force

# Remove with auto backup
mcpm remove time --backup

# Remove from specific scope
mcpm remove shared-db --scope project
```

**Output:**
```
Server: time
  Type: stdio
  Command: uvx mcp-server-time

Remove this server? [y/N]: y

✓ Server 'time' removed successfully!
```

**Exit Codes:**
- `0`: Success
- `1`: Server not found
- `2`: User cancelled

---

### `edit`

서버 설정을 대화형으로 수정합니다.

**Synopsis:**
```bash
mcpm edit NAME [OPTIONS]
```

**Arguments:**
```bash
NAME    Server name (required)
```

**Options:**
```bash
--editor TEXT    Editor to use (default: $EDITOR or vi)
--backup         Create backup before editing
```

**Examples:**
```bash
# Edit in default editor
mcpm edit time

# Edit with specific editor
mcpm edit time --editor nano

# Edit with auto backup
mcpm edit time --backup
```

**Exit Codes:**
- `0`: Success
- `1`: Server not found
- `2`: Validation error after edit

---

### `enable` / `disable`

서버를 활성화하거나 비활성화합니다.

**Synopsis:**
```bash
mcpm enable NAME
mcpm disable NAME
```

**Arguments:**
```bash
NAME    Server name (required)
```

**Examples:**
```bash
# Disable server
mcpm disable time

# Enable server
mcpm enable time
```

**Output:**
```
✓ Server 'time' disabled
✓ Server 'time' enabled
```

**Exit Codes:**
- `0`: Success
- `1`: Server not found

---

### `backup`

설정 백업을 관리합니다.

**Synopsis:**
```bash
mcpm backup COMMAND [OPTIONS]
```

**Subcommands:**

#### `backup create`
```bash
mcpm backup create [OPTIONS]

Options:
  --name TEXT    Backup name (default: auto-generated timestamp)
  --reason TEXT  Reason for backup
```

**Examples:**
```bash
# Create backup with auto name
mcpm backup create

# Create named backup
mcpm backup create --name before-update

# Create backup with reason
mcpm backup create --reason "Before major changes"
```

**Output:**
```
✓ Backup created: 20241202-120000
  Path: ~/.mcp-manager/backups/20241202-120000.json
```

#### `backup list`
```bash
mcpm backup list

Options:
  --limit INT    Show only N most recent backups [default: 10]
```

**Output:**
```
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┓
┃ Backup ID       ┃ Timestamp           ┃ Reason             ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━┩
│ 20241202-120000 │ 2024-12-02 12:00:00 │ Before update      │
│ 20241201-180000 │ 2024-12-01 18:00:00 │ Auto backup        │
└─────────────────┴─────────────────────┴────────────────────┘
```

#### `backup restore`
```bash
mcpm backup restore BACKUP_ID

Arguments:
  BACKUP_ID    Backup ID or path
```

**Examples:**
```bash
# Restore from backup ID
mcpm backup restore 20241202-120000

# Restore from path
mcpm backup restore ~/.mcp-manager/backups/20241202-120000.json
```

**Output:**
```
Restoring backup: 20241202-120000
  Created: 2024-12-02 12:00:00
  Servers: 4

This will overwrite current configuration!
Continue? [y/N]: y

✓ Configuration restored successfully!
```

#### `backup clean`
```bash
mcpm backup clean [OPTIONS]

Options:
  --keep INT    Number of backups to keep [default: 5]
  --older-than TEXT    Remove backups older than (e.g., '7d', '1m')
```

**Examples:**
```bash
# Keep only 5 most recent
mcpm backup clean --keep 5

# Remove backups older than 7 days
mcpm backup clean --older-than 7d
```

---

### `export` / `import`

서버 설정을 내보내거나 가져옵니다.

**Synopsis:**
```bash
mcpm export NAME [OPTIONS]
mcpm import FILE [OPTIONS]
```

**export Options:**
```bash
--output PATH    Output file path (default: stdout)
--format TEXT    Output format [json|yaml] [default: json]
```

**import Options:**
```bash
--scope TEXT     Import to scope [user|project|local] [default: user]
--force          Overwrite if exists
```

**Examples:**
```bash
# Export server to file
mcpm export time --output time-server.json

# Export to stdout
mcpm export time

# Import server
mcpm import time-server.json

# Import to project scope
mcpm import shared.json --scope project

# Import and overwrite
mcpm import time-server.json --force
```

---

### `health`

서버 상태를 확인합니다.

**Synopsis:**
```bash
mcpm health [NAME] [OPTIONS]
```

**Arguments:**
```bash
NAME    Server name (optional, check all if not specified)
```

**Options:**
```bash
--timeout INT    Timeout in seconds [default: 10]
--fix            Attempt to fix issues
```

**Examples:**
```bash
# Check all servers
mcpm health

# Check specific server
mcpm health time

# Check with auto-fix
mcpm health --fix
```

**Output:**
```
Checking server health...

time          ✓ Healthy
fetch         ✓ Healthy
broken-server ✗ Failed to connect
  Error: Command not found: invalid-cmd
  Fix: Install 'invalid-cmd' or update command path

Summary: 2/3 healthy
```

---

### `validate`

설정 파일을 검증합니다.

**Synopsis:**
```bash
mcpm validate [OPTIONS]
```

**Options:**
```bash
--fix          Attempt to fix issues automatically
--strict       Enable strict validation
--format TEXT  Output format [text|json] [default: text]
```

**Examples:**
```bash
# Validate configuration
mcpm validate

# Validate and fix
mcpm validate --fix

# Strict validation
mcpm validate --strict
```

**Output:**
```
Validating configuration...

✓ JSON syntax valid
✓ Schema valid
⚠ Warning: Server 'old' uses deprecated SSE transport
✗ Error: Server 'broken' missing required 'command' field

Issues found: 1 error, 1 warning
```

---

### `migrate`

서버 설정을 scope 간 이동합니다.

**Synopsis:**
```bash
mcpm migrate NAME --to SCOPE [OPTIONS]
```

**Arguments:**
```bash
NAME    Server name (required)
```

**Options:**
```bash
--to TEXT      Target scope [user|project|local] (required)
--remove       Remove from source after migration
```

**Examples:**
```bash
# Migrate to project scope
mcpm migrate db --to project

# Migrate and remove from source
mcpm migrate db --to project --remove
```

---

### `templates`

서버 템플릿을 관리합니다.

**Synopsis:**
```bash
mcpm templates COMMAND [OPTIONS]
```

**Subcommands:**

#### `templates list`
```bash
mcpm templates list
```

**Output:**
```
Available Templates:
  time        - Current time server
  fetch       - URL fetching server
  filesystem  - Local filesystem access
  github      - GitHub Copilot MCP
  sentry      - Sentry monitoring
```

#### `templates install`
```bash
mcpm templates install TEMPLATE_NAME [OPTIONS]

Arguments:
  TEMPLATE_NAME    Template name

Options:
  --name TEXT      Custom server name
  --scope TEXT     Installation scope [default: user]
```

**Examples:**
```bash
# Install template
mcpm templates install time

# Install with custom name
mcpm templates install time --name my-time-server
```

---

### `doctor`

설정 문제를 진단하고 해결책을 제안합니다.

**Synopsis:**
```bash
mcpm doctor [OPTIONS]
```

**Options:**
```bash
--fix    Attempt to fix issues automatically
```

**Examples:**
```bash
# Diagnose issues
mcpm doctor

# Diagnose and fix
mcpm doctor --fix
```

**Output:**
```
Running diagnostics...

✓ Config file exists
✓ Config file readable
✓ JSON syntax valid
✗ Permission issue: ~/.claude.json is not writable
  Fix: chmod 644 ~/.claude.json
⚠ Unused servers: old-test, debug-server
  Suggestion: Remove with 'mcpm remove <name>'

Summary: 1 error, 1 warning
```

---

### `version`

버전 정보를 표시합니다.

**Synopsis:**
```bash
mcpm version
```

**Output:**
```
mcpm version 0.1.0
Python 3.11.0
uv 0.5.0
```

---

## Output Formats

### Table (Default)
Rich Table 형식으로 보기 좋게 출력합니다.

### JSON
기계 판독 가능한 JSON 형식으로 출력합니다.
```json
{
  "servers": [...],
  "count": 3
}
```

### Tree
계층적 구조를 트리 형식으로 표시합니다.
```
📦 MCP Servers
├── 🌐 User Scope
│   ├── time (stdio)
│   └── fetch (stdio)
└── 📁 Project Scope
    └── github (http)
```

---

## Environment Variables

```bash
MCP_CONFIG_PATH    # Override default config path
MCPM_NO_COLOR      # Disable colored output
MCPM_VERBOSE       # Enable verbose mode
MCPM_BACKUP_DIR    # Custom backup directory
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0    | Success |
| 1    | General error |
| 2    | Validation error |
| 3    | Permission error |
| 4    | Not found |
| 5    | Already exists |

---

## Common Workflows

### First-time Setup
```bash
# Add your first server
mcpm add time --interactive

# List servers
mcpm list

# Check health
mcpm health
```

### Daily Usage
```bash
# Add a new server
mcpm add db --type stdio --command npx --args @bytebase/dbhub

# Check it works
mcpm health db

# Backup before changes
mcpm backup create

# Remove old server
mcpm remove old-server
```

### Team Collaboration
```bash
# Add shared project server
mcpm add shared-api --type http --scope project \
  --url https://api.example.com/mcp

# Export for sharing
mcpm export shared-api --output shared.json

# Team member imports
mcpm import shared.json --scope project
```

---

## Summary

MCP Manager CLI는:
- **직관적**: Interactive 모드 지원
- **안전함**: Backup, dry-run, validation
- **유연함**: 다양한 출력 포맷
- **강력함**: 전문가를 위한 플래그 옵션

모든 명령어는 `--help`로 상세 도움말을 확인할 수 있습니다.
