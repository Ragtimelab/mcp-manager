# Testing Strategy

## Overview

MCP Manager는 Test Pyramid 접근 방식을 따라 안정적인 품질을 보장합니다. Unit, Integration, E2E 테스트를 조합하여 높은 커버리지와 빠른 피드백을 제공합니다.

## Test Pyramid

```
        /\
       /E2E\      10% - End-to-End Tests
      /______\
     /        \
    /Integration\ 20% - Integration Tests
   /__________\
  /            \
 /  Unit Tests  \  70% - Unit Tests
/________________\
```

### Distribution

- **Unit Tests (70%)**: 각 함수/클래스 독립 테스트
- **Integration Tests (20%)**: 모듈 간 상호작용
- **E2E Tests (10%)**: CLI 실제 실행

---

## Coverage Goals

| Component | Coverage Target | Priority |
|-----------|----------------|----------|
| validators.py | 100% | Critical |
| config.py | 100% | Critical |
| models.py | 100% | Critical |
| file_handler.py | 100% | Critical |
| backup.py | 95% | High |
| cli.py | 90% | High |
| templates.py | 90% | Medium |
| health.py | 85% | Medium |
| utils.py | 85% | Medium |
| **Overall** | **80%+** | Required |

---

## Unit Tests (70%)

### Test Structure

```
tests/unit/
├── test_validators.py
├── test_config.py
├── test_backup.py
├── test_file_handler.py
├── test_models.py
├── test_templates.py
├── test_health.py
└── test_utils.py
```

---

### test_validators.py

```python
import pytest
from mcp_manager.validators import (
    validate_server_name,
    validate_command,
    validate_url,
    validate_server
)
from mcp_manager.exceptions import (
    InvalidServerNameError,
    InvalidCommandError,
    InvalidURLError
)
from mcp_manager.models import MCPServer, MCPServerType

class TestValidateServerName:
    """Test server name validation"""

    def test_valid_names(self):
        """Valid server names should pass"""
        assert validate_server_name("time")
        assert validate_server_name("my-server")
        assert validate_server_name("db_client")
        assert validate_server_name("api2")

    def test_invalid_names(self):
        """Invalid server names should raise error"""
        with pytest.raises(InvalidServerNameError):
            validate_server_name("MyServer")  # Uppercase

        with pytest.raises(InvalidServerNameError):
            validate_server_name("123abc")  # Starts with number

        with pytest.raises(InvalidServerNameError):
            validate_server_name("my server")  # Space

        with pytest.raises(InvalidServerNameError):
            validate_server_name("a" * 65)  # Too long

    def test_reserved_names(self):
        """Reserved names should be rejected"""
        with pytest.raises(ValidationError):
            validate_server_name("system")


class TestValidateCommand:
    """Test command validation"""

    def test_whitelisted_commands(self):
        """Whitelisted commands should pass"""
        assert validate_command("uvx")
        assert validate_command("npx")
        assert validate_command("python")

    def test_non_whitelisted_but_exists(self):
        """Existing commands should pass with warning"""
        assert validate_command("ls")  # Exists on system
        assert validate_command("cat")

    def test_invalid_command(self):
        """Non-existent commands should fail"""
        with pytest.raises(InvalidCommandError):
            validate_command("definitely-not-a-real-command-12345")


class TestValidateServer:
    """Test cross-field server validation"""

    def test_valid_stdio_server(self):
        """Valid stdio server should pass"""
        server = MCPServer(
            type=MCPServerType.STDIO,
            command="uvx",
            args=["mcp-server-time"]
        )
        assert validate_server(server)

    def test_stdio_without_command(self):
        """Stdio server without command should fail"""
        server = MCPServer(
            type=MCPServerType.STDIO,
            command=None
        )
        with pytest.raises(ValidationError):
            validate_server(server)

    def test_http_without_url(self):
        """HTTP server without URL should fail"""
        server = MCPServer(
            type=MCPServerType.HTTP,
            url=None
        )
        with pytest.raises(ValidationError):
            validate_server(server)
```

---

### test_config.py

```python
import pytest
import json
from pathlib import Path
from mcp_manager.config import ConfigManager
from mcp_manager.models import Config, MCPServer, MCPServerType
from mcp_manager.exceptions import (
    ConfigNotFoundError,
    ConfigCorruptedError,
    ServerAlreadyExistsError
)

class TestConfigManager:
    @pytest.fixture
    def temp_config(self, tmp_path):
        """Create temporary config file"""
        config_path = tmp_path / "config.json"
        config_data = {
            "mcpServers": {
                "existing": {
                    "type": "stdio",
                    "command": "uvx",
                    "args": ["mcp-server-time"],
                    "env": {}
                }
            }
        }
        config_path.write_text(json.dumps(config_data, indent=2))
        return config_path

    def test_load_config(self, temp_config):
        """Should load config successfully"""
        manager = ConfigManager(temp_config)
        config = manager.load()

        assert isinstance(config, Config)
        assert "existing" in config.mcpServers

    def test_load_nonexistent_config(self, tmp_path):
        """Should raise ConfigNotFoundError"""
        manager = ConfigManager(tmp_path / "nonexistent.json")

        with pytest.raises(ConfigNotFoundError):
            manager.load()

    def test_load_corrupted_config(self, tmp_path):
        """Should raise ConfigCorruptedError"""
        config_path = tmp_path / "corrupted.json"
        config_path.write_text("{invalid json")

        manager = ConfigManager(config_path)

        with pytest.raises(ConfigCorruptedError):
            manager.load()

    def test_add_server(self, temp_config):
        """Should add new server"""
        manager = ConfigManager(temp_config)

        server = MCPServer(
            type=MCPServerType.STDIO,
            command="npx",
            args=["-y", "@example/server"]
        )

        manager.add_server("newserver", server)

        # Verify
        config = manager.load()
        assert "newserver" in config.mcpServers
        assert config.mcpServers["newserver"].command == "npx"

    def test_add_duplicate_server(self, temp_config):
        """Should raise ServerAlreadyExistsError"""
        manager = ConfigManager(temp_config)

        server = MCPServer(
            type=MCPServerType.STDIO,
            command="uvx"
        )

        with pytest.raises(ServerAlreadyExistsError):
            manager.add_server("existing", server)

    def test_remove_server(self, temp_config):
        """Should remove server"""
        manager = ConfigManager(temp_config)
        manager.remove_server("existing")

        config = manager.load()
        assert "existing" not in config.mcpServers

    def test_get_server(self, temp_config):
        """Should get server by name"""
        manager = ConfigManager(temp_config)
        server = manager.get_server("existing")

        assert server is not None
        assert server.type == MCPServerType.STDIO
```

---

### test_backup.py

```python
import pytest
from datetime import datetime
from mcp_manager.backup import BackupManager
from mcp_manager.models import Config, MCPServer, MCPServerType

class TestBackupManager:
    @pytest.fixture
    def backup_manager(self, tmp_path):
        return BackupManager(tmp_path / "backups")

    @pytest.fixture
    def sample_config(self):
        return Config(
            mcpServers={
                "time": MCPServer(
                    type=MCPServerType.STDIO,
                    command="uvx",
                    args=["mcp-server-time"]
                )
            }
        )

    def test_create_backup(self, backup_manager, sample_config):
        """Should create backup successfully"""
        backup = backup_manager.create(sample_config)

        assert backup.config == sample_config
        assert isinstance(backup.timestamp, datetime)

        # Verify backup file exists
        backup_path = backup_manager._get_backup_path(backup.backup_id)
        assert backup_path.exists()

    def test_list_backups(self, backup_manager, sample_config):
        """Should list all backups"""
        # Create multiple backups
        backup_manager.create(sample_config, reason="backup1")
        backup_manager.create(sample_config, reason="backup2")

        backups = backup_manager.list()
        assert len(backups) == 2

    def test_restore_backup(self, backup_manager, sample_config):
        """Should restore from backup"""
        # Create backup
        backup = backup_manager.create(sample_config)

        # Restore
        restored_config = backup_manager.restore(backup.backup_id)

        assert restored_config.mcpServers == sample_config.mcpServers

    def test_cleanup_old_backups(self, backup_manager, sample_config):
        """Should clean up old backups"""
        # Create 10 backups
        for i in range(10):
            backup_manager.create(sample_config, reason=f"backup{i}")

        # Keep only 5
        removed = backup_manager.cleanup(keep=5)

        assert removed == 5
        assert len(backup_manager.list()) == 5
```

---

## Integration Tests (20%)

### Test Structure

```
tests/integration/
├── test_add_remove_flow.py
├── test_atomic_write.py
├── test_backup_restore.py
└── test_scope_migration.py
```

---

### test_add_remove_flow.py

```python
import pytest
from mcp_manager.config import ConfigManager
from mcp_manager.models import MCPServer, MCPServerType

def test_full_add_remove_cycle(tmp_path):
    """Test complete add and remove workflow"""
    config_path = tmp_path / "config.json"

    # Initialize empty config
    config_path.write_text('{"mcpServers": {}}')

    manager = ConfigManager(config_path)

    # Add server
    server = MCPServer(
        type=MCPServerType.STDIO,
        command="uvx",
        args=["mcp-server-time"]
    )
    manager.add_server("time", server)

    # Verify added
    assert manager.get_server("time") is not None

    # Remove server
    manager.remove_server("time")

    # Verify removed
    assert manager.get_server("time") is None

    # Verify file updated
    manager2 = ConfigManager(config_path)
    assert manager2.get_server("time") is None
```

---

### test_atomic_write.py

```python
import pytest
import threading
import time
from pathlib import Path
from mcp_manager.file_handler import atomic_write

def test_concurrent_writes(tmp_path):
    """Test atomic writes with concurrent access"""
    test_file = tmp_path / "concurrent.txt"
    errors = []

    def write_data(data: str):
        try:
            atomic_write(test_file, data)
        except Exception as e:
            errors.append(e)

    # Spawn multiple threads
    threads = []
    for i in range(10):
        t = threading.Thread(target=write_data, args=(f"data_{i}",))
        threads.append(t)
        t.start()

    # Wait for all
    for t in threads:
        t.join()

    # No errors
    assert len(errors) == 0

    # File exists and has valid content
    assert test_file.exists()
    content = test_file.read_text()
    assert content.startswith("data_")

def test_atomic_write_failure_cleanup(tmp_path):
    """Test cleanup on write failure"""
    test_file = tmp_path / "test.txt"

    # Simulate write error
    with pytest.raises(Exception):
        atomic_write(test_file, None)  # Will raise TypeError

    # Temp file should not exist
    temp_file = test_file.with_suffix('.tmp')
    assert not temp_file.exists()
```

---

### test_backup_restore.py

```python
import pytest
from mcp_manager.config import ConfigManager
from mcp_manager.backup import BackupManager
from mcp_manager.models import MCPServer, MCPServerType

def test_backup_and_restore_workflow(tmp_path):
    """Test full backup and restore cycle"""
    config_path = tmp_path / "config.json"
    backup_dir = tmp_path / "backups"

    config_path.write_text('{"mcpServers": {}}')

    manager = ConfigManager(config_path)
    backup_manager = BackupManager(backup_dir)

    # Add server
    server = MCPServer(
        type=MCPServerType.STDIO,
        command="uvx",
        args=["mcp-server-time"]
    )
    manager.add_server("time", server)

    # Create backup
    config = manager.load()
    backup = backup_manager.create(config)

    # Modify config (break it)
    config_path.write_text("{invalid json")

    # Restore from backup
    restored_config = backup_manager.restore(backup.backup_id)
    manager.save(restored_config)

    # Verify restored
    assert manager.get_server("time") is not None
```

---

## E2E Tests (10%)

### Test Structure

```
tests/e2e/
├── test_cli.py
└── test_interactive.py
```

---

### test_cli.py

```python
import pytest
from typer.testing import CliRunner
from mcp_manager.cli import app

runner = CliRunner()

class TestCLI:
    def test_list_command(self, tmp_path):
        """Test mcpm list command"""
        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "Name" in result.stdout  # Table header

    def test_add_remove_command(self, tmp_path):
        """Test mcpm add and remove"""
        # Add
        result = runner.invoke(app, [
            "add", "test",
            "--type", "stdio",
            "--command", "uvx",
            "--args", "mcp-server-time"
        ])

        assert result.exit_code == 0
        assert "added" in result.stdout.lower()

        # List (verify)
        result = runner.invoke(app, ["list"])
        assert "test" in result.stdout

        # Remove
        result = runner.invoke(app, ["remove", "test", "--force"])
        assert result.exit_code == 0

    def test_backup_commands(self):
        """Test backup create, list, restore"""
        # Create
        result = runner.invoke(app, ["backup", "create"])
        assert result.exit_code == 0

        # List
        result = runner.invoke(app, ["backup", "list"])
        assert result.exit_code == 0

    def test_invalid_command(self):
        """Test error handling"""
        result = runner.invoke(app, [
            "add", "Invalid Name",  # Invalid name
            "--type", "stdio",
            "--command", "uvx"
        ])

        assert result.exit_code != 0
        assert "invalid" in result.stdout.lower()
```

---

## Test Fixtures

### Fixture Structure

```
tests/fixtures/
├── valid_config.json
├── corrupted_config.json
├── empty_config.json
├── duplicate_server_config.json
└── backups/
    └── 20241202-120000.json
```

---

### conftest.py

```python
import pytest
from pathlib import Path

@pytest.fixture
def valid_config_data():
    """Valid config JSON data"""
    return {
        "mcpServers": {
            "time": {
                "type": "stdio",
                "command": "uvx",
                "args": ["mcp-server-time"],
                "env": {}
            },
            "fetch": {
                "type": "stdio",
                "command": "uvx",
                "args": ["mcp-server-fetch"],
                "env": {}
            }
        }
    }

@pytest.fixture
def corrupted_config_data():
    """Corrupted JSON data"""
    return "{invalid json syntax"

@pytest.fixture
def mock_claude_home(tmp_path, monkeypatch):
    """Mock home directory for testing"""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path
```

---

## Mocking Strategy

### Mock File Operations

```python
from unittest.mock import patch, mock_open

def test_with_mock_file():
    """Test using mock file"""
    mock_data = '{"mcpServers": {}}'

    with patch("pathlib.Path.read_text", return_value=mock_data):
        # Test code
        pass
```

---

### Mock External Commands

```python
from unittest.mock import patch

def test_with_mock_subprocess():
    """Test command execution"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        # Test code that runs subprocess
        pass

        # Verify called correctly
        mock_run.assert_called_once_with(
            ["uvx", "mcp-server-time"],
            shell=False
        )
```

---

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=mcp_manager --cov-report=html

# Run specific test file
pytest tests/unit/test_validators.py

# Run specific test class
pytest tests/unit/test_validators.py::TestValidateServerName

# Run specific test
pytest tests/unit/test_validators.py::TestValidateServerName::test_valid_names

# Run with verbose output
pytest -v

# Run and stop at first failure
pytest -x

# Run parallel (faster)
pytest -n auto
```

---

### Test Configuration

```toml
# pyproject.toml
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

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
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
      run: uv run pytest --cov --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

---

## Summary

MCP Manager의 테스트 전략은:
- **Test Pyramid**: Unit 70%, Integration 20%, E2E 10%
- **High Coverage**: 전체 80%+, 핵심 모듈 100%
- **Fast Feedback**: Unit 테스트 우선
- **CI/CD**: 자동화된 테스트 실행
- **Quality**: 회귀 방지 및 리팩토링 안전성

이 전략을 통해 안정적이고 신뢰할 수 있는 소프트웨어를 제공합니다.
