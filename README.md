# MCP Manager

CLI tool for managing Model Context Protocol (MCP) servers for Claude Code.

## Features

- **Easy Server Management**: Add, remove, list, and configure MCP servers
- **Backup & Restore**: Automatic backups before changes with easy restoration
- **Multiple Scopes**: Manage servers at user, project, or local level
- **Template System**: Quick installation from pre-configured templates
- **Health Checks**: Verify server connectivity and configuration
- **Interactive Mode**: Step-by-step guided server setup
- **Rich Output**: Beautiful terminal output with tables and colors

## Installation

### Recommended: uv

```bash
uv tool install mcp-manager
```

### Alternative: pipx

```bash
pipx install mcp-manager
```

### Alternative: pip

```bash
pip install mcp-manager
```

## Quick Start

```bash
# List all MCP servers
mcpm list

# Add a new server (interactive)
mcpm add my-server --interactive

# Add a server (non-interactive)
mcpm add time --type stdio --command uvx --args mcp-server-time

# Check server health
mcpm health

# Create a backup
mcpm backup create

# Show detailed help
mcpm --help
```

## Usage Examples

### Managing Servers

```bash
# List all servers
mcpm list

# List with filters
mcpm list --scope user --type stdio

# Show server details
mcpm show time

# Add stdio server
mcpm add time \
  --type stdio \
  --command uvx \
  --args mcp-server-time

# Add HTTP server
mcpm add github \
  --type http \
  --url https://api.githubcopilot.com/mcp/

# Add server with environment variables
mcpm add custom \
  --type stdio \
  --command python \
  --args /path/to/server.py \
  --env DB_URL=localhost:5432 \
  --env NODE_ENV=production

# Remove server (with confirmation)
mcpm remove time

# Remove without confirmation
mcpm remove time --force
```

### Backup & Restore

```bash
# Create backup
mcpm backup create

# Create named backup
mcpm backup create --name before-update

# List backups
mcpm backup list

# Restore from backup
mcpm backup restore 20241202-120000

# Clean old backups (keep 5)
mcpm backup clean --keep 5
```

### Templates

```bash
# List available templates
mcpm templates list

# Show template details
mcpm templates show time

# Install template
mcpm templates install time

# Install with custom name
mcpm templates install time --name my-time-server

# Install to project scope
mcpm templates install github --scope project
```

### Health Checks

```bash
# Check all servers
mcpm health

# Check specific server
mcpm health time

# Check servers in project scope
mcpm health --scope project
```

## Configuration

MCP Manager works with Claude Code's configuration:

- **User scope**: `~/.claude.json` (personal, all projects)
- **Project scope**: `.mcp.json` (team-shared, version control)
- **Local scope**: `.claude/settings.json` (personal, single project)

## Available Commands

```bash
# Server Management
mcpm list [--scope SCOPE] [--type TYPE] [--format FORMAT]
mcpm show NAME [--scope SCOPE] [--verbose]
mcpm add NAME [--type TYPE] [--command CMD] [--args ARGS...] [--env KEY=VALUE...] [--interactive]
mcpm remove NAME [--scope SCOPE] [--force]

# Backup & Restore
mcpm backup create [--name NAME]
mcpm backup list [--limit N]
mcpm backup restore BACKUP_ID [--scope SCOPE] [--force]
mcpm backup clean [--keep N] [--force]

# Templates
mcpm templates list
mcpm templates show NAME
mcpm templates install NAME [--name CUSTOM_NAME] [--scope SCOPE]

# Health Check
mcpm health [NAME] [--scope SCOPE]

# Help
mcpm --help
mcpm COMMAND --help
```

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/yourusername/mcp-manager.git
cd mcp-manager

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Install pre-commit hooks (recommended)
uv run pre-commit install

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov
```

### Pre-commit Hooks

This project uses [pre-commit](https://pre-commit.com/) to ensure code quality before commits.

**Setup** (one-time):
```bash
uv run pre-commit install
```

**What runs on each commit:**
- ✅ Ruff linting with auto-fix
- ✅ Ruff formatting
- ✅ Mypy type checking
- ✅ Trailing whitespace removal
- ✅ YAML/TOML/JSON validation
- ✅ Large file detection
- ✅ Debug statement detection

**Manual run** (optional):
```bash
# Run on all files
uv run pre-commit run --all-files

# Run specific hook
uv run pre-commit run ruff --all-files
```

**Skip hooks** (if needed):
```bash
git commit --no-verify
```

### Project Structure

```
mcp-manager/
├── src/mcp_manager/    # Source code
├── tests/              # Test suite
├── docs/               # Design documentation
├── templates/          # Server templates
└── pyproject.toml      # Project configuration
```

### Running Tests

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov

# Specific test
uv run pytest tests/unit/test_validators.py

# Parallel execution
uv run pytest -n auto
```

### Code Quality

**Automated** (via pre-commit hooks):
```bash
# Runs on every commit automatically after `pre-commit install`
git commit -m "Your changes"
```

**Manual**:
```bash
# Run all quality checks
uv run pre-commit run --all-files

# Individual commands
uv run ruff check src/ tests/     # Lint
uv run ruff format src/ tests/    # Format
uv run mypy src/                  # Type check
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Install pre-commit hooks: `uv run pre-commit install`
4. Add tests for new functionality
5. Ensure all tests pass and pre-commit checks succeed
6. Submit a pull request

All pull requests are automatically checked by CI for:
- Code quality (ruff + mypy)
- Test coverage (pytest)
- Cross-platform compatibility (Linux, macOS, Windows)

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/mcp-manager/issues)
- **Documentation**: [docs/](docs/)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/mcp-manager/discussions)

## Related Projects

- [Claude Code](https://claude.com/claude-code) - The official Claude CLI
- [Model Context Protocol](https://modelcontextprotocol.io) - MCP specification

---

Made with ❤️ for the Claude Code community
