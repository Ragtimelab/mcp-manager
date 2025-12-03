# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`mcp-manager` is a simple CLI tool for managing MCP (Model Context Protocol) servers. It provides brew-like upgrade functionality for MCP servers configured in `~/.claude.json`.

**Architecture**: Single-file Python CLI (~230 lines) - intentionally kept simple to avoid over-engineering.

## Development Commands

### Local Development
```bash
# Run without installing
uv run python mcpm.py list
uv run python mcpm.py --help

# Run specific command
uv run python mcpm.py upgrade
uv run python mcpm.py health
```

### Code Quality
```bash
# Linting
uv run ruff check mcpm.py

# Auto-format
uv run ruff format mcpm.py

# Type checking
uv run mypy mcpm.py
```

### Installation
```bash
# Install globally as tool
uv tool install .

# Reinstall after code changes (IMPORTANT: use --reinstall, not --force)
uv tool install --reinstall .

# Uninstall
uv tool uninstall mcp-manager
```

**Important**: When updating local packages (`.`), use `--reinstall` to force rebuild from source.
`--force` only reinstalls dependencies but may use cached build artifacts.

## Key Architecture Decisions

### Single-File Design
- **File**: `mcpm.py` (all code in one file)
- **Rationale**: Avoids over-engineering for a simple automation tool
- **No src/ directory**: Direct module entry via `pyproject.toml`

### Configuration Target
- **Location**: `~/.claude.json` (Claude Code's MCP server config)
- **Format**: JSON with `mcpServers` object
- **Backup location**: `~/.mcp-manager/backups/`

### MCP Server Types
The tool handles two types of MCP servers:
- **uvx-based**: Python packages (e.g., `mcp-server-time`)
  - Upgrade: `uvx --refresh <package> --help` (verifies installation)
- **npx-based**: Node.js packages (e.g., `@upstash/context7-mcp`)
  - Upgrade: `npm cache clean --force` only (no pre-download)
  - Rationale: npx downloads on actual use; pre-verification causes timeouts for large packages

### Command Structure
```
mcpm
├── list (alias: ls)      # List servers with Rich table
├── upgrade (alias: up)   # Upgrade all or specific server
├── health               # Check server executability
├── show                 # Display server config details
├── backup               # Create/list/restore/delete backups
│   ├── -l, --list       # List backups
│   ├── -r, --restore    # Restore from backup
│   ├── -d, --delete     # Delete specific backup
│   ├── --clean          # Clean up old backups
│   ├── --keep N         # Keep N recent backups (use with --clean)
│   └── --force          # Skip confirmation
├── install              # Install and configure MCP server
├── uninstall            # Remove MCP server from configuration
├── disable              # Temporarily disable MCP server
├── enable               # Re-enable disabled MCP server
└── doctor               # Diagnose MCP configuration issues
```

## Important Constraints

### Build Configuration
```toml
[tool.hatch.build.targets.wheel]
packages = ["mcpm.py"]  # Must explicitly list the single file
```
**Critical**: Do not use `packages = ["."]` - it breaks module resolution.

### CLI Framework Limitations
- **No `-h` support**: Typer/Click only support `--help` by default
- **Do not attempt**: Adding `-h` via callbacks or context_settings (tested, doesn't work in installed tools)

### Code Quality Standards
- **No bare except**: Use specific exceptions (e.g., `except ValueError`)
- **Type hints**: Required for all function signatures
- **Formatting**: Enforced by ruff (line length, PEP 8)

## Design Principles (from project)

1. **추측 금지, 검증 우선**: All inputs validated (file existence, JSON parsing, server names)
2. **우회 금지, 근본 해결**: Direct subprocess execution, no wrappers
3. **아첨 금지, 비판적 사고**: Comprehensive error case handling

## Dependencies

### Runtime
- `typer>=0.12.0` - CLI framework
- `rich>=13.7.0` - Terminal output formatting

### Development
- `ruff>=0.14.7` - Linter and formatter
- `mypy>=1.19.0` - Type checker

## Testing Checklist

When making changes, verify:
1. `uv run ruff check mcpm.py` passes
2. `uv run mypy mcpm.py` passes
3. `uv run python mcpm.py list` works (local test)
4. `uv tool install --reinstall .` succeeds (rebuild from source)
5. `mcpm --help` displays correctly (installed version)
6. All 10 commands functional:
   - `mcpm list` / `mcpm ls`
   - `mcpm upgrade` / `mcpm up`
   - `mcpm health`
   - `mcpm show <server>`
   - `mcpm backup` / `mcpm backup -l` / `mcpm backup -r <id>` / `mcpm backup -d <id>` / `mcpm backup --clean`
   - `mcpm install <package>`
   - `mcpm uninstall <server>`
   - `mcpm disable <server>`
   - `mcpm enable <server>`
   - `mcpm doctor` (diagnostics)
