# Error Handling Strategy

## Overview

MCP Manager는 체계적인 에러 처리를 통해 안정적인 사용자 경험을 제공합니다. 각 레이어는 자신의 예외를 정의하고, 상위 레이어는 하위 레이어의 예외를 적절히 처리합니다.

## Exception Hierarchy

```python
MCPManagerError (base)
├── ConfigError
│   ├── ConfigNotFoundError
│   ├── ConfigCorruptedError
│   └── ConfigPermissionError
├── ValidationError
│   ├── InvalidServerNameError
│   ├── InvalidServerTypeError
│   ├── InvalidCommandError
│   ├── InvalidURLError
│   └── ServerAlreadyExistsError
├── BackupError
│   ├── BackupNotFoundError
│   ├── BackupCorruptedError
│   └── BackupRestoreError
├── FileIOError
│   ├── FileReadError
│   ├── FileWriteError
│   └── FileLockError
└── HealthCheckError
    ├── ServerUnreachableError
    └── ServerTimeoutError
```

---

## Exception Definitions

### Base Exception

```python
class MCPManagerError(Exception):
    """Base exception for all MCP Manager errors"""

    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def __str__(self) -> str:
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message
```

### Config Errors

```python
class ConfigError(MCPManagerError):
    """Configuration-related errors"""
    pass

class ConfigNotFoundError(ConfigError):
    """Configuration file not found"""

    def __init__(self, path: Path):
        super().__init__(
            f"Configuration file not found: {path}",
            details={"path": str(path)}
        )

class ConfigCorruptedError(ConfigError):
    """Configuration file is corrupted or invalid JSON"""

    def __init__(self, path: Path, reason: str):
        super().__init__(
            f"Configuration file corrupted: {reason}",
            details={"path": str(path), "reason": reason}
        )

class ConfigPermissionError(ConfigError):
    """Insufficient permissions to read/write config"""

    def __init__(self, path: Path, operation: str):
        super().__init__(
            f"Permission denied: cannot {operation} {path}",
            details={"path": str(path), "operation": operation}
        )
```

### Validation Errors

```python
class ValidationError(MCPManagerError):
    """Input validation errors"""
    pass

class InvalidServerNameError(ValidationError):
    """Server name doesn't match pattern"""

    def __init__(self, name: str):
        super().__init__(
            f"Invalid server name: '{name}'",
            details={
                "name": name,
                "pattern": r"^[a-z][a-z0-9_-]{{0,63}}$"
            }
        )

class InvalidCommandError(ValidationError):
    """Command not found or not allowed"""

    def __init__(self, command: str, allowed: set[str]):
        super().__init__(
            f"Invalid command: '{command}'",
            details={
                "command": command,
                "allowed": list(allowed)
            }
        )

class ServerAlreadyExistsError(ValidationError):
    """Server with this name already exists"""

    def __init__(self, name: str, scope: Scope):
        super().__init__(
            f"Server '{name}' already exists in {scope} scope",
            details={"name": name, "scope": scope.value}
        )
```

---

## Error Recovery Strategies

### 1. ConfigCorruptedError

**Scenario**: JSON 파싱 실패 또는 스키마 불일치

**Recovery**:
```python
try:
    config = config_manager.load()
except ConfigCorruptedError as e:
    console.print(f"[red]✗ Config corrupted:[/] {e.message}")

    # Check for backup
    backup_manager = BackupManager()
    backups = backup_manager.list(limit=1)

    if backups:
        backup = backups[0]
        console.print(f"\n[yellow]Backup found:[/] {backup.backup_id}")
        console.print(f"  Created: {backup.timestamp}")

        if typer.confirm("Restore from backup?"):
            try:
                config = backup_manager.restore(backup.backup_id)
                config_manager.save(config)
                console.print("[green]✓[/] Configuration restored!")
            except BackupRestoreError:
                console.print("[red]✗[/] Backup restore failed")
                console.print("\n[yellow]Manual fix required:[/]")
                console.print(f"  1. Edit {config_manager.config_path}")
                console.print("  2. Fix JSON syntax")
                console.print("  3. Run 'mcpm validate --fix'")
                sys.exit(1)
    else:
        console.print("\n[yellow]No backups found[/]")
        console.print("Manual fix required:")
        console.print(f"  nano {config_manager.config_path}")
        sys.exit(1)
```

---

### 2. ConfigPermissionError

**Scenario**: 파일 읽기/쓰기 권한 없음

**Recovery**:
```python
try:
    config_manager.save(config)
except ConfigPermissionError as e:
    console.print(f"[red]✗ Permission denied:[/] {e.message}")
    console.print("\n[yellow]Fix:[/]")
    console.print(f"  chmod 644 {e.details['path']}")

    if typer.confirm("Apply fix automatically?"):
        import os
        import stat
        os.chmod(e.details['path'], stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
        console.print("[green]✓[/] Permissions fixed!")
        # Retry
        config_manager.save(config)
    else:
        sys.exit(3)
```

---

### 3. InvalidCommandError

**Scenario**: 명령어를 찾을 수 없거나 허용되지 않음

**Recovery**:
```python
try:
    validate_command(command)
except InvalidCommandError as e:
    console.print(f"[red]✗ Invalid command:[/] {e.message}")
    console.print("\n[yellow]Allowed commands:[/]")
    for cmd in e.details['allowed']:
        console.print(f"  - {cmd}")

    console.print("\n[yellow]Or use absolute path:[/]")
    console.print("  /usr/local/bin/my-command")

    # Suggest alternatives
    import difflib
    suggestions = difflib.get_close_matches(
        command,
        e.details['allowed'],
        n=3,
        cutoff=0.6
    )
    if suggestions:
        console.print("\n[yellow]Did you mean?[/]")
        for suggestion in suggestions:
            console.print(f"  - {suggestion}")

    sys.exit(2)
```

---

### 4. BackupNotFoundError

**Scenario**: 백업을 찾을 수 없음

**Recovery**:
```python
try:
    config = backup_manager.restore(backup_id)
except BackupNotFoundError as e:
    console.print(f"[red]✗ Backup not found:[/] {e.message}")

    # Show available backups
    console.print("\n[yellow]Available backups:[/]")
    backups = backup_manager.list()

    if not backups:
        console.print("  (none)")
        sys.exit(4)

    for backup in backups:
        console.print(f"  - {backup.backup_id} ({backup.timestamp})")

    console.print("\nUsage:")
    console.print("  mcpm backup restore <backup-id>")
    sys.exit(4)
```

---

## Layer-specific Error Handling

### Presentation Layer (CLI)

**Responsibility**: 사용자 친화적 메시지 + 해결 방법 제시

```python
# cli.py
@app.command()
def add(name: str, ...):
    try:
        # Business logic
        validate_server_name(name)
        server = MCPServer(...)
        config_manager.add_server(name, server)
        config_manager.save()

        console.print(f"[green]✓[/] Server '{name}' added!")

    except InvalidServerNameError as e:
        console.print(f"[red]✗ Invalid name:[/] {e.message}")
        console.print("\n[yellow]Server name must:[/]")
        console.print("  - Start with lowercase letter")
        console.print("  - Contain only: a-z, 0-9, -, _")
        console.print("  - Be 1-64 characters long")
        console.print("\n[yellow]Examples:[/]")
        console.print("  ✓ my-server, db_client, api2")
        console.print("  ✗ MyServer, 123abc, my server")
        sys.exit(2)

    except ServerAlreadyExistsError as e:
        console.print(f"[red]✗ Server exists:[/] {e.message}")
        console.print("\n[yellow]Options:[/]")
        console.print(f"  1. Use different name")
        console.print(f"  2. Remove existing: mcpm remove {name}")
        console.print(f"  3. Edit existing: mcpm edit {name}")
        sys.exit(5)

    except ConfigPermissionError as e:
        # (Recovery strategy as shown above)
        sys.exit(3)

    except Exception as e:
        # Unexpected error
        console.print(f"[red]✗ Unexpected error:[/] {e}")
        console.print("\n[yellow]Please report this issue:[/]")
        console.print("  https://github.com/yourusername/mcp-manager/issues")
        if verbose:
            import traceback
            console.print("\n[dim]" + traceback.format_exc() + "[/dim]")
        sys.exit(1)
```

---

### Business Layer

**Responsibility**: 비즈니스 예외 발생

```python
# config.py
class ConfigManager:
    def add_server(self, name: str, server: MCPServer):
        config = self.load()

        # Check if exists
        if name in config.mcpServers:
            raise ServerAlreadyExistsError(name, Scope.USER)

        # Add server
        config.mcpServers[name] = server

        # Save (may raise ConfigPermissionError)
        self.save(config)

# validators.py
def validate_server_name(name: str) -> bool:
    pattern = r'^[a-z][a-z0-9_-]{0,63}$'
    if not re.match(pattern, name):
        raise InvalidServerNameError(name)
    return True
```

---

### Data Layer

**Responsibility**: I/O 예외 → 비즈니스 예외 변환

```python
# config.py
class ConfigManager:
    def load(self) -> Config:
        try:
            data = self.config_path.read_text()
        except FileNotFoundError:
            raise ConfigNotFoundError(self.config_path)
        except PermissionError:
            raise ConfigPermissionError(self.config_path, "read")

        try:
            json_data = json.loads(data)
        except json.JSONDecodeError as e:
            raise ConfigCorruptedError(self.config_path, str(e))

        try:
            return Config.model_validate(json_data)
        except ValidationError as e:
            raise ConfigCorruptedError(self.config_path, f"Schema error: {e}")
```

---

## Logging Strategy

### User-facing Logs (Rich Console)

```python
from rich.console import Console

console = Console()

# Success
console.print("[green]✓[/] Server added successfully!")

# Warning
console.print("[yellow]⚠[/] Server using deprecated SSE transport")

# Error
console.print("[red]✗[/] Failed to connect to server")

# Info
console.print("[blue]ℹ[/] Creating backup before changes...")

# Progress
from rich.progress import track
for server in track(servers, description="Checking health..."):
    check_health(server)
```

---

### Debug Logs (File)

```python
import logging
from pathlib import Path

def setup_logging(verbose: bool = False):
    log_dir = Path.home() / ".mcp-manager" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"{datetime.now():%Y-%m-%d}.log"

    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler() if verbose else logging.NullHandler()
        ]
    )

# Usage
logger = logging.getLogger(__name__)
logger.debug(f"Loading config from {path}")
logger.info(f"Added server: {name}")
logger.error(f"Failed to write config: {e}")
```

---

### Audit Logs

모든 설정 변경 사항을 기록합니다.

```python
class AuditLogger:
    def __init__(self):
        self.audit_file = Path.home() / ".mcp-manager" / "audit.log"

    def log_change(
        self,
        action: str,
        details: dict,
        before: Optional[dict] = None,
        after: Optional[dict] = None
    ):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details,
            "before": before,
            "after": after
        }

        with self.audit_file.open('a') as f:
            f.write(json.dumps(entry) + '\n')

# Usage
audit = AuditLogger()
audit.log_change(
    action="add_server",
    details={"name": "time", "type": "stdio"},
    after={"command": "uvx", "args": ["mcp-server-time"]}
)
```

---

## Error Context Propagation

예외에 컨텍스트 정보를 포함합니다.

```python
class ConfigError(MCPManagerError):
    def __init__(
        self,
        message: str,
        details: Optional[dict] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message, details)
        self.__cause__ = cause

# Usage
try:
    data = json.loads(content)
except json.JSONDecodeError as e:
    raise ConfigCorruptedError(
        path,
        f"Invalid JSON: {e}",
        cause=e
    )
```

---

## Retry Logic

일시적 오류에 대한 재시도 로직.

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
def save_with_retry(config_manager: ConfigManager, config: Config):
    """Save with retry on transient errors"""
    try:
        config_manager.save(config)
    except FileLockError:
        # Retry on lock timeout
        raise
    except ConfigPermissionError:
        # Don't retry on permission errors
        raise
```

---

## Error Reporting

사용자가 문제를 보고할 수 있도록 정보 제공.

```python
def format_error_report(e: Exception) -> str:
    """Format error for bug report"""
    import platform
    import sys

    return f"""
MCP Manager Error Report
========================

Error Type: {type(e).__name__}
Message: {str(e)}

System Information:
- OS: {platform.system()} {platform.release()}
- Python: {sys.version}
- MCP Manager: {__version__}

Stack Trace:
{traceback.format_exc()}

Config Path: {config_manager.config_path}
Config Exists: {config_manager.config_path.exists()}

Please report this issue:
https://github.com/yourusername/mcp-manager/issues/new
""".strip()

# Usage in CLI
except Exception as e:
    if verbose:
        console.print(format_error_report(e))
    else:
        console.print(f"[red]✗[/] {e}")
        console.print("Run with --verbose for details")
```

---

## Exit Codes

표준화된 종료 코드:

```python
class ExitCode(IntEnum):
    SUCCESS = 0
    GENERAL_ERROR = 1
    VALIDATION_ERROR = 2
    PERMISSION_ERROR = 3
    NOT_FOUND = 4
    ALREADY_EXISTS = 5

# Usage
sys.exit(ExitCode.VALIDATION_ERROR)
```

---

## Summary

MCP Manager의 에러 처리는:
- **계층적 예외**: 명확한 예외 계층 구조
- **복구 전략**: 각 에러에 대한 복구 방법 제공
- **사용자 친화적**: 명확한 에러 메시지 + 해결 방법
- **디버깅 지원**: 상세 로깅 + 에러 보고
- **안정성**: 재시도, 백업, 검증

이 설계를 통해 안정적이고 신뢰할 수 있는 사용자 경험을 제공합니다.
