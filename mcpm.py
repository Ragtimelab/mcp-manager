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
from rich.table import Table

app = typer.Typer(
    name="mcpm",
    help="Simple CLI for managing MCP servers",
    add_completion=False,
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


@app.command("list", help="List all MCP servers")
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


@app.command("upgrade", help="Upgrade MCP servers")
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

    console.print("🔄 Upgrading MCP servers...")

    for sname, server in servers.items():
        cmd = server["command"]
        args = server["args"]

        try:
            if cmd == "uvx":
                # uvx --refresh <package>
                subprocess.run(
                    ["uvx", "--refresh", *args, "--help"],
                    capture_output=True,
                    check=True,
                    timeout=30,
                )
            elif cmd == "npx":
                # npm cache clean (latest version will be downloaded on next use)
                subprocess.run(
                    ["npm", "cache", "clean", "--force"],
                    capture_output=True,
                    timeout=30,
                )

            console.print(f"[green]✓[/] {sname}")
        except Exception as e:
            console.print(f"[red]✗[/] {sname}: {e}")

    console.print("[green]✅ Done![/]")


@app.command("health", help="Check MCP server health")
def health_check(name: Optional[str] = typer.Argument(None, help="Server name")):
    """Check health of MCP servers"""
    config = load_config()
    servers = get_servers(config)

    if name:
        if name not in servers:
            console.print(f"[red]✗[/] Server '{name}' not found")
            raise typer.Exit(1)
        servers = {name: servers[name]}

    console.print("Checking MCP servers...")

    for sname, server in servers.items():
        cmd = server["command"]
        args = server["args"]

        try:
            if cmd == "uvx":
                # uvx uses cache, safe to execute
                result = subprocess.run(
                    [cmd, *args, "--help"], capture_output=True, timeout=30
                )
                if result.returncode == 0:
                    console.print(f"[green]✓[/] {sname}: OK")
                else:
                    console.print(
                        f"[red]✗[/] {sname}: ERROR (exit code {result.returncode})"
                    )
            elif cmd == "npx":
                # npx may download packages, only check command availability
                if shutil.which(cmd):
                    console.print(f"[green]✓[/] {sname}: OK (npx available)")
                else:
                    console.print(f"[red]✗[/] {sname}: npx not found in PATH")
            else:
                # Other commands: try to execute
                result = subprocess.run(
                    [cmd, *args, "--help"], capture_output=True, timeout=30
                )
                if result.returncode == 0:
                    console.print(f"[green]✓[/] {sname}: OK")
                else:
                    console.print(
                        f"[red]✗[/] {sname}: ERROR (exit code {result.returncode})"
                    )
        except Exception as e:
            console.print(f"[red]✗[/] {sname}: ERROR ({e})")


@app.command("show", help="Show MCP server details")
def show_server(name: str = typer.Argument(..., help="Server name")):
    """Show detailed info for a server"""
    config = load_config()
    servers = get_servers(config)

    if name not in servers:
        console.print(f"[red]✗[/] Server '{name}' not found")
        raise typer.Exit(1)

    server = servers[name]
    console.print(f"\n[cyan]Server: {name}[/]")
    console.print(f"├─ Type: {server['type']}")
    console.print(f"├─ Command: {server['command']}")
    console.print(f"├─ Args: {server['args']}")
    console.print(f"└─ Env: {server.get('env', {})}\n")


@app.command("backup", help="Backup/restore config")
def backup_config(
    list_backups: bool = typer.Option(False, "-l", "--list", help="List backups"),
    restore: Optional[str] = typer.Option(
        None, "-r", "--restore", help="Restore backup"
    ),
):
    """Backup or restore ~/.claude.json"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    if list_backups:
        backups = sorted(BACKUP_DIR.glob("*.json"), reverse=True)
        if not backups:
            console.print("[yellow]No backups found[/]")
            return

        console.print("[cyan]Available backups:[/]")
        for i, backup in enumerate(backups, 1):
            # 파일명에서 날짜 파싱 (YYYYMMDD-HHMMSS)
            timestamp = backup.stem
            try:
                dt = datetime.strptime(timestamp, "%Y%m%d-%H%M%S")
                console.print(
                    f"  {i}. {timestamp}.json ({dt.strftime('%Y-%m-%d %H:%M:%S')})"
                )
            except ValueError:
                console.print(f"  {i}. {backup.name}")
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

    # 백업 생성
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_file = BACKUP_DIR / f"{timestamp}.json"

    config = load_config()
    with open(backup_file, "w") as f:
        json.dump(config, f, indent=2)

    console.print(f"[green]✅ Backup created:[/] {backup_file}")


@app.command("install", help="Install MCP server")
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
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_file = BACKUP_DIR / f"{timestamp}.json"
    with open(backup_file, "w") as f:
        json.dump(config, f, indent=2)

    # Add server
    servers[server_name] = {"type": "stdio", "command": cmd, "args": args}
    config["mcpServers"] = servers

    # Save
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    console.print(f"[green]✓[/] Installed '{server_name}'")
    console.print(f"  Command: {cmd} {' '.join(args)}")
    console.print("[yellow]Note:[/] Restart Claude Code to activate")


@app.command("uninstall", help="Uninstall MCP server")
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
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_file = BACKUP_DIR / f"{timestamp}.json"
    with open(backup_file, "w") as f:
        json.dump(config, f, indent=2)

    # Remove server
    del servers[name]
    config["mcpServers"] = servers

    # Save
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    console.print(f"[green]✓[/] Uninstalled '{name}'")
    console.print("[yellow]Note:[/] Restart Claude Code to apply changes")


@app.command("disable", help="Disable MCP server")
def disable_server(name: str = typer.Argument(..., help="Server name")):
    """Disable MCP server (move to _disabled_mcpServers)"""
    config = load_config()
    servers = config.get("mcpServers", {})
    disabled = config.get("_disabled_mcpServers", {})

    if name not in servers:
        console.print(f"[red]✗[/] Server '{name}' not found or already disabled")
        raise typer.Exit(1)

    # Create backup
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_file = BACKUP_DIR / f"{timestamp}.json"
    with open(backup_file, "w") as f:
        json.dump(config, f, indent=2)

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


@app.command("enable", help="Enable MCP server")
def enable_server(name: str = typer.Argument(..., help="Server name")):
    """Enable MCP server (move from _disabled_mcpServers)"""
    config = load_config()
    servers = config.get("mcpServers", {})
    disabled = config.get("_disabled_mcpServers", {})

    if name not in disabled:
        console.print(f"[red]✗[/] Server '{name}' not found in disabled servers")
        raise typer.Exit(1)

    # Create backup
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_file = BACKUP_DIR / f"{timestamp}.json"
    with open(backup_file, "w") as f:
        json.dump(config, f, indent=2)

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


@app.command("doctor", help="Diagnose config issues")
def doctor():
    """Diagnose MCP configuration and suggest fixes"""
    console.print("[bold]Diagnosing MCP configuration...[/]\n")

    errors = 0
    warnings = 0

    # Check 1: Config file exists
    if not CONFIG_PATH.exists():
        console.print("[red]✗[/] ~/.claude.json not found")
        errors += 1
        console.print("\n[yellow]Suggestions:[/]")
        console.print("1. Run Claude Code to create the config file")
        console.print("2. Or create manually: touch ~/.claude.json")
        raise typer.Exit(1)

    console.print("[green]✓[/] ~/.claude.json exists")

    # Check 2: Valid JSON
    try:
        with open(CONFIG_PATH) as f:
            config = json.load(f)
        console.print("[green]✓[/] Valid JSON syntax")
    except json.JSONDecodeError as e:
        console.print(f"[red]✗[/] Invalid JSON: {e}")
        errors += 1
        console.print("\n[yellow]Suggestions:[/]")
        console.print(f"1. Fix JSON syntax error at line {e.lineno}")
        console.print("2. Restore from backup: mcpm backup -l")
        raise typer.Exit(1)

    # Check 3: mcpServers field exists
    servers = config.get("mcpServers", {})
    if not servers:
        console.print("[yellow]⚠[/] No MCP servers configured")
        warnings += 1
    else:
        console.print(f"[green]✓[/] mcpServers field found ({len(servers)} servers)\n")

    # Check 4: Validate each server
    if servers:
        console.print("[bold]Checking servers:[/]")
        for name, server in servers.items():
            server_errors = []
            server_warnings = []

            # Check required fields
            if "type" not in server:
                server_errors.append("missing 'type' field")
            elif server["type"] not in ["stdio", "sse", "http"]:
                server_errors.append(f"invalid type '{server['type']}'")

            if server.get("type") == "stdio":
                if "command" not in server:
                    server_errors.append("missing 'command' field")
                if "args" not in server:
                    server_warnings.append("missing 'args' field (using [])")

            # Check command availability
            cmd = server.get("command")
            if cmd:
                if not shutil.which(cmd):
                    server_errors.append(f"command '{cmd}' not found in PATH")

            # Check args length
            args = server.get("args", [])
            if len(args) > 10:
                server_warnings.append(f"large args array ({len(args)} items)")

            # Print results
            if server_errors:
                console.print(f"[red]✗[/] {name}: {', '.join(server_errors)}")
                errors += len(server_errors)
            elif server_warnings:
                console.print(f"[yellow]⚠[/] {name}: {', '.join(server_warnings)}")
                warnings += len(server_warnings)
            else:
                console.print(f"[green]✓[/] {name}: Valid configuration")

    # Check 5: Required commands availability
    console.print("\n[bold]Checking system commands:[/]")
    required_commands = {"uvx": "uv", "npx": "node/npm"}

    for cmd, pkg in required_commands.items():
        if shutil.which(cmd):
            console.print(f"[green]✓[/] {cmd} available")
        else:
            console.print(f"[yellow]⚠[/] {cmd} not found (needed for {pkg} servers)")
            warnings += 1

    # Summary
    console.print("\n[bold]Summary:[/]")
    if errors == 0 and warnings == 0:
        console.print(
            "[green]✅ No issues found! Your MCP configuration is healthy.[/]"
        )
    else:
        console.print(
            f"Issues found: [red]{errors} error(s)[/], [yellow]{warnings} warning(s)[/]"
        )

        if errors > 0:
            console.print("\n[yellow]Suggestions:[/]")
            console.print("1. Fix errors above to ensure MCP servers work correctly")
            console.print("2. Run 'mcpm list' to verify server configuration")
            console.print("3. Run 'mcpm health' to test server executability")

    raise typer.Exit(0 if errors == 0 else 1)


if __name__ == "__main__":
    app()
