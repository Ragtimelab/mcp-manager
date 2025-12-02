# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-12-02

### Added

#### Core Functionality
- **Configuration Management**: Complete CRUD operations for MCP servers
  - Support for three configuration scopes: user (`~/.claude.json`), project (`.mcp.json`), local (`.claude/settings.json`)
  - Atomic file writes with advisory locking for safe concurrent access
  - Environment variable expansion (`${VAR}`, `${VAR:-default}`)
  - Pydantic v2 data models with full validation

- **Backup & Restore System**
  - Automatic backup creation with timestamp-based IDs
  - Metadata support (reason, name)
  - List, restore, and cleanup operations
  - Auto-backup before restore operations

- **CLI Interface** (Typer + Rich)
  - `mcpm list` - List servers with table/JSON output, filtering by scope/type
  - `mcpm show` - Display server details with verbose mode
  - `mcpm add` - Add servers (interactive or flag-based)
  - `mcpm remove` - Remove servers with confirmation prompts
  - `mcpm backup create/list/restore/clean` - Backup management commands
  - `mcpm templates list/show/install` - Template management
  - `mcpm health` - Server health checks
  - Rich terminal output with tables, colors, and icons

- **Template System**
  - Pre-configured templates for common MCP servers
  - Templates: `time`, `fetch`, `filesystem`, `github`
  - `TemplateManager` for loading and installing templates
  - Custom exceptions for template errors

- **Health Check System**
  - `HealthChecker` for verifying server availability
  - STDIO server checks (command existence, `--version` test)
  - HTTP/SSE server checks (connection test with headers)
  - Status types: HEALTHY, UNHEALTHY, UNKNOWN
  - Color-coded CLI output

#### Security
- Command whitelist validation (uvx, npx, node, python, docker, etc.)
- Path traversal prevention
- Dangerous environment variable warnings
- Input validation with safe patterns

#### Quality & Testing
- 258 unit tests with 87% coverage (core modules: 97-100%)
- Cross-platform support: Linux, macOS, Windows
- CI/CD with GitHub Actions (9 platform/version combinations)
- Pre-commit hooks: ruff (lint+format), mypy, YAML/JSON/TOML validation
- Type hints throughout codebase

#### Documentation
- Comprehensive README with installation, usage examples, and development guide
- Detailed TASK.md with implementation phases and progress tracking
- Inline docstrings for all public APIs
- Type annotations for all functions

### Technical Details

#### Architecture
- **Presentation Layer**: CLI (Typer + Rich)
- **Business Logic**: ConfigManager, BackupManager, TemplateManager, HealthChecker
- **Data Layer**: Pydantic models, validators, file handlers
- **Infrastructure**: Atomic I/O, file locking, constants, exceptions

#### Dependencies
- Python >= 3.10
- typer >= 0.12.0
- rich >= 13.7.0
- pydantic >= 2.0.0
- portalocker >= 2.8.0

#### Supported Platforms
- **OS**: Ubuntu, macOS, Windows
- **Python**: 3.10, 3.11, 3.12

### Fixed
- Windows compatibility issues:
  - fcntl module replaced with portalocker for cross-platform file locking
  - UTF-8 encoding explicitly specified for all file operations
  - Platform-specific test skipping for Windows file locking behavior

### Notes
- This is the initial MVP release
- Some advanced features planned for future versions (see TASK.md Phase 7-8)
- Designed for use with Claude Code's MCP server configuration

[0.1.0]: https://github.com/yourusername/mcp-manager/releases/tag/v0.1.0
