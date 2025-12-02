# Deployment Strategy

## Overview

MCP Manager는 uv를 사용한 현대적인 Python 패키징 방식을 따릅니다. PyPI 배포를 통해 사용자가 쉽게 설치하고 업데이트할 수 있도록 합니다.

## Packaging with uv

### Project Configuration

```toml
# pyproject.toml
[project]
name = "mcp-manager"
version = "0.1.0"
description = "CLI tool for managing Model Context Protocol (MCP) servers"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
keywords = ["mcp", "model-context-protocol", "cli", "management"]
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Libraries",
    "Topic :: Utilities",
]

dependencies = [
    "typer>=0.12.0",
    "rich>=13.7.0",
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=5.0.0",
    "pytest-xdist>=3.5.0",
    "ruff>=0.6.0",
    "black>=24.0.0",
    "mypy>=1.10.0",
]

[project.scripts]
mcpm = "mcp_manager.cli:main"

[project.urls]
Homepage = "https://github.com/yourusername/mcp-manager"
Repository = "https://github.com/yourusername/mcp-manager"
Documentation = "https://github.com/yourusername/mcp-manager/tree/main/docs"
Issues = "https://github.com/yourusername/mcp-manager/issues"
Changelog = "https://github.com/yourusername/mcp-manager/blob/main/CHANGELOG.md"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatchling.build.targets.wheel]
packages = ["src/mcp_manager"]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "pytest-cov>=5.0.0",
    "pytest-xdist>=3.5.0",
    "ruff>=0.6.0",
    "black>=24.0.0",
    "mypy>=1.10.0",
]

[tool.ruff]
line-length = 100
target-version = "py310"
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]

[tool.ruff.per-file-ignores]
"__init__.py" = ["F401"]

[tool.black]
line-length = 100
target-version = ['py310', 'py311', 'py312']

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = [
    "--strict-markers",
    "--tb=short",
    "--cov=mcp_manager",
    "--cov-report=term-missing",
    "--cov-report=html",
]

[tool.coverage.run]
source = ["src"]
omit = ["tests/*", "**/__pycache__/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
```

---

## Build Process

### Local Build

```bash
# 1. Initialize project (first time)
cd mcp-manager
uv init

# 2. Install dependencies
uv sync

# 3. Run tests
uv run pytest

# 4. Build package
uv build

# Output:
# dist/
# ├── mcp_manager-0.1.0-py3-none-any.whl
# └── mcp_manager-0.1.0.tar.gz
```

---

### Publish to PyPI

```bash
# 1. Build package
uv build

# 2. Check package
uv run twine check dist/*

# 3. Publish to TestPyPI (testing)
uv run twine upload --repository testpypi dist/*

# 4. Test installation from TestPyPI
uv tool install --index-url https://test.pypi.org/simple/ mcp-manager

# 5. Publish to PyPI (production)
uv run twine upload dist/*
```

---

## Installation Methods

### Method 1: uv tool install (Recommended)

```bash
# Install
uv tool install mcp-manager

# Verify
mcpm --version

# Update
uv tool upgrade mcp-manager

# Uninstall
uv tool uninstall mcp-manager
```

**Advantages**:
- Isolated environment
- Fast installation
- Easy updates
- No conflicts with system Python

---

### Method 2: pipx

```bash
# Install pipx
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# Install mcp-manager
pipx install mcp-manager

# Verify
mcpm --version

# Update
pipx upgrade mcp-manager

# Uninstall
pipx uninstall mcp-manager
```

**Advantages**:
- Isolated environment
- Works without uv
- Compatible with pip

---

### Method 3: pip (Not Recommended)

```bash
# Install globally
pip install mcp-manager

# Or in virtualenv
python -m venv .venv
source .venv/bin/activate
pip install mcp-manager

# Update
pip install --upgrade mcp-manager

# Uninstall
pip uninstall mcp-manager
```

**Disadvantages**:
- May conflict with system packages
- Requires manual virtualenv management

---

### Method 4: From Source

```bash
# Clone repository
git clone https://github.com/yourusername/mcp-manager.git
cd mcp-manager

# Install with uv
uv sync
uv run mcpm --version

# Or install in editable mode
uv pip install -e .
```

---

## Versioning Strategy

### Semantic Versioning (SemVer)

```
MAJOR.MINOR.PATCH

- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes
```

### Version History

```
v0.1.0 - Initial MVP
  - list, add, remove commands
  - Basic backup/restore
  - User scope only

v0.2.0 - Enhanced Features
  - Templates system
  - Health checks
  - Project scope support

v0.3.0 - Advanced Features
  - Migration between scopes
  - Doctor command
  - Interactive mode improvements

v1.0.0 - Stable Release
  - Production-ready
  - Full documentation
  - Comprehensive testing
```

---

## Release Process

### 1. Prepare Release

```bash
# Update version in pyproject.toml
[project]
version = "0.2.0"

# Update CHANGELOG.md
## [0.2.0] - 2024-12-15
### Added
- Template system for common servers
- Health check command
### Fixed
- Bug in atomic write
```

---

### 2. Run Tests

```bash
# Full test suite
uv run pytest

# Coverage check
uv run pytest --cov --cov-report=term-missing

# Ensure 80%+ coverage
```

---

### 3. Build & Tag

```bash
# Build package
uv build

# Create git tag
git add .
git commit -m "Release v0.2.0"
git tag -a v0.2.0 -m "Version 0.2.0"
git push origin main
git push origin v0.2.0
```

---

### 4. Publish

```bash
# Publish to PyPI
uv run twine upload dist/*

# Create GitHub Release
gh release create v0.2.0 \
  --title "Release v0.2.0" \
  --notes "See CHANGELOG.md for details" \
  dist/*
```

---

## Distribution Channels

### 1. PyPI (Primary)

```bash
# Users install from PyPI
uv tool install mcp-manager
```

**Advantages**:
- Standard Python distribution
- Wide compatibility
- Easy updates

---

### 2. GitHub Releases

```bash
# Download wheel from GitHub
wget https://github.com/yourusername/mcp-manager/releases/download/v0.2.0/mcp_manager-0.2.0-py3-none-any.whl

# Install
uv tool install mcp_manager-0.2.0-py3-none-any.whl
```

**Advantages**:
- Versioned artifacts
- Release notes
- Changelog

---

### 3. Homebrew (Future)

```ruby
# Formula: homebrew-tap/mcp-manager.rb
class McpManager < Formula
  include Language::Python::Virtualenv

  desc "CLI tool for managing MCP servers"
  homepage "https://github.com/yourusername/mcp-manager"
  url "https://files.pythonhosted.org/packages/.../mcp_manager-0.2.0.tar.gz"
  sha256 "..."
  license "MIT"

  depends_on "python@3.11"

  def install
    virtualenv_install_with_resources
  end

  test do
    system "#{bin}/mcpm", "--version"
  end
end
```

```bash
# Users install via Homebrew
brew tap yourusername/tap
brew install mcp-manager
```

---

### 4. Docker (Optional)

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ src/

# Install dependencies
RUN uv sync --frozen

# Set entrypoint
ENTRYPOINT ["uv", "run", "mcpm"]
```

```bash
# Build image
docker build -t mcp-manager .

# Run
docker run -v ~/.claude.json:/root/.claude.json mcp-manager list
```

---

## Configuration Migration

### Version Compatibility

```python
# config.py
def migrate_config(config: dict, from_version: str) -> dict:
    """Migrate config to latest version"""
    version = config.get("_version", "0.1.0")

    if version == "0.1.0":
        # Migrate 0.1.0 → 0.2.0
        config = migrate_0_1_to_0_2(config)
        version = "0.2.0"

    if version == "0.2.0":
        # Migrate 0.2.0 → 0.3.0
        config = migrate_0_2_to_0_3(config)
        version = "0.3.0"

    config["_version"] = version
    return config

def migrate_0_1_to_0_2(config: dict) -> dict:
    """Migration: 0.1.0 → 0.2.0"""
    # Add new fields with defaults
    for server in config.get("mcpServers", {}).values():
        if "enabled" not in server:
            server["enabled"] = True
    return config
```

---

## Backward Compatibility

### Deprecation Policy

```python
# Minimum 2 minor versions before removal

# v0.2.0: Deprecate old field
def get_server_status(server: dict) -> str:
    if "active" in server:  # Old field
        warnings.warn(
            "'active' field is deprecated, use 'enabled' instead",
            DeprecationWarning,
            stacklevel=2
        )
        return server["active"]
    return server.get("enabled", True)

# v0.4.0: Remove old field
def get_server_status(server: dict) -> str:
    return server.get("enabled", True)
```

---

## Update Mechanism

### Check for Updates

```python
# cli.py
import requests

def check_for_updates():
    """Check if new version available"""
    try:
        response = requests.get(
            "https://pypi.org/pypi/mcp-manager/json",
            timeout=2
        )
        latest = response.json()["info"]["version"]
        current = __version__

        if latest > current:
            console.print(f"[yellow]New version available:[/] {latest}")
            console.print(f"Update: uv tool upgrade mcp-manager")
    except:
        pass  # Silently fail

# Run on startup (async)
if not os.getenv("MCP_SKIP_UPDATE_CHECK"):
    threading.Thread(target=check_for_updates, daemon=True).start()
```

---

## CI/CD Pipeline

### GitHub Actions

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build-and-publish:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Install uv
      uses: astral-sh/setup-uv@v1

    - name: Set up Python
      run: uv python install 3.11

    - name: Install dependencies
      run: uv sync

    - name: Run tests
      run: uv run pytest --cov

    - name: Build package
      run: uv build

    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: uv run twine upload dist/*

    - name: Create GitHub Release
      uses: softprops/action-gh-release@v1
      with:
        files: dist/*
        body_path: CHANGELOG.md
```

---

## Monitoring & Analytics

### Usage Statistics (Optional)

```python
# Anonymous usage tracking
def track_command(command: str):
    """Track command usage (opt-in)"""
    if not os.getenv("MCP_TELEMETRY_ENABLED"):
        return

    try:
        requests.post(
            "https://analytics.example.com/event",
            json={
                "event": "command_executed",
                "command": command,
                "version": __version__,
                "platform": platform.system()
            },
            timeout=1
        )
    except:
        pass  # Never block on analytics
```

---

## Distribution Checklist

### Pre-Release

- [ ] All tests passing
- [ ] Coverage >= 80%
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped
- [ ] No security vulnerabilities

### Release

- [ ] Git tag created
- [ ] Package built
- [ ] Published to PyPI
- [ ] GitHub Release created
- [ ] Documentation deployed

### Post-Release

- [ ] Announcement published
- [ ] Social media posts
- [ ] Monitor for issues
- [ ] Update dependencies

---

## Summary

MCP Manager의 배포 전략은:
- **uv 기반**: 현대적인 Python 패키징
- **PyPI 배포**: 표준 설치 방법
- **SemVer**: 명확한 버전 관리
- **CI/CD**: 자동화된 릴리스
- **호환성**: 마이그레이션 및 deprecation 정책

이 전략을 통해 사용자에게 안정적이고 업데이트하기 쉬운 도구를 제공합니다.
