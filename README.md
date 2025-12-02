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

# Remove server
mcpm remove time

# Enable/disable server
mcpm disable time
mcpm enable time
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

# Install template
mcpm templates install time

# Install with custom name
mcpm templates install time --name my-time-server
```

### Health & Validation

```bash
# Check all servers
mcpm health

# Check specific server
mcpm health time

# Validate configuration
mcpm validate

# Validate and fix issues
mcpm validate --fix

# Diagnose problems
mcpm doctor
```

### Import & Export

```bash
# Export server configuration
mcpm export time --output time-server.json

# Import server configuration
mcpm import time-server.json

# Import to project scope
mcpm import shared.json --scope project
```

## Configuration

MCP Manager works with Claude Code's configuration:

- **User scope**: `~/.claude.json` (personal, all projects)
- **Project scope**: `.mcp.json` (team-shared, version control)
- **Local scope**: `.claude/settings.json` (personal, single project)

## Documentation

Detailed design documentation is available in the `docs/` directory:

1. [Architecture](docs/01-architecture.md) - System design and components
2. [Data Models](docs/02-data-models.md) - Data structures and validation
3. [API Reference](docs/03-api-reference.md) - Complete CLI command reference
4. [Module Design](docs/04-module-design.md) - Code structure and organization
5. [Error Handling](docs/05-error-handling.md) - Exception handling strategies
6. [Security](docs/06-security.md) - Security measures and threat mitigation
7. [Testing](docs/07-testing.md) - Testing strategy and coverage
8. [Deployment](docs/08-deployment.md) - Packaging and distribution

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

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov
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

```bash
# Format code
uv run black src/ tests/

# Lint
uv run ruff check src/ tests/

# Type check
uv run mypy src/
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

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
