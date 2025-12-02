# Module Design

## Overview

MCP Manager는 명확한 책임 분리를 위해 모듈화된 구조로 설계되었습니다. 각 모듈은 단일 책임을 가지며, 잘 정의된 인터페이스를 통해 통신합니다.

## Project Structure

```
mcp-manager/
├── pyproject.toml           # Project metadata, dependencies
├── uv.lock                  # Lock file (uv)
├── README.md                # User documentation
├── LICENSE                  # MIT License
├── .gitignore              # Git ignore rules
│
├── src/
│   └── mcp_manager/
│       ├── __init__.py          # Package initialization
│       ├── cli.py               # CLI commands (Typer app)
│       ├── config.py            # ConfigManager
│       ├── models.py            # Pydantic models
│       ├── validators.py        # Validation logic
│       ├── backup.py            # BackupManager
│       ├── file_handler.py      # Atomic I/O, locking
│       ├── templates.py         # Template system
│       ├── health.py            # Health checks
│       ├── utils.py             # Utility functions
│       ├── constants.py         # Global constants
│       └── exceptions.py        # Custom exceptions
│
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── test_validators.py
│   │   ├── test_config.py
│   │   ├── test_backup.py
│   │   └── test_file_handler.py
│   ├── integration/
│   │   ├── test_add_remove_flow.py
│   │   ├── test_atomic_write.py
│   │   └── test_backup_restore.py
│   ├── e2e/
│   │   ├── test_cli.py
│   │   └── test_interactive.py
│   └── fixtures/
│       ├── valid_config.json
│       ├── corrupted_config.json
│       └── backups/
│
├── templates/               # MCP server templates
│   ├── time.json
│   ├── fetch.json
│   ├── filesystem.json
│   └── github.json
│
└── docs/                    # Design documentation
    ├── 01-architecture.md
    ├── 02-data-models.md
    ├── 03-api-reference.md
    ├── 04-module-design.md
    ├── 05-error-handling.md
    ├── 06-security.md
    ├── 07-testing.md
    ├── 08-deployment.md
    └── diagrams/
```

---

## Module Descriptions

### `cli.py` - Command Line Interface

**Responsibility**: 사용자 입력 처리 및 출력 표시

**Public API**:
```python
import typer
from rich.console import Console

app = typer.Typer(help="MCP Manager - Manage MCP servers")
console = Console()

@app.command()
def list(
    scope: Optional[Scope] = None,
    format: str = "table"
) -> None:
    """List all MCP servers"""
    ...

@app.command()
def add(
    name: str,
    type: MCPServerType,
    command: Optional[str] = None,
    ...
) -> None:
    """Add a new MCP server"""
    ...
```

**Dependencies**:
- `config.ConfigManager`: 설정 읽기/쓰기
- `validators.*`: 입력 검증
- `models.*`: 데이터 모델
- `rich.*`: 출력 포맷팅

**Key Responsibilities**:
- Typer 명령어 정의
- 사용자 입력 파싱
- Rich 기반 출력 (Table, Tree, JSON)
- 에러 메시지 표시

---

### `config.py` - Configuration Manager

**Responsibility**: 설정 파일 CRUD 연산

**Public API**:
```python
from pathlib import Path
from typing import Optional

class ConfigManager:
    """Manage MCP server configuration"""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self._default_config_path()
        self._config: Optional[Config] = None

    def load(self) -> Config:
        """Load configuration from file"""
        ...

    def save(self, config: Config) -> None:
        """Save configuration to file"""
        ...

    def add_server(self, name: str, server: MCPServer) -> None:
        """Add a new server to configuration"""
        ...

    def remove_server(self, name: str) -> None:
        """Remove server from configuration"""
        ...

    def get_server(self, name: str) -> Optional[MCPServer]:
        """Get server by name"""
        ...

    def list_servers(
        self,
        scope: Optional[Scope] = None,
        server_type: Optional[MCPServerType] = None
    ) -> dict[str, MCPServer]:
        """List servers with optional filters"""
        ...
```

**Dependencies**:
- `models.Config`, `models.MCPServer`: 데이터 모델
- `file_handler.atomic_write`, `file_handler.file_lock`: 파일 I/O
- `exceptions.ConfigError`: 예외

**Key Responsibilities**:
- ~/.claude.json 읽기/쓰기
- 서버 추가/삭제/수정
- Scope 관리 (user/project/local)
- Config 캐싱

---

### `models.py` - Data Models

**Responsibility**: 데이터 구조 정의 및 검증

**Public API**:
```python
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional

class MCPServerType(str, Enum):
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"

class MCPServer(BaseModel):
    type: MCPServerType
    command: Optional[str] = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    url: Optional[str] = None
    headers: dict[str, str] = Field(default_factory=dict)

class Config(BaseModel):
    mcpServers: dict[str, MCPServer] = Field(default_factory=dict)
    # ... other fields

class Backup(BaseModel):
    timestamp: datetime
    config: Config
    metadata: dict[str, str] = Field(default_factory=dict)
```

**Dependencies**:
- `pydantic`: 타입 검증

**Key Responsibilities**:
- Pydantic 모델 정의
- 자동 타입 검증
- JSON 직렬화/역직렬화
- Field validators

---

### `validators.py` - Validation Logic

**Responsibility**: 비즈니스 규칙 검증

**Public API**:
```python
import re
import shutil
from typing import Optional

def validate_server_name(name: str) -> bool:
    """Validate server name format"""
    pattern = r'^[a-z][a-z0-9_-]{0,63}$'
    if not re.match(pattern, name):
        raise InvalidServerNameError(
            f"Invalid name '{name}': must be lowercase alphanumeric"
        )
    return True

def validate_command(command: str) -> bool:
    """Validate command exists and is allowed"""
    ALLOWED = {"uvx", "npx", "node", "python", "python3", "docker"}

    if command not in ALLOWED and not shutil.which(command):
        raise InvalidCommandError(
            f"Command '{command}' not found. Allowed: {ALLOWED}"
        )
    return True

def validate_url(url: str) -> bool:
    """Validate URL format"""
    from pydantic import HttpUrl
    try:
        HttpUrl(url)
        return True
    except ValidationError:
        raise InvalidURLError(f"Invalid URL: {url}")

def validate_server(server: MCPServer) -> bool:
    """Cross-field server validation"""
    if server.type == MCPServerType.STDIO:
        if not server.command:
            raise ValidationError("stdio servers require 'command'")
        validate_command(server.command)

    if server.type in (MCPServerType.HTTP, MCPServerType.SSE):
        if not server.url:
            raise ValidationError(f"{server.type} servers require 'url'")
        validate_url(server.url)

    return True
```

**Dependencies**:
- `models.MCPServer`, `models.MCPServerType`: 데이터 모델
- `exceptions.ValidationError`: 예외

**Key Responsibilities**:
- 서버 이름 검증
- 명령어 검증 (whitelist, which)
- URL 검증
- 크로스 필드 검증

---

### `backup.py` - Backup Manager

**Responsibility**: 설정 백업/복원

**Public API**:
```python
from pathlib import Path
from datetime import datetime
from typing import Optional

class BackupManager:
    """Manage configuration backups"""

    def __init__(self, backup_dir: Optional[Path] = None):
        self.backup_dir = backup_dir or self._default_backup_dir()
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        config: Config,
        name: Optional[str] = None,
        reason: Optional[str] = None
    ) -> Backup:
        """Create a new backup"""
        ...

    def list(self, limit: int = 10) -> list[Backup]:
        """List available backups"""
        ...

    def restore(self, backup_id: str) -> Config:
        """Restore configuration from backup"""
        ...

    def cleanup(
        self,
        keep: int = 5,
        older_than: Optional[str] = None
    ) -> int:
        """Remove old backups"""
        ...

    def _default_backup_dir(self) -> Path:
        return Path.home() / ".mcp-manager" / "backups"

    def _get_backup_path(self, backup_id: str) -> Path:
        return self.backup_dir / f"{backup_id}.json"
```

**Dependencies**:
- `models.Config`, `models.Backup`: 데이터 모델
- `file_handler.atomic_write`: 파일 쓰기

**Key Responsibilities**:
- 백업 생성 (타임스탬프 + metadata)
- 백업 목록 조회
- 백업 복원
- 오래된 백업 정리

---

### `file_handler.py` - File I/O

**Responsibility**: 안전한 파일 읽기/쓰기

**Public API**:
```python
from pathlib import Path
import fcntl
import tempfile
import os

def atomic_write(path: Path, content: str) -> None:
    """Write file atomically"""
    temp_path = path.with_suffix('.tmp')

    try:
        # Write to temp file
        temp_path.write_text(content)

        # Ensure written to disk
        with open(temp_path, 'r+') as f:
            os.fsync(f.fileno())

        # Atomic rename
        temp_path.rename(path)

    except Exception as e:
        # Cleanup on error
        if temp_path.exists():
            temp_path.unlink()
        raise FileIOError(f"Failed to write {path}: {e}")

def file_lock(path: Path, exclusive: bool = True):
    """Context manager for file locking"""
    class FileLock:
        def __init__(self, path, exclusive):
            self.path = path
            self.mode = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
            self.fd = None

        def __enter__(self):
            self.fd = open(self.path, 'r+' if exclusive else 'r')
            fcntl.flock(self.fd, self.mode)
            return self.fd

        def __exit__(self, *args):
            if self.fd:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
                self.fd.close()

    return FileLock(path, exclusive)
```

**Dependencies**:
- `exceptions.FileIOError`: 예외

**Key Responsibilities**:
- Atomic file write (temp → rename)
- File locking (fcntl)
- fsync for durability

---

### `templates.py` - Template System

**Responsibility**: MCP 서버 템플릿 관리

**Public API**:
```python
from pathlib import Path
from typing import Optional

class TemplateManager:
    """Manage MCP server templates"""

    def __init__(self, template_dir: Optional[Path] = None):
        self.template_dir = template_dir or self._default_template_dir()

    def list_templates(self) -> dict[str, dict]:
        """List available templates"""
        ...

    def get_template(self, name: str) -> MCPServer:
        """Get template by name"""
        ...

    def install_template(
        self,
        template_name: str,
        server_name: Optional[str] = None,
        scope: Scope = Scope.USER
    ) -> MCPServer:
        """Install template as server"""
        ...

    def _default_template_dir(self) -> Path:
        return Path(__file__).parent.parent / "templates"
```

**Dependencies**:
- `models.MCPServer`: 데이터 모델
- `config.ConfigManager`: 설정 저장

---

### `health.py` - Health Checks

**Responsibility**: 서버 상태 확인

**Public API**:
```python
import subprocess
from typing import Optional

class HealthChecker:
    """Check MCP server health"""

    def check(
        self,
        server: MCPServer,
        timeout: int = 10
    ) -> HealthStatus:
        """Check server health"""
        ...

    def check_stdio_server(self, server: MCPServer) -> HealthStatus:
        """Check stdio server (command exists)"""
        if not shutil.which(server.command):
            return HealthStatus.UNHEALTHY

        try:
            subprocess.run(
                [server.command, "--version"],
                timeout=timeout,
                capture_output=True
            )
            return HealthStatus.HEALTHY
        except:
            return HealthStatus.UNHEALTHY

    def check_http_server(self, server: MCPServer) -> HealthStatus:
        """Check HTTP server (connection test)"""
        ...

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
```

---

### `utils.py` - Utilities

**Responsibility**: 재사용 가능한 유틸리티 함수

**Public API**:
```python
from pathlib import Path
from typing import Any

def get_config_path(scope: Scope) -> Path:
    """Get config file path for scope"""
    if scope == Scope.USER:
        return Path.home() / ".claude.json"
    elif scope == Scope.PROJECT:
        return Path.cwd() / ".mcp.json"
    else:  # LOCAL
        return Path.cwd() / ".claude" / "settings.json"

def expand_env_vars(text: str) -> str:
    """Expand ${VAR} and ${VAR:-default}"""
    import os
    import re

    def replace(match):
        var_expr = match.group(1)
        if ":-" in var_expr:
            var, default = var_expr.split(":-", 1)
            return os.getenv(var, default)
        else:
            return os.getenv(var_expr, match.group(0))

    return re.sub(r'\$\{([^}]+)\}', replace, text)

def format_server_info(server: MCPServer) -> str:
    """Format server for display"""
    ...
```

---

### `constants.py` - Constants

**Responsibility**: 전역 상수 정의

**Public API**:
```python
from pathlib import Path

# Config paths
DEFAULT_CONFIG_PATH = Path.home() / ".claude.json"
PROJECT_CONFIG_PATH = Path.cwd() / ".mcp.json"
LOCAL_CONFIG_PATH = Path.cwd() / ".claude" / "settings.json"

# Backup
DEFAULT_BACKUP_DIR = Path.home() / ".mcp-manager" / "backups"
DEFAULT_BACKUP_KEEP = 5

# Validation
ALLOWED_COMMANDS = {"uvx", "npx", "node", "python", "python3", "docker"}
DANGEROUS_ENV_VARS = {"PATH", "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH"}
SERVER_NAME_PATTERN = r'^[a-z][a-z0-9_-]{0,63}$'

# Timeouts
DEFAULT_HEALTH_TIMEOUT = 10
DEFAULT_LOCK_TIMEOUT = 5
```

---

### `exceptions.py` - Custom Exceptions

**Responsibility**: 애플리케이션 예외 정의

**Public API**:
```python
class MCPManagerError(Exception):
    """Base exception for MCP Manager"""
    pass

class ConfigError(MCPManagerError):
    """Configuration error"""
    pass

class ConfigNotFoundError(ConfigError):
    """Configuration file not found"""
    pass

class ConfigCorruptedError(ConfigError):
    """Configuration file corrupted"""
    pass

class ConfigPermissionError(ConfigError):
    """Permission denied for config file"""
    pass

class ValidationError(MCPManagerError):
    """Validation error"""
    pass

class InvalidServerNameError(ValidationError):
    """Invalid server name format"""
    pass

class InvalidCommandError(ValidationError):
    """Invalid or disallowed command"""
    pass

class ServerAlreadyExistsError(ValidationError):
    """Server name already exists"""
    pass

class BackupError(MCPManagerError):
    """Backup operation error"""
    pass

class FileIOError(MCPManagerError):
    """File I/O error"""
    pass
```

---

## Dependency Map

```
cli.py
  ├─→ config.ConfigManager
  ├─→ validators.*
  ├─→ backup.BackupManager
  ├─→ templates.TemplateManager
  ├─→ health.HealthChecker
  └─→ models.*

config.py
  ├─→ models.Config, MCPServer
  ├─→ file_handler.atomic_write, file_lock
  ├─→ utils.get_config_path
  └─→ exceptions.ConfigError

backup.py
  ├─→ models.Config, Backup
  ├─→ file_handler.atomic_write
  └─→ exceptions.BackupError

validators.py
  ├─→ models.MCPServer, MCPServerType
  ├─→ constants.ALLOWED_COMMANDS
  └─→ exceptions.ValidationError

file_handler.py
  └─→ exceptions.FileIOError

templates.py
  ├─→ models.MCPServer
  └─→ config.ConfigManager

health.py
  ├─→ models.MCPServer
  └─→ exceptions.HealthCheckError

utils.py
  ├─→ models.*
  └─→ constants.*

models.py
  └─→ (no internal dependencies)

constants.py
  └─→ (no dependencies)

exceptions.py
  └─→ (no dependencies)
```

---

## Module Interaction Examples

### Add Server Flow

```python
# cli.py
@app.command()
def add(name: str, type: MCPServerType, command: str):
    # 1. Validate input
    validate_server_name(name)  # validators.py
    validate_command(command)   # validators.py

    # 2. Create server model
    server = MCPServer(          # models.py
        type=type,
        command=command
    )
    validate_server(server)      # validators.py

    # 3. Add to config
    config_manager = ConfigManager()  # config.py
    config_manager.add_server(name, server)

    # 4. Save
    config_manager.save()        # → file_handler.atomic_write

    console.print(f"✓ Server '{name}' added!")
```

### Backup & Restore Flow

```python
# cli.py
@app.command()
def backup_create():
    # 1. Load current config
    config_manager = ConfigManager()
    config = config_manager.load()

    # 2. Create backup
    backup_manager = BackupManager()
    backup = backup_manager.create(config)

    console.print(f"✓ Backup created: {backup.backup_id}")

@app.command()
def backup_restore(backup_id: str):
    # 1. Load backup
    backup_manager = BackupManager()
    config = backup_manager.restore(backup_id)

    # 2. Save as current config
    config_manager = ConfigManager()
    config_manager.save(config)

    console.print("✓ Configuration restored!")
```

---

## Testing Strategy per Module

### Unit Tests

각 모듈은 독립적으로 테스트합니다.

```python
# tests/unit/test_validators.py
def test_validate_server_name():
    assert validate_server_name("my-server")
    with pytest.raises(InvalidServerNameError):
        validate_server_name("MyServer")

# tests/unit/test_config.py
def test_add_server(tmp_path):
    config_path = tmp_path / "config.json"
    manager = ConfigManager(config_path)
    server = MCPServer(type=MCPServerType.STDIO, command="uvx")
    manager.add_server("test", server)
    assert "test" in manager.load().mcpServers
```

### Integration Tests

모듈 간 상호작용을 테스트합니다.

```python
# tests/integration/test_add_remove_flow.py
def test_full_add_remove_cycle(tmp_path):
    config_path = tmp_path / "config.json"
    manager = ConfigManager(config_path)

    # Add
    server = MCPServer(type=MCPServerType.STDIO, command="uvx")
    manager.add_server("test", server)

    # Verify
    assert manager.get_server("test") is not None

    # Remove
    manager.remove_server("test")
    assert manager.get_server("test") is None
```

---

## Summary

MCP Manager의 모듈 설계는:
- **명확한 책임**: 각 모듈은 단일 책임
- **잘 정의된 인터페이스**: Public API 명확
- **느슨한 결합**: 의존성 최소화
- **높은 응집도**: 관련 기능 그룹화
- **테스트 가능**: 각 모듈 독립 테스트

이 설계를 통해 유지보수하기 쉽고 확장 가능한 구조를 제공합니다.
