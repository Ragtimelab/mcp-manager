# Security Strategy

## Overview

MCP Manager는 사용자의 시스템과 데이터를 보호하기 위해 다층 보안 전략을 적용합니다. 입력 검증, 안전한 실행, 데이터 무결성을 통해 보안 위협을 완화합니다.

## Input Validation Levels

### Level 1: Type Safety (Pydantic)

Pydantic 모델이 자동으로 타입을 검증합니다.

```python
class MCPServer(BaseModel):
    type: MCPServerType  # Enum만 허용
    command: Optional[str] = None  # str 또는 None
    args: list[str] = []  # 반드시 문자열 리스트
    env: dict[str, str] = {}  # str → str 매핑만

# Type safety
server = MCPServer(
    type="invalid"  # ✗ ValidationError: not a valid MCPServerType
)

server = MCPServer(
    type=MCPServerType.STDIO,
    args=["valid", 123]  # ✗ ValidationError: args must be list[str]
)
```

---

### Level 2: Business Rules (Validators)

비즈니스 로직 검증을 수행합니다.

```python
# validators.py

def validate_server_name(name: str) -> bool:
    """
    Server name security rules:
    - Lowercase only (prevents case confusion)
    - Alphanumeric + hyphen/underscore only
    - Must start with letter (prevents numeric-only names)
    - Max 64 characters (prevents resource exhaustion)
    """
    pattern = r'^[a-z][a-z0-9_-]{0,63}$'

    if not re.match(pattern, name):
        raise InvalidServerNameError(name)

    # Additional security: reserved names
    RESERVED_NAMES = {"system", "root", "admin", "config"}
    if name in RESERVED_NAMES:
        raise ValidationError(f"'{name}' is a reserved name")

    return True
```

---

### Level 3: Security Validation

보안 위협을 차단합니다.

```python
def validate_command(command: str) -> bool:
    """
    Command security rules:
    - Whitelist approach for known-safe commands
    - Absolute path validation
    - No shell meta-characters in whitelist commands
    """
    # Whitelist: known-safe package managers
    ALLOWED_COMMANDS = {"uvx", "npx", "node", "python", "python3", "docker"}

    if command in ALLOWED_COMMANDS:
        return True

    # Allow absolute paths (but validate)
    if command.startswith('/'):
        validate_absolute_path(command)
        return True

    # Fallback: check if executable exists
    if not shutil.which(command):
        raise InvalidCommandError(
            f"Command '{command}' not found. "
            f"Allowed: {', '.join(ALLOWED_COMMANDS)}"
        )

    # Warn about non-whitelisted commands
    logger.warning(f"Non-whitelisted command: {command}")
    return True

def validate_absolute_path(path: str) -> bool:
    """Validate absolute executable paths"""
    # No path traversal
    if '..' in path:
        raise SecurityError("Path traversal detected: '..' not allowed")

    # Must be absolute
    if not path.startswith('/'):
        raise SecurityError("Only absolute paths allowed")

    # File must exist and be executable
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Executable not found: {path}")

    if not os.access(path, os.X_OK):
        raise SecurityError(f"File not executable: {path}")

    return True
```

---

## Threat Model & Mitigation

### 1. Arbitrary Command Execution

**Threat**: 악의적인 명령어 실행

```json
{
  "command": "rm -rf /",
  "args": []
}
```

**Mitigation**:
```python
# 1. Whitelist approach
ALLOWED_COMMANDS = {"uvx", "npx", "node", "python", "python3", "docker"}

# 2. No shell execution
# ✗ Bad: shell=True (allows shell injection)
subprocess.run(f"{command} {args}", shell=True)

# ✓ Good: No shell, args as list
subprocess.run([command] + args, shell=False)

# 3. Validation
def validate_command(command: str) -> bool:
    if command not in ALLOWED_COMMANDS:
        if not shutil.which(command):
            raise InvalidCommandError(command)
    return True
```

---

### 2. Path Traversal

**Threat**: 경로 탐색을 통한 시스템 파일 접근

```json
{
  "command": "../../etc/passwd"
}
```

**Mitigation**:
```python
def validate_path(path: str) -> bool:
    """Prevent path traversal attacks"""
    # Reject relative paths
    if '..' in path:
        raise SecurityError("Path traversal detected")

    # Only allow absolute paths
    if not path.startswith('/'):
        raise SecurityError("Only absolute paths allowed")

    # Canonicalize and check
    resolved = Path(path).resolve()
    if not str(resolved).startswith('/'):
        raise SecurityError("Path escapes root")

    return True
```

---

### 3. Environment Variable Pollution

**Threat**: 위험한 환경변수 조작

```json
{
  "env": {
    "PATH": "/tmp/malicious/bin:/usr/bin",
    "LD_PRELOAD": "/tmp/evil.so"
  }
}
```

**Mitigation**:
```python
DANGEROUS_ENV_VARS = {
    "PATH",           # 실행 경로 변경
    "LD_PRELOAD",     # 라이브러리 주입
    "LD_LIBRARY_PATH",  # 라이브러리 경로
    "DYLD_INSERT_LIBRARIES",  # macOS 라이브러리 주입
    "PYTHONPATH",     # Python 모듈 경로
    "NODE_PATH"       # Node 모듈 경로
}

def validate_env_vars(env: dict[str, str]) -> bool:
    """Check for dangerous environment variables"""
    for key in env.keys():
        if key in DANGEROUS_ENV_VARS:
            logger.warning(f"Dangerous env var: {key}")

            # Ask user for confirmation
            console.print(f"[yellow]⚠ Warning:[/] Setting '{key}' can be dangerous")
            if not typer.confirm("Continue?"):
                raise SecurityError(f"User rejected dangerous env var: {key}")

        # Check for command injection in values
        if any(char in env[key] for char in [';', '&', '|', '`', '$']):
            raise SecurityError(f"Shell metacharacter in env value: {key}={env[key]}")

    return True
```

---

### 4. Configuration File Corruption

**Threat**: 동시 쓰기로 인한 JSON 손상

**Scenario**:
```
Process A: Read config → Modify → Write
Process B: Read config → Modify → Write
Result: Lost updates or corrupted JSON
```

**Mitigation**:
```python
import fcntl

def atomic_write_with_lock(path: Path, content: str) -> None:
    """
    Atomic write with file locking
    1. Acquire exclusive lock
    2. Write to temp file
    3. fsync for durability
    4. Atomic rename
    5. Release lock
    """
    lock_path = path.with_suffix('.lock')

    try:
        # Acquire exclusive lock
        with open(lock_path, 'w') as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)

            # Write to temp file
            temp_path = path.with_suffix('.tmp')
            temp_path.write_text(content)

            # Ensure written to disk
            with open(temp_path, 'r+') as f:
                os.fsync(f.fileno())

            # Atomic rename
            temp_path.rename(path)

            # Lock automatically released on close
    finally:
        # Cleanup lock file
        if lock_path.exists():
            lock_path.unlink()
```

---

### 5. Sensitive Data Exposure

**Threat**: 평문 토큰/비밀번호 저장

```json
{
  "headers": {
    "Authorization": "Bearer sk-secret-token-12345"
  }
}
```

**Mitigation**:
```python
# 1. Warn about hardcoded secrets
def validate_headers(headers: dict[str, str]) -> bool:
    for key, value in headers.items():
        # Detect potential secrets
        if any(pattern in value.lower() for pattern in ['token', 'key', 'secret', 'password']):
            if not value.startswith('${'):  # Not using env var
                console.print(f"[yellow]⚠ Warning:[/] Hardcoded secret detected in '{key}'")
                console.print("Consider using environment variable:")
                console.print(f"  {key}: ${{MY_TOKEN}}")

                if not typer.confirm("Continue with hardcoded value?"):
                    raise SecurityError("User rejected hardcoded secret")
    return True

# 2. Support ${VAR} expansion
def expand_env_vars(text: str) -> str:
    """
    Expand environment variables in format:
    - ${VAR}
    - ${VAR:-default}
    """
    import os
    import re

    def replace(match):
        var_expr = match.group(1)
        if ":-" in var_expr:
            var, default = var_expr.split(":-", 1)
            return os.getenv(var, default)
        else:
            value = os.getenv(var_expr)
            if value is None:
                raise SecurityError(f"Environment variable not set: {var_expr}")
            return value

    return re.sub(r'\$\{([^}]+)\}', replace, text)

# Usage
headers = {
    "Authorization": "Bearer ${API_TOKEN}"
}
expanded_headers = {
    k: expand_env_vars(v) for k, v in headers.items()
}
```

---

### 6. JSON Injection

**Threat**: 사용자 입력이 JSON 구조를 깨뜨림

```python
# ✗ Bad: String concatenation
config_str = f'{{"name": "{user_input}"}}'

# ✓ Good: Pydantic + json.dumps
server = MCPServer(name=user_input, ...)
config_str = json.dumps(config.model_dump())
```

---

## Safe Execution Practices

### 1. No Shell Execution

```python
# ✗ Vulnerable to shell injection
os.system(f"{command} {args}")
subprocess.run(f"{command} {args}", shell=True)

# ✓ Safe: No shell, args as list
subprocess.run([command] + args, shell=False)
```

---

### 2. Input Sanitization

```python
def sanitize_server_name(name: str) -> str:
    """Remove dangerous characters"""
    # Only allow safe characters
    return re.sub(r'[^a-z0-9_-]', '', name.lower())

def sanitize_path(path: str) -> str:
    """Canonicalize path"""
    return str(Path(path).resolve())
```

---

### 3. Principle of Least Privilege

```python
# Config file permissions: 644 (rw-r--r--)
def ensure_safe_permissions(path: Path):
    """Set safe file permissions"""
    import stat
    path.chmod(
        stat.S_IRUSR | stat.S_IWUSR |  # User: read, write
        stat.S_IRGRP |                  # Group: read
        stat.S_IROTH                    # Other: read
    )

# Backup directory: 700 (rwx------)
def ensure_private_dir(path: Path):
    """Ensure directory is private"""
    import stat
    path.chmod(
        stat.S_IRWXU  # User: read, write, execute
    )
```

---

## Secure Defaults

### 1. Restrictive by Default

```python
# Default: user scope (most restrictive)
DEFAULT_SCOPE = Scope.USER

# Default: no env vars
DEFAULT_ENV = {}

# Default: require confirmation
DEFAULT_CONFIRM = True
```

---

### 2. Explicit Security Opts

```python
# User must explicitly allow dangerous operations
@app.command()
def add(
    name: str,
    command: str,
    force_allow_command: bool = False  # Explicit flag
):
    if command not in ALLOWED_COMMANDS and not force_allow_command:
        raise SecurityError(
            f"Command '{command}' not in whitelist. "
            "Use --force-allow-command to override"
        )
```

---

## Rollback & Recovery

### 1. Automatic Backup

```python
def safe_modify(operation: Callable):
    """Decorator for safe modifications"""
    def wrapper(*args, **kwargs):
        # Create backup
        backup_manager = BackupManager()
        config = config_manager.load()
        backup = backup_manager.create(config, reason=f"before_{operation.__name__}")

        try:
            # Perform operation
            result = operation(*args, **kwargs)
            return result

        except Exception as e:
            # Rollback on error
            console.print(f"[red]✗ Operation failed:[/] {e}")
            console.print(f"[yellow]Rolling back to backup {backup.backup_id}[/]")

            restored_config = backup_manager.restore(backup.backup_id)
            config_manager.save(restored_config)

            console.print("[green]✓[/] Configuration restored")
            raise

    return wrapper

# Usage
@safe_modify
def add_server(name: str, server: MCPServer):
    config_manager.add_server(name, server)
    config_manager.save()
```

---

### 2. Dry Run Mode

```python
@app.command()
def add(name: str, ..., dry_run: bool = False):
    """Add server with dry-run support"""
    if dry_run:
        console.print("[yellow]DRY RUN MODE - No changes will be made[/]")

    server = MCPServer(...)

    console.print("\nPreview:")
    console.print(f"  Name: {name}")
    console.print(f"  Type: {server.type}")
    console.print(f"  Command: {server.command}")

    if dry_run:
        console.print("\n[yellow]Would add server (dry run)[/]")
        return

    # Actual operation
    config_manager.add_server(name, server)
```

---

## Audit Trail

모든 보안 관련 이벤트를 기록합니다.

```python
class SecurityAudit:
    def __init__(self):
        self.audit_file = Path.home() / ".mcp-manager" / "security.log"

    def log_event(
        self,
        event_type: str,
        severity: str,
        details: dict
    ):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "severity": severity,
            "details": details,
            "user": os.getenv("USER"),
            "pid": os.getpid()
        }

        with self.audit_file.open('a') as f:
            f.write(json.dumps(entry) + '\n')

# Usage
audit = SecurityAudit()

audit.log_event(
    "command_validation",
    "WARNING",
    {
        "command": command,
        "allowed": command in ALLOWED_COMMANDS,
        "action": "accepted" if allowed else "rejected"
    }
)

audit.log_event(
    "dangerous_env_var",
    "HIGH",
    {
        "variable": "PATH",
        "value": env["PATH"],
        "action": "confirmed_by_user"
    }
)
```

---

## Security Checklist

### Configuration

- [ ] Config file permissions: 644
- [ ] Backup directory permissions: 700
- [ ] No sensitive data in version control
- [ ] Environment variables for secrets

### Input Validation

- [ ] Type safety (Pydantic)
- [ ] Business rules (Validators)
- [ ] Security checks (Sanitization)
- [ ] Whitelist approach for commands

### Execution

- [ ] No shell=True
- [ ] Args as list (not string)
- [ ] Environment variable filtering
- [ ] Path traversal prevention

### Data Protection

- [ ] Atomic writes
- [ ] File locking
- [ ] Automatic backups
- [ ] Rollback on error

### Monitoring

- [ ] Audit logging
- [ ] Security event tracking
- [ ] Permission validation
- [ ] Anomaly detection

---

## Summary

MCP Manager의 보안 전략은:
- **다층 검증**: Type → Business → Security
- **위협 완화**: 각 위협에 대한 구체적 대응
- **안전한 실행**: No shell, 환경변수 필터링
- **데이터 보호**: Atomic write, locking, backup
- **감사 추적**: 모든 보안 이벤트 기록

이 설계를 통해 사용자의 시스템과 데이터를 안전하게 보호합니다.
