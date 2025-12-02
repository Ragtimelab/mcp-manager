# MCP Manager - Implementation Tasks

## Phase 1: Core Infrastructure (Foundation)

### 1.1 Project Setup
- [ ] Create `src/mcp_manager/__init__.py`
- [ ] Add `__version__ = "0.1.0"`
- [ ] Create `src/mcp_manager/py.typed` (for type checking)

### 1.2 Constants Module (`constants.py`)
- [ ] Define `DEFAULT_CONFIG_PATH = Path.home() / ".claude.json"`
- [ ] Define `PROJECT_CONFIG_PATH = Path.cwd() / ".mcp.json"`
- [ ] Define `LOCAL_CONFIG_PATH = Path.cwd() / ".claude" / "settings.json"`
- [ ] Define `DEFAULT_BACKUP_DIR = Path.home() / ".mcp-manager" / "backups"`
- [ ] Define `ALLOWED_COMMANDS = {"uvx", "npx", "node", "python", "python3", "docker"}`
- [ ] Define `DANGEROUS_ENV_VARS = {"PATH", "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH"}`
- [ ] Define `SERVER_NAME_PATTERN = r"^[a-z][a-z0-9_-]{0,63}$"`
- [ ] Define timeout constants (health check, file lock)

### 1.3 Exceptions Module (`exceptions.py`)
- [ ] Define `MCPManagerError(Exception)` base class
- [ ] Define `ConfigError(MCPManagerError)`
  - [ ] `ConfigNotFoundError`
  - [ ] `ConfigCorruptedError`
  - [ ] `ConfigPermissionError`
- [ ] Define `ValidationError(MCPManagerError)`
  - [ ] `InvalidServerNameError`
  - [ ] `InvalidServerTypeError`
  - [ ] `InvalidCommandError`
  - [ ] `InvalidURLError`
  - [ ] `ServerAlreadyExistsError`
- [ ] Define `BackupError(MCPManagerError)`
  - [ ] `BackupNotFoundError`
  - [ ] `BackupCorruptedError`
- [ ] Define `FileIOError(MCPManagerError)`
- [ ] Add `details: dict` field to all exceptions
- [ ] Add proper `__str__` method

---

## Phase 2: Data Layer

### 2.1 Data Models (`models.py`)
- [ ] Import Pydantic v2 (`from pydantic import BaseModel, Field`)
- [ ] Define `MCPServerType(str, Enum)`
  - [ ] `STDIO = "stdio"`
  - [ ] `SSE = "sse"`
  - [ ] `HTTP = "http"`
- [ ] Define `Scope(str, Enum)`
  - [ ] `USER = "user"`
  - [ ] `PROJECT = "project"`
  - [ ] `LOCAL = "local"`
- [ ] Define `MCPServer(BaseModel)`
  - [ ] Field: `type: MCPServerType`
  - [ ] Field: `command: Optional[str] = None`
  - [ ] Field: `args: list[str] = Field(default_factory=list)`
  - [ ] Field: `env: dict[str, str] = Field(default_factory=dict)`
  - [ ] Field: `url: Optional[str] = None`
  - [ ] Field: `headers: dict[str, str] = Field(default_factory=dict)`
  - [ ] Add field validator for `command` (stdio requires it)
  - [ ] Add field validator for `url` (http/sse requires it)
  - [ ] Add `model_config = ConfigDict(use_enum_values=True)`
- [ ] Define `Config(BaseModel)`
  - [ ] Field: `mcpServers: dict[str, MCPServer] = Field(default_factory=dict)`
  - [ ] Add `model_config = ConfigDict(extra="allow")` (preserve unknown fields)
- [ ] Define `Backup(BaseModel)`
  - [ ] Field: `timestamp: datetime = Field(default_factory=datetime.now)`
  - [ ] Field: `config: Config`
  - [ ] Field: `metadata: dict[str, str] = Field(default_factory=dict)`
  - [ ] Property: `backup_id` (returns formatted timestamp)

### 2.2 Validators Module (`validators.py`)
- [ ] Import constants and exceptions
- [ ] Function: `validate_server_name(name: str) -> bool`
  - [ ] Check pattern `^[a-z][a-z0-9_-]{0,63}$`
  - [ ] Reject reserved names ("system", "root", "admin")
  - [ ] Raise `InvalidServerNameError` on failure
- [ ] Function: `validate_command(command: str) -> bool`
  - [ ] Check if in `ALLOWED_COMMANDS` whitelist
  - [ ] If not, check with `shutil.which()`
  - [ ] Raise `InvalidCommandError` if not found
  - [ ] Log warning for non-whitelisted commands
- [ ] Function: `validate_url(url: str) -> bool`
  - [ ] Use Pydantic `HttpUrl` for validation
  - [ ] Raise `InvalidURLError` on failure
- [ ] Function: `validate_env_vars(env: dict[str, str]) -> bool`
  - [ ] Warn if setting dangerous vars
  - [ ] Check for shell metacharacters in values
  - [ ] Return True or raise `SecurityError`
- [ ] Function: `validate_server(server: MCPServer) -> bool`
  - [ ] Cross-field validation
  - [ ] Ensure stdio has command
  - [ ] Ensure http/sse has url
  - [ ] Call `validate_command` or `validate_url`

### 2.3 File Handler Module (`file_handler.py`)
- [ ] Import `fcntl`, `tempfile`, `os`
- [ ] Function: `atomic_write(path: Path, content: str) -> None`
  - [ ] Create temp file with `.tmp` suffix
  - [ ] Write content to temp file
  - [ ] Call `os.fsync()` for durability
  - [ ] Atomic rename: `temp.rename(path)`
  - [ ] Cleanup temp file on error
  - [ ] Raise `FileIOError` on failure
- [ ] Class: `FileLock` (context manager)
  - [ ] `__init__(self, path: Path, exclusive: bool = True)`
  - [ ] `__enter__`: Open file, acquire lock (`fcntl.flock`)
  - [ ] `__exit__`: Release lock, close file
- [ ] Function: `file_lock(path: Path, exclusive: bool = True) -> FileLock`

---

## Phase 3: Business Logic Layer

### 3.1 Config Manager (`config.py`)
- [ ] Import models, validators, file_handler, exceptions
- [ ] Class: `ConfigManager`
  - [ ] `__init__(self, config_path: Optional[Path] = None, scope: Scope = Scope.USER)`
  - [ ] Determine config path based on scope
  - [ ] Property: `config` (lazy loading with caching)
- [ ] Method: `load(self) -> Config`
  - [ ] Read file with proper error handling
  - [ ] Handle `FileNotFoundError` → `ConfigNotFoundError`
  - [ ] Handle `PermissionError` → `ConfigPermissionError`
  - [ ] Parse JSON with error handling
  - [ ] Handle `json.JSONDecodeError` → `ConfigCorruptedError`
  - [ ] Validate with Pydantic
  - [ ] Handle `ValidationError` → `ConfigCorruptedError`
- [ ] Method: `save(self, config: Config) -> None`
  - [ ] Serialize with `config.model_dump(mode='json')`
  - [ ] Format JSON with `json.dumps(indent=2)`
  - [ ] Use `atomic_write` with file locking
  - [ ] Handle errors appropriately
- [ ] Method: `add_server(self, name: str, server: MCPServer) -> None`
  - [ ] Validate server name
  - [ ] Check if server already exists
  - [ ] Raise `ServerAlreadyExistsError` if duplicate
  - [ ] Add to config
  - [ ] Save config
- [ ] Method: `remove_server(self, name: str) -> None`
  - [ ] Check if server exists
  - [ ] Remove from config
  - [ ] Save config
- [ ] Method: `get_server(self, name: str) -> Optional[MCPServer]`
  - [ ] Return server or None
- [ ] Method: `list_servers(self, scope: Optional[Scope] = None, server_type: Optional[MCPServerType] = None) -> dict[str, MCPServer]`
  - [ ] Load config
  - [ ] Apply filters if provided
  - [ ] Return filtered dict

### 3.2 Backup Manager (`backup.py`)
- [ ] Import models, file_handler, exceptions
- [ ] Class: `BackupManager`
  - [ ] `__init__(self, backup_dir: Optional[Path] = None)`
  - [ ] Set backup directory (default: `~/.mcp-manager/backups`)
  - [ ] Create directory if not exists
- [ ] Method: `create(self, config: Config, name: Optional[str] = None, reason: Optional[str] = None) -> Backup`
  - [ ] Create `Backup` object
  - [ ] Add metadata (reason, user, etc.)
  - [ ] Generate backup_id from timestamp
  - [ ] Save to file using `atomic_write`
  - [ ] Return Backup object
- [ ] Method: `list(self, limit: int = 10) -> list[Backup]`
  - [ ] List all backup files
  - [ ] Parse and validate
  - [ ] Sort by timestamp (newest first)
  - [ ] Return limited list
- [ ] Method: `restore(self, backup_id: str) -> Config`
  - [ ] Find backup file
  - [ ] Raise `BackupNotFoundError` if not found
  - [ ] Load and parse backup
  - [ ] Return Config object
- [ ] Method: `cleanup(self, keep: int = 5, older_than: Optional[str] = None) -> int`
  - [ ] List all backups
  - [ ] Determine which to delete
  - [ ] Delete old backups
  - [ ] Return count of deleted backups

### 3.3 Utilities Module (`utils.py`)
- [ ] Function: `get_config_path(scope: Scope) -> Path`
  - [ ] Return appropriate path based on scope
- [ ] Function: `expand_env_vars(text: str) -> str`
  - [ ] Expand `${VAR}` syntax
  - [ ] Support `${VAR:-default}` syntax
  - [ ] Use regex for pattern matching
- [ ] Function: `format_server_info(server: MCPServer) -> str`
  - [ ] Format server for display
- [ ] Add other utility functions as needed

---

## Phase 4: Presentation Layer (CLI)

### 4.1 CLI Module (`cli.py`)
- [ ] Import Typer, Rich, all business logic modules
- [ ] Create `app = typer.Typer(help="MCP Manager...")`
- [ ] Create `console = Console()`
- [ ] Function: `main()` entry point

#### 4.1.1 Global Options
- [ ] Add `--version` callback
- [ ] Add `--verbose` option
- [ ] Add `--config` option for custom config path

#### 4.1.2 List Command
- [ ] `@app.command()` decorator
- [ ] Function: `list(scope: Optional[Scope], format: str, ...)`
- [ ] Load servers via `ConfigManager`
- [ ] Filter by scope/type if provided
- [ ] Output in table/json/tree format
- [ ] Handle errors gracefully

#### 4.1.3 Show Command
- [ ] `@app.command()` decorator
- [ ] Function: `show(name: str, verbose: bool, json: bool)`
- [ ] Get server via `ConfigManager`
- [ ] Display server details
- [ ] Show env vars in verbose mode

#### 4.1.4 Add Command
- [ ] `@app.command()` decorator
- [ ] Function: `add(name: str, type: MCPServerType, command: Optional[str], ...)`
- [ ] Support interactive mode
- [ ] Validate all inputs
- [ ] Create MCPServer object
- [ ] Add via ConfigManager
- [ ] Print success message

#### 4.1.5 Remove Command
- [ ] `@app.command()` decorator
- [ ] Function: `remove(name: str, force: bool, backup: bool)`
- [ ] Confirm deletion (unless --force)
- [ ] Create backup if requested
- [ ] Remove via ConfigManager
- [ ] Print success message

#### 4.1.6 Backup Commands
- [ ] Group: `backup = typer.Typer()`
- [ ] Command: `backup_create(name: Optional[str], reason: Optional[str])`
- [ ] Command: `backup_list(limit: int)`
- [ ] Command: `backup_restore(backup_id: str)`
- [ ] Command: `backup_clean(keep: int, older_than: Optional[str])`

#### 4.1.7 Additional Commands
- [ ] Command: `enable(name: str)` (mark server as enabled)
- [ ] Command: `disable(name: str)` (mark server as disabled)
- [ ] Command: `validate(fix: bool)` (validate config)
- [ ] Command: `doctor(fix: bool)` (diagnose issues)

### 4.2 Rich Output Formatting
- [ ] Create Table for `list` command
- [ ] Create Tree for hierarchical display
- [ ] Add color codes (green=success, red=error, yellow=warning)
- [ ] Add icons (✓, ✗, ⚠, ℹ)
- [ ] Format error messages with recovery suggestions

---

## Phase 5: Advanced Features

### 5.1 Templates Module (`templates.py`)
- [ ] Class: `TemplateManager`
  - [ ] Load templates from `templates/` directory
  - [ ] Method: `list_templates() -> dict`
  - [ ] Method: `get_template(name: str) -> MCPServer`
  - [ ] Method: `install_template(template_name: str, server_name: Optional[str])`

### 5.2 Health Check Module (`health.py`)
- [ ] Class: `HealthChecker`
  - [ ] Method: `check(server: MCPServer) -> HealthStatus`
  - [ ] Method: `check_stdio_server(server: MCPServer) -> HealthStatus`
    - [ ] Check if command exists
    - [ ] Try running with --version
  - [ ] Method: `check_http_server(server: MCPServer) -> HealthStatus`
    - [ ] Test HTTP connection
  - [ ] Enum: `HealthStatus(HEALTHY, UNHEALTHY, UNKNOWN)`

### 5.3 Template Files
- [ ] Create `templates/time.json`
- [ ] Create `templates/fetch.json`
- [ ] Create `templates/filesystem.json`
- [ ] Create `templates/github.json`

---

## Phase 6: Testing

### 6.1 Test Infrastructure
- [ ] Create `tests/__init__.py`
- [ ] Create `tests/conftest.py` with fixtures
- [ ] Create `tests/fixtures/` directory
- [ ] Add `valid_config.json` fixture
- [ ] Add `corrupted_config.json` fixture

### 6.2 Unit Tests
- [ ] `tests/unit/test_validators.py`
  - [ ] Test all validation functions
  - [ ] Test valid and invalid inputs
  - [ ] Test error messages
- [ ] `tests/unit/test_config.py`
  - [ ] Test ConfigManager.load()
  - [ ] Test ConfigManager.save()
  - [ ] Test ConfigManager.add_server()
  - [ ] Test ConfigManager.remove_server()
  - [ ] Test error cases
- [ ] `tests/unit/test_backup.py`
  - [ ] Test BackupManager.create()
  - [ ] Test BackupManager.restore()
  - [ ] Test BackupManager.cleanup()
- [ ] `tests/unit/test_file_handler.py`
  - [ ] Test atomic_write()
  - [ ] Test file locking
  - [ ] Test concurrent access
- [ ] `tests/unit/test_models.py`
  - [ ] Test Pydantic validation
  - [ ] Test field validators
  - [ ] Test serialization

### 6.3 Integration Tests
- [ ] `tests/integration/test_add_remove_flow.py`
  - [ ] Test full add → save → load → remove cycle
- [ ] `tests/integration/test_atomic_write.py`
  - [ ] Test concurrent writes
- [ ] `tests/integration/test_backup_restore.py`
  - [ ] Test backup → modify → restore cycle

### 6.4 E2E Tests
- [ ] `tests/e2e/test_cli.py`
  - [ ] Test all CLI commands
  - [ ] Test error handling
  - [ ] Use CliRunner from Typer

### 6.5 Coverage
- [ ] Run `pytest --cov`
- [ ] Ensure >= 80% coverage
- [ ] Ensure 100% coverage for critical modules

---

## Phase 7: Documentation & Polish

### 7.1 Code Documentation
- [ ] Add docstrings to all public functions
- [ ] Add type hints to all functions
- [ ] Add inline comments for complex logic

### 7.2 User Documentation
- [ ] Update README.md with installation instructions
- [ ] Add usage examples
- [ ] Add troubleshooting section

### 7.3 CHANGELOG
- [ ] Create `CHANGELOG.md`
- [ ] Document v0.1.0 features

### 7.4 LICENSE
- [ ] Create `LICENSE` file (MIT)

---

## Phase 8: Release Preparation

### 8.1 Version 0.1.0 MVP
- [ ] All Phase 1-4 tasks complete
- [ ] All tests passing
- [ ] Coverage >= 80%
- [ ] Documentation complete

### 8.2 Code Quality
- [ ] Run `black` formatter
- [ ] Run `ruff` linter (fix all issues)
- [ ] Run `mypy` type checker (no errors)

### 8.3 Build & Test
- [ ] Run `uv build`
- [ ] Test installation: `uv tool install dist/*.whl`
- [ ] Test all commands manually
- [ ] Uninstall: `uv tool uninstall mcp-manager`

### 8.4 Git Tagging
- [ ] Create git tag: `git tag -a v0.1.0 -m "Version 0.1.0"`
- [ ] Push tag: `git push origin v0.1.0`

### 8.5 GitHub Release
- [ ] Create GitHub release
- [ ] Attach wheel and tarball
- [ ] Write release notes

### 8.6 PyPI Publication (Optional)
- [ ] Create PyPI account
- [ ] Generate API token
- [ ] Publish: `uv run twine upload dist/*`

---

## Progress Tracking

### Phase 1: Core Infrastructure
Progress: 0/3 modules complete

### Phase 2: Data Layer
Progress: 0/3 modules complete

### Phase 3: Business Logic
Progress: 0/3 modules complete

### Phase 4: CLI
Progress: 0/7 command groups complete

### Phase 5: Advanced Features
Progress: 0/3 modules complete

### Phase 6: Testing
Progress: 0/5 test categories complete

### Phase 7: Documentation
Progress: 0/4 documentation items complete

### Phase 8: Release
Progress: 0/6 release tasks complete

---

## Notes

- Always run tests after each module completion
- Commit frequently with clear messages
- Follow Python PEP 8 style guide
- Use type hints everywhere
- Write docstrings for all public APIs
- Test edge cases and error conditions
- Keep security in mind (no shell execution, validate inputs)

## Commands Reference

```bash
# Development
uv sync                    # Install dependencies
uv run pytest              # Run tests
uv run pytest --cov        # Run tests with coverage
uv run black src/ tests/   # Format code
uv run ruff check src/     # Lint code
uv run mypy src/           # Type check

# Testing CLI
uv run mcpm --help         # Test CLI help
uv run mcpm list           # Test list command
uv run mcpm add test --interactive  # Test add command

# Build
uv build                   # Build package
uv tool install dist/*.whl # Install locally
```
