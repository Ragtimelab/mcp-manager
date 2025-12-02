# MCP Manager - Project Context

## Project Overview

MCP Manager (`mcpm`) is a CLI tool for managing Model Context Protocol (MCP) servers used by Claude Code.

**Tech Stack**: Python 3.10+ | uv | Typer | Rich | Pydantic v2

## Architecture

4-Layer Architecture:
1. **Presentation**: CLI (Typer + Rich)
2. **Business Logic**: Validators, BackupManager, Templates
3. **Data Access**: ConfigManager (CRUD)
4. **Infrastructure**: FileHandler (Atomic I/O, Locking)

See: `docs/01-architecture.md`

## Core Data Models

```python
class MCPServerType(str, Enum):
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"

class MCPServer(BaseModel):
    type: MCPServerType
    command: Optional[str] = None  # stdio
    args: list[str] = []
    env: dict[str, str] = {}
    url: Optional[str] = None      # http/sse
    headers: dict[str, str] = {}
```

See: `docs/02-data-models.md`

## Key Commands

```bash
mcpm list                    # List servers
mcpm add <name>              # Add server
mcpm remove <name>           # Remove server
mcpm backup create           # Create backup
mcpm health [name]           # Health check
```

See: `docs/03-api-reference.md`

## Module Structure

```
src/mcp_manager/
├── cli.py           # Typer commands
├── config.py        # ConfigManager
├── models.py        # Pydantic models
├── validators.py    # Input validation
├── backup.py        # BackupManager
├── file_handler.py  # Atomic I/O
├── templates.py     # Template system
├── health.py        # Health checks
├── utils.py         # Utilities
├── constants.py     # Constants
└── exceptions.py    # Custom exceptions
```

See: `docs/04-module-design.md`

## Implementation Guidelines

### Code Style

- **Python Version**: 3.10+ (use modern type hints)
- **Formatter**: Black (line-length=100)
- **Linter**: Ruff (select=["E", "F", "I", "N", "W"])
- **Type Checker**: mypy (strict mode)

### Coding Standards

1. **Type Hints**: All functions must have type hints
   ```python
   def add_server(self, name: str, server: MCPServer) -> None:
       ...
   ```

2. **Docstrings**: Google style for public APIs
   ```python
   def validate_server_name(name: str) -> bool:
       """Validate server name format.

       Args:
           name: Server name to validate

       Returns:
           True if valid

       Raises:
           InvalidServerNameError: If name is invalid
       """
   ```

3. **Error Handling**: Explicit exception handling
   ```python
   try:
       config = load_config()
   except ConfigNotFoundError:
       # Handle specific error
       ...
   except ConfigCorruptedError as e:
       # Provide recovery strategy
       ...
   ```

4. **No Shell Execution**: Always use list args
   ```python
   # ✓ Good
   subprocess.run([command] + args, shell=False)

   # ✗ Bad
   subprocess.run(f"{command} {args}", shell=True)
   ```

5. **Atomic Operations**: All file writes must be atomic
   ```python
   def atomic_write(path: Path, content: str):
       temp = path.with_suffix('.tmp')
       temp.write_text(content)
       temp.rename(path)  # Atomic
   ```

### Security Requirements

- **Input Validation**: 3-level validation (Type → Business → Security)
- **Command Whitelist**: Only allow safe commands
- **No Path Traversal**: Reject '..' in paths
- **Environment Filtering**: Warn on dangerous env vars
- **File Locking**: Use fcntl for concurrent access

See: `docs/06-security.md`

### Testing Requirements

- **Coverage**: Minimum 80% overall, 100% for core modules
- **Test Pyramid**: Unit 70%, Integration 20%, E2E 10%
- **Fixtures**: Use pytest fixtures for reusable test data
- **Mocking**: Mock external dependencies (file I/O, subprocess)

See: `docs/07-testing.md`

## Configuration Files

MCP Manager manages these configs:
- `~/.claude.json` - User scope (personal)
- `.mcp.json` - Project scope (team-shared)
- `.claude/settings.json` - Local scope (personal, project-specific)

**Critical**: Only modify `mcpServers` field, preserve other fields!

## Development Workflow

```bash
# Setup
uv sync

# Run tests
uv run pytest --cov

# Format
uv run black src/ tests/

# Lint
uv run ruff check src/ tests/

# Type check
uv run mypy src/

# Run CLI
uv run mcpm --help
```

## Common Patterns

### ConfigManager Usage
```python
manager = ConfigManager()
config = manager.load()
server = MCPServer(type=MCPServerType.STDIO, command="uvx")
manager.add_server("time", server)
manager.save()
```

### Backup Before Modify
```python
backup_manager = BackupManager()
backup = backup_manager.create(config, reason="before_add")
try:
    # Modify config
    manager.add_server(name, server)
except Exception as e:
    # Rollback
    restored = backup_manager.restore(backup.backup_id)
    manager.save(restored)
    raise
```

### Rich Output
```python
from rich.console import Console
from rich.table import Table

console = Console()

# Success
console.print("[green]✓[/] Server added!")

# Error with recovery
console.print("[red]✗[/] Failed to add server")
console.print("\n[yellow]Fix:[/]")
console.print("  1. Check server name format")
console.print("  2. Ensure command exists")
```

## Known Issues & Gotchas

1. **File Locking on Windows**: fcntl not available, use alternative
2. **Environment Variables**: Always expand ${VAR} syntax
3. **JSON Preserving**: Keep unknown fields in Config (extra="allow")
4. **Server Name Validation**: Pattern `^[a-z][a-z0-9_-]{0,63}$`
5. **Pydantic v2**: Use `model_validate()`, not `parse_obj()`

## Resources

- MCP Spec: https://modelcontextprotocol.io
- Claude Code Docs: https://code.claude.com/docs/en/mcp
- Typer Docs: https://typer.tiangolo.com
- Rich Docs: https://rich.readthedocs.io
- Pydantic Docs: https://docs.pydantic.dev

## Design Documents

Complete design documentation in `docs/`:
1. Architecture
2. Data Models
3. API Reference
4. Module Design
5. Error Handling
6. Security
7. Testing
8. Deployment

## Implementation Checklist

See `TASK.md` for detailed implementation tasks.
