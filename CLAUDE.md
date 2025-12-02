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

# Reinstall after changes
uv tool install --force .

# Uninstall
uv tool uninstall mcp-manager
```

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
  - Upgrade: `uvx --refresh <package>`
- **npx-based**: Node.js packages (e.g., `@upstash/context7-mcp`)
  - Upgrade: `npm cache clean --force && npx <package>`

### Command Structure
```
mcpm
├── list (alias: ls)      # List servers with Rich table
├── upgrade (alias: up)   # Upgrade all or specific server
├── health               # Check server executability
├── show                 # Display server config details
└── backup               # Create/list/restore backups
    ├── -l, --list       # List backups
    └── -r, --restore    # Restore from backup
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
3. `uv run python mcpm.py list` works
4. `uv tool install --force .` succeeds
5. `mcpm --help` displays correctly
6. All 6 commands functional (list, upgrade, health, show, backup)
