#!/usr/bin/env python3
"""MCP Manager - Simple CLI for managing MCP servers"""

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.tree import Tree

app = typer.Typer(
    name="mcpm",
    help="Simple CLI for managing MCP servers",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()

# 상수
CONFIG_PATH = Path.home() / ".claude.json"
BACKUP_DIR = Path.home() / ".mcp-manager" / "backups"


def load_config() -> dict:
    """Load ~/.claude.json"""
    # 추측 금지: 파일 존재 확인
    if not CONFIG_PATH.exists():
        console.print("[red]✗[/] ~/.claude.json not found")
        raise typer.Exit(1)

    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except json.JSONDecodeError:
        console.print("[red]✗[/] ~/.claude.json is corrupted")
        raise typer.Exit(1)


def get_servers(config: dict) -> dict:
    """Extract mcpServers from config"""
    return config.get("mcpServers", {})


def create_backup(config: dict) -> Path:
    """Create timestamped backup of config"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_file = BACKUP_DIR / f"{timestamp}.json"
    with open(backup_file, "w") as f:
        json.dump(config, f, indent=2)
    return backup_file


@app.command("list", help="List all configured MCP servers [dim]\\[ls][/dim]")
@app.command("ls", hidden=True)
def list_servers(
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Show detailed info"),
    all_servers: bool = typer.Option(False, "-a", "--all", help="Include disabled servers"),
):
    """List all MCP servers"""
    config = load_config()
    servers = get_servers(config)
    disabled = config.get("_disabled_mcpServers", {})

    if not servers and not disabled:
        console.print("[yellow]No MCP servers found[/]")
        return

    table = Table(title="MCP Servers")
    table.add_column("Name", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Type", style="magenta")
    table.add_column("Command", style="green")
    if verbose:
        table.add_column("Env", style="yellow")

    # Active servers
    for name, server in servers.items():
        cmd = f"{server['command']} {' '.join(server['args'])}"
        row = [name, "[green]●[/] active", server["type"], cmd]
        if verbose:
            row.append(str(server.get("env", {})))
        table.add_row(*row)

    # Disabled servers
    if all_servers and disabled:
        for name, server in disabled.items():
            cmd = f"{server['command']} {' '.join(server['args'])}"
            row = [name, "[dim]○[/] disabled", server["type"], cmd]
            if verbose:
                row.append(str(server.get("env", {})))
            table.add_row(*row)

    console.print(table)

    if disabled and not all_servers:
        console.print(f"\n[dim]{len(disabled)} disabled server(s). Use -a to show all.[/]")


@app.command("upgrade", help="Upgrade MCP server packages [dim]\\[up][/dim]")
@app.command("up", hidden=True)
def upgrade_servers(name: Optional[str] = typer.Argument(None, help="Server name")):
    """Upgrade all or specific MCP server"""
    config = load_config()
    servers = get_servers(config)

    # 필터링
    if name:
        if name not in servers:
            console.print(f"[red]✗[/] Server '{name}' not found")
            raise typer.Exit(1)
        servers = {name: servers[name]}

    results: list[tuple[str, bool, str]] = []  # (name, success, message)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Upgrading MCP servers...", total=len(servers))

        for sname, server in servers.items():
            progress.update(task, description=f"Upgrading {sname}...")
            cmd = server["command"]
            args = server["args"]

            try:
                if cmd == "uvx":
                    subprocess.run(
                        ["uvx", "--refresh", *args, "--help"],
                        capture_output=True,
                        check=True,
                        timeout=30,
                    )
                    results.append((sname, True, "refreshed"))
                elif cmd == "npx":
                    subprocess.run(
                        ["npm", "cache", "clean", "--force"],
                        capture_output=True,
                        timeout=30,
                    )
                    results.append((sname, True, "cache cleared"))
                else:
                    results.append((sname, True, "skipped (unknown type)"))
            except subprocess.TimeoutExpired:
                results.append((sname, False, "timeout"))
            except subprocess.CalledProcessError as e:
                results.append((sname, False, f"exit code {e.returncode}"))
            except Exception as e:
                results.append((sname, False, str(e)))

            progress.advance(task)

    # 결과 테이블
    table = Table(title="Upgrade Results", show_header=True)
    table.add_column("Server", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Details", style="dim")

    success_count = 0
    for sname, success, msg in results:
        if success:
            table.add_row(sname, "[green]✓[/] OK", msg)
            success_count += 1
        else:
            table.add_row(sname, "[red]✗[/] FAILED", msg)

    console.print(table)
    console.print(f"\n[green]✓[/] {success_count}/{len(results)} upgraded successfully")


@app.command("health", help="Check health of MCP servers")
def health_check(name: Optional[str] = typer.Argument(None, help="Server name")):
    """Check health of MCP servers"""
    config = load_config()
    servers = get_servers(config)

    if name:
        if name not in servers:
            console.print(f"[red]✗[/] Server '{name}' not found")
            raise typer.Exit(1)
        servers = {name: servers[name]}

    results: list[tuple[str, str, str, str]] = []  # (name, type, status, details)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Checking MCP servers...", total=len(servers))

        for sname, server in servers.items():
            progress.update(task, description=f"Checking {sname}...")
            cmd = server["command"]
            args = server["args"]

            try:
                if cmd == "uvx":
                    result = subprocess.run(
                        [cmd, *args, "--help"], capture_output=True, timeout=30
                    )
                    if result.returncode == 0:
                        results.append((sname, "uvx", "ok", "executable"))
                    else:
                        results.append(
                            (sname, "uvx", "error", f"exit code {result.returncode}")
                        )
                elif cmd == "npx":
                    if shutil.which(cmd):
                        results.append((sname, "npx", "ok", "npx available"))
                    else:
                        results.append((sname, "npx", "error", "npx not in PATH"))
                else:
                    result = subprocess.run(
                        [cmd, *args, "--help"], capture_output=True, timeout=30
                    )
                    if result.returncode == 0:
                        results.append((sname, cmd, "ok", "executable"))
                    else:
                        results.append(
                            (sname, cmd, "error", f"exit code {result.returncode}")
                        )
            except subprocess.TimeoutExpired:
                results.append((sname, cmd, "error", "timeout"))
            except Exception as e:
                results.append((sname, cmd, "error", str(e)))

            progress.advance(task)

    # 결과 테이블
    table = Table(title="Health Check Results", show_header=True)
    table.add_column("Server", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Status", style="white")
    table.add_column("Details", style="dim")

    healthy = 0
    for sname, stype, status, details in results:
        if status == "ok":
            table.add_row(sname, stype, "[green]● Healthy[/]", details)
            healthy += 1
        else:
            table.add_row(sname, stype, "[red]● Unhealthy[/]", details)

    console.print(table)
    console.print(f"\n[green]✓[/] {healthy}/{len(results)} servers healthy")


@app.command("show", help="Show details for a specific server")
def show_server(name: str = typer.Argument(..., help="Server name")):
    """Show detailed info for a server"""
    config = load_config()
    servers = get_servers(config)
    disabled = config.get("_disabled_mcpServers", {})

    # 활성 서버 또는 비활성 서버에서 찾기
    if name in servers:
        server = servers[name]
        status = "[green]● active[/]"
    elif name in disabled:
        server = disabled[name]
        status = "[dim]○ disabled[/]"
    else:
        console.print(f"[red]✗[/] Server '{name}' not found")
        raise typer.Exit(1)

    # Rich Tree로 표시
    tree = Tree(f"[bold cyan]{name}[/] {status}")
    tree.add(f"[white]Type:[/] [yellow]{server['type']}[/]")
    tree.add(f"[white]Command:[/] [green]{server['command']}[/]")

    args_branch = tree.add("[white]Args:[/]")
    for arg in server.get("args", []):
        args_branch.add(f"[dim]{arg}[/]")

    env = server.get("env", {})
    if env:
        env_branch = tree.add("[white]Env:[/]")
        for key, val in env.items():
            # 민감한 값 마스킹
            display_val = val if len(val) < 20 else f"{val[:8]}...{val[-4:]}"
            env_branch.add(f"[blue]{key}[/]=[dim]{display_val}[/]")
    else:
        tree.add("[white]Env:[/] [dim](none)[/]")

    console.print()
    console.print(tree)
    console.print()


@app.command("backup", help="Create and restore configuration backups")
def backup_config(
    list_backups: bool = typer.Option(False, "-l", "--list", help="List backups"),
    restore: Optional[str] = typer.Option(
        None, "-r", "--restore", help="Restore backup"
    ),
    delete: Optional[str] = typer.Option(None, "-d", "--delete", help="Delete backup"),
    clean: bool = typer.Option(False, "--clean", help="Clean up old backups"),
    keep: Optional[int] = typer.Option(None, "--keep", help="Keep N recent backups (use with --clean)"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
):
    """Backup or restore ~/.claude.json"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    if list_backups:
        backups = sorted(BACKUP_DIR.glob("*.json"), reverse=True)
        if not backups:
            console.print("[yellow]No backups found[/]")
            return

        table = Table(title="Backups", show_header=True)
        table.add_column("ID", style="cyan", justify="right")
        table.add_column("Filename", style="white")
        table.add_column("Created", style="green")
        table.add_column("Size", style="dim", justify="right")

        for i, backup in enumerate(backups, 1):
            timestamp = backup.stem
            size = backup.stat().st_size
            size_str = f"{size:,} B" if size < 1024 else f"{size / 1024:.1f} KB"
            try:
                dt = datetime.strptime(timestamp, "%Y%m%d-%H%M%S")
                table.add_row(str(i), backup.name, dt.strftime("%Y-%m-%d %H:%M:%S"), size_str)
            except ValueError:
                table.add_row(str(i), backup.name, "-", size_str)

        console.print(table)
        console.print("\n[dim]Use 'mcpm backup -r <ID>' to restore[/]")
        return

    if restore:
        backup_file = (
            BACKUP_DIR / f"{restore}.json"
            if not restore.endswith(".json")
            else BACKUP_DIR / restore
        )
        if not backup_file.exists():
            console.print(f"[red]✗[/] Backup not found: {restore}")
            raise typer.Exit(1)

        console.print(f"🔄 Restoring from {backup_file.name}...")
        with open(backup_file) as f:
            config = json.load(f)
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
        console.print("[green]✅ Restored successfully![/]")
        return

    if delete:
        backups = sorted(BACKUP_DIR.glob("*.json"), reverse=True)
        if not backups:
            console.print("[yellow]No backups found[/]")
            return

        # ID 또는 타임스탬프로 백업 찾기
        target_file: Optional[Path] = None
        if delete.isdigit():
            # 숫자 ID로 찾기
            idx = int(delete) - 1
            if 0 <= idx < len(backups):
                target_file = backups[idx]
        else:
            # 타임스탬프로 찾기
            timestamp = delete if delete.endswith(".json") else f"{delete}.json"
            temp_file = BACKUP_DIR / timestamp
            if temp_file.exists():
                target_file = temp_file

        if not target_file:
            console.print(f"[red]✗[/] Backup not found: {delete}")
            raise typer.Exit(1)

        # 확인
        if not force:
            console.print(f"[yellow]Delete backup '{target_file.name}'?[/]")
            confirm = typer.confirm("Continue?")
            if not confirm:
                console.print("[yellow]Cancelled[/]")
                raise typer.Exit(0)

        target_file.unlink()
        console.print(f"[green]✓[/] Deleted backup: {target_file.name}")
        return

    if clean:
        backups = sorted(BACKUP_DIR.glob("*.json"), reverse=True)
        if not backups:
            console.print("[yellow]No backups found[/]")
            return

        # keep 옵션으로 유지할 백업 수 결정
        if keep is not None:
            to_delete = backups[keep:]
            to_keep = backups[:keep]
        else:
            to_delete = backups
            to_keep = []

        if not to_delete:
            console.print("[yellow]No backups to delete[/]")
            return

        # 확인
        if not force:
            console.print(f"[yellow]Delete {len(to_delete)} backup(s)?[/]")
            if to_keep:
                console.print(f"[dim]Keeping {len(to_keep)} most recent backup(s)[/]")
            for backup in to_delete[:5]:  # 처음 5개만 미리보기
                console.print(f"  - {backup.name}")
            if len(to_delete) > 5:
                console.print(f"  ... and {len(to_delete) - 5} more")

            confirm = typer.confirm("Continue?")
            if not confirm:
                console.print("[yellow]Cancelled[/]")
                raise typer.Exit(0)

        # 삭제 실행
        for backup in to_delete:
            backup.unlink()

        console.print(f"[green]✓[/] Deleted {len(to_delete)} backup(s)")
        if to_keep:
            console.print(f"[dim]Kept {len(to_keep)} most recent backup(s)[/]")
        return

    # 백업 생성
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_file = BACKUP_DIR / f"{timestamp}.json"

    config = load_config()
    with open(backup_file, "w") as f:
        json.dump(config, f, indent=2)

    console.print(f"[green]✅ Backup created:[/] {backup_file}")


@app.command("install", help="Install and configure an MCP server")
def install_server(
    package: str = typer.Argument(..., help="Package name"),
    name: Optional[str] = typer.Option(None, "--name", help="Custom server name"),
):
    """Install and configure MCP server"""
    config = load_config()
    servers = config.get("mcpServers", {})

    # Detect package type
    if package.startswith("@") or "/" in package:
        cmd = "npx"
        args = ["-y", package]
    else:
        cmd = "uvx"
        args = [package]

    # Determine server name
    server_name = name or package.split("/")[-1].replace("@", "").replace("mcp-server-", "")

    # Check if already exists
    if server_name in servers:
        console.print(f"[red]✗[/] Server '{server_name}' already exists")
        console.print(f"[yellow]Hint:[/] Use 'mcpm uninstall {server_name}' first")
        raise typer.Exit(1)

    # Create backup
    create_backup(config)

    # Add server
    servers[server_name] = {"type": "stdio", "command": cmd, "args": args}
    config["mcpServers"] = servers

    # Save
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    console.print(f"[green]✓[/] Installed '{server_name}'")
    console.print(f"  Command: {cmd} {' '.join(args)}")
    console.print("[yellow]Note:[/] Restart Claude Code to activate")


@app.command("uninstall", help="Remove an MCP server from configuration")
def uninstall_server(
    name: str = typer.Argument(..., help="Server name"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
):
    """Remove MCP server from configuration"""
    config = load_config()
    servers = config.get("mcpServers", {})

    if name not in servers:
        console.print(f"[red]✗[/] Server '{name}' not found")
        raise typer.Exit(1)

    # Confirmation
    if not force:
        console.print(f"[yellow]Remove server '{name}'?[/]")
        console.print(f"  Command: {servers[name]['command']} {' '.join(servers[name]['args'])}")
        confirm = typer.confirm("Continue?")
        if not confirm:
            console.print("[yellow]Cancelled[/]")
            raise typer.Exit(0)

    # Create backup
    create_backup(config)

    # Remove server
    del servers[name]
    config["mcpServers"] = servers

    # Save
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    console.print(f"[green]✓[/] Uninstalled '{name}'")
    console.print("[yellow]Note:[/] Restart Claude Code to apply changes")


@app.command("disable", help="Temporarily disable an MCP server")
def disable_server(name: str = typer.Argument(..., help="Server name")):
    """Disable MCP server (move to _disabled_mcpServers)"""
    config = load_config()
    servers = config.get("mcpServers", {})
    disabled = config.get("_disabled_mcpServers", {})

    if name not in servers:
        console.print(f"[red]✗[/] Server '{name}' not found or already disabled")
        raise typer.Exit(1)

    # Create backup
    create_backup(config)

    # Move to disabled
    disabled[name] = servers[name]
    del servers[name]
    config["mcpServers"] = servers
    config["_disabled_mcpServers"] = disabled

    # Save
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    console.print(f"[green]✓[/] Disabled '{name}'")
    console.print("[yellow]Note:[/] Restart Claude Code to apply changes")


@app.command("enable", help="Re-enable a disabled MCP server")
def enable_server(name: str = typer.Argument(..., help="Server name")):
    """Enable MCP server (move from _disabled_mcpServers)"""
    config = load_config()
    servers = config.get("mcpServers", {})
    disabled = config.get("_disabled_mcpServers", {})

    if name not in disabled:
        console.print(f"[red]✗[/] Server '{name}' not found in disabled servers")
        raise typer.Exit(1)

    # Create backup
    create_backup(config)

    # Move to active
    servers[name] = disabled[name]
    del disabled[name]
    config["mcpServers"] = servers
    if disabled:
        config["_disabled_mcpServers"] = disabled
    else:
        config.pop("_disabled_mcpServers", None)

    # Save
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    console.print(f"[green]✓[/] Enabled '{name}'")
    console.print("[yellow]Note:[/] Restart Claude Code to activate")


@app.command("doctor", help="Diagnose configuration issues")
def doctor():
    """Diagnose MCP configuration and suggest fixes"""
    console.print(Panel("[bold]MCP Configuration Diagnostics[/]", style="cyan"))

    errors = 0
    warnings = 0
    config_checks: list[tuple[str, str, str]] = []  # (check, status, details)

    # Check 1: Config file exists
    if not CONFIG_PATH.exists():
        config_checks.append(("Config file", "error", "~/.claude.json not found"))
        errors += 1
        _print_doctor_results(config_checks, [], [], errors, warnings)
        console.print(Panel(
            "[yellow]Suggestions:[/]\n"
            "1. Run Claude Code to create the config file\n"
            "2. Or create manually: touch ~/.claude.json",
            title="How to fix",
            style="yellow",
        ))
        raise typer.Exit(1)

    config_checks.append(("Config file", "ok", "~/.claude.json exists"))

    # Check 2: Valid JSON
    try:
        with open(CONFIG_PATH) as f:
            config = json.load(f)
        config_checks.append(("JSON syntax", "ok", "Valid JSON"))
    except json.JSONDecodeError as e:
        config_checks.append(("JSON syntax", "error", f"Invalid: line {e.lineno}"))
        errors += 1
        _print_doctor_results(config_checks, [], [], errors, warnings)
        console.print(Panel(
            f"[yellow]Suggestions:[/]\n"
            f"1. Fix JSON syntax error at line {e.lineno}\n"
            f"2. Restore from backup: mcpm backup -l",
            title="How to fix",
            style="yellow",
        ))
        raise typer.Exit(1)

    # Check 3: mcpServers field exists
    servers = config.get("mcpServers", {})
    if not servers:
        config_checks.append(("mcpServers", "warning", "No servers configured"))
        warnings += 1
    else:
        config_checks.append(("mcpServers", "ok", f"{len(servers)} server(s) found"))

    # Check 4: Validate each server
    server_results: list[tuple[str, str, str]] = []
    for name, server in servers.items():
        server_errors = []
        server_warnings = []

        if "type" not in server:
            server_errors.append("missing 'type'")
        elif server["type"] not in ["stdio", "sse", "http"]:
            server_errors.append("invalid type")

        if server.get("type") == "stdio":
            if "command" not in server:
                server_errors.append("missing 'command'")
            if "args" not in server:
                server_warnings.append("no 'args'")

        cmd = server.get("command")
        if cmd and not shutil.which(cmd):
            server_errors.append(f"'{cmd}' not in PATH")

        if server_errors:
            server_results.append((name, "error", ", ".join(server_errors)))
            errors += len(server_errors)
        elif server_warnings:
            server_results.append((name, "warning", ", ".join(server_warnings)))
            warnings += len(server_warnings)
        else:
            server_results.append((name, "ok", "Valid"))

    # Check 5: Required commands
    cmd_results: list[tuple[str, str, str]] = []
    required_commands = {"uvx": "Python MCP servers", "npx": "Node.js MCP servers"}

    for cmd, desc in required_commands.items():
        if shutil.which(cmd):
            cmd_results.append((cmd, "ok", desc))
        else:
            cmd_results.append((cmd, "warning", f"Not found ({desc})"))
            warnings += 1

    # Print all results
    _print_doctor_results(config_checks, server_results, cmd_results, errors, warnings)

    raise typer.Exit(0 if errors == 0 else 1)


def _print_doctor_results(
    config_checks: list[tuple[str, str, str]],
    server_results: list[tuple[str, str, str]],
    cmd_results: list[tuple[str, str, str]],
    errors: int,
    warnings: int,
) -> None:
    """Print doctor diagnostic results in tables"""
    # Config checks table
    if config_checks:
        table = Table(title="Configuration", show_header=True, title_style="bold")
        table.add_column("Check", style="cyan")
        table.add_column("Status")
        table.add_column("Details", style="dim")

        for check, status, details in config_checks:
            status_str = {
                "ok": "[green]● OK[/]",
                "warning": "[yellow]● Warning[/]",
                "error": "[red]● Error[/]",
            }.get(status, status)
            table.add_row(check, status_str, details)

        console.print(table)
        console.print()

    # Server checks table
    if server_results:
        table = Table(title="Servers", show_header=True, title_style="bold")
        table.add_column("Server", style="cyan")
        table.add_column("Status")
        table.add_column("Details", style="dim")

        for name, status, details in server_results:
            status_str = {
                "ok": "[green]● Valid[/]",
                "warning": "[yellow]● Warning[/]",
                "error": "[red]● Invalid[/]",
            }.get(status, status)
            table.add_row(name, status_str, details)

        console.print(table)
        console.print()

    # System commands table
    if cmd_results:
        table = Table(title="System Commands", show_header=True, title_style="bold")
        table.add_column("Command", style="cyan")
        table.add_column("Status")
        table.add_column("Used for", style="dim")

        for cmd, status, desc in cmd_results:
            status_str = {
                "ok": "[green]● Available[/]",
                "warning": "[yellow]● Missing[/]",
            }.get(status, status)
            table.add_row(cmd, status_str, desc)

        console.print(table)
        console.print()

    # Summary panel
    if errors == 0 and warnings == 0:
        console.print(Panel(
            "[green]No issues found! Your MCP configuration is healthy.[/]",
            title="Summary",
            style="green",
        ))
    else:
        summary_lines = [f"[red]{errors} error(s)[/], [yellow]{warnings} warning(s)[/]"]
        if errors > 0:
            summary_lines.append("")
            summary_lines.append("[dim]Run 'mcpm health' to test server executability[/]")
        console.print(Panel(
            "\n".join(summary_lines),
            title="Summary",
            style="red" if errors > 0 else "yellow",
        ))


if __name__ == "__main__":
    app()
