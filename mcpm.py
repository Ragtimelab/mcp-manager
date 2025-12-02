#!/usr/bin/env python3
"""MCP Manager - Simple CLI for managing MCP servers"""

import json
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
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Show detailed info")
):
    """List all MCP servers"""
    config = load_config()
    servers = get_servers(config)

    if not servers:
        console.print("[yellow]No MCP servers found[/]")
        return

    table = Table(title="MCP Servers")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Command", style="green")
    if verbose:
        table.add_column("Env", style="yellow")

    for name, server in servers.items():
        cmd = f"{server['command']} {' '.join(server['args'])}"
        row = [name, server['type'], cmd]
        if verbose:
            row.append(str(server.get('env', {})))
        table.add_row(*row)

    console.print(table)


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
                # npm cache clean + npx @package@latest
                subprocess.run(
                    ["npm", "cache", "clean", "--force"],
                    capture_output=True,
                    timeout=30,
                )
                # npx @package@latest --help
                subprocess.run(
                    ["npx", *args, "--help"],
                    capture_output=True,
                    timeout=30,
                )

            console.print(f"[green]✓[/] {sname}")
        except Exception as e:
            console.print(f"[red]✗[/] {sname}: {e}")

    console.print("[green]✅ Done![/]")


@app.command("health", help="Check server health")
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
        cmd = [server["command"], *server["args"], "--help"]
        try:
            result = subprocess.run(
                cmd, capture_output=True, timeout=10
            )
            if result.returncode == 0:
                console.print(f"[green]✓[/] {sname}: OK")
            else:
                console.print(f"[red]✗[/] {sname}: ERROR (exit code {result.returncode})")
        except Exception as e:
            console.print(f"[red]✗[/] {sname}: ERROR ({e})")


@app.command("show", help="Show server details")
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


@app.command("backup", help="Backup configuration")
def backup_config(
    list_backups: bool = typer.Option(False, "-l", "--list", help="List backups"),
    restore: Optional[str] = typer.Option(None, "-r", "--restore", help="Restore backup"),
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
                console.print(f"  {i}. {timestamp}.json ({dt.strftime('%Y-%m-%d %H:%M:%S')})")
            except:
                console.print(f"  {i}. {backup.name}")
        return

    if restore:
        backup_file = BACKUP_DIR / f"{restore}.json" if not restore.endswith(".json") else BACKUP_DIR / restore
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


if __name__ == "__main__":
    app()
