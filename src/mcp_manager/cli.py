"""Command-line interface for MCP Manager."""

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from mcp_manager import __version__
from mcp_manager.backup import BackupManager
from mcp_manager.config import ConfigManager
from mcp_manager.health import HealthChecker
from mcp_manager.models import MCPServer, MCPServerType, Scope
from mcp_manager.templates import TemplateManager
from mcp_manager.validators import validate_server_name

app = typer.Typer(
    name="mcpm",
    help="[bold cyan]MCP Manager[/] - Manage Model Context Protocol servers",
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"[bold cyan]MCP Manager[/] version [green]{__version__}[/]")
        raise typer.Exit()


@app.callback()
def callback(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Enable verbose output",
    ),
) -> None:
    """
    [bold cyan]MCP Manager[/] - Manage Model Context Protocol servers for Claude Code.

    Manage MCP servers across different scopes (user, project, local) with
    features like backup/restore, validation, and health checks.
    """
    if verbose:
        console.print("[dim]Verbose mode enabled[/]")


# ============================================================================
# Server Management Commands
# ============================================================================


@app.command(name="list", rich_help_panel="Server Management")
def list_servers(
    scope: Optional[Scope] = typer.Option(
        None,
        "--scope",
        "-s",
        help="Filter by scope (user/project/local)",
    ),
    server_type: Optional[MCPServerType] = typer.Option(
        None,
        "--type",
        "-t",
        help="Filter by server type (stdio/http/sse)",
    ),
    format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format (table/json)",
    ),
) -> None:
    """
    [green]List[/] all MCP servers.

    Display servers from the specified scope or all scopes.
    Output can be formatted as table or JSON.
    """
    try:
        # Determine scope(s) to check
        scopes = [scope] if scope else [Scope.USER, Scope.PROJECT, Scope.LOCAL]

        all_servers = {}
        for s in scopes:
            try:
                manager = ConfigManager(scope=s)
                servers = manager.list_servers(server_type=server_type)
                for name, server in servers.items():
                    # Add scope info to server name for display
                    display_name = f"{name} ({s.value})"
                    all_servers[display_name] = (server, s)
            except Exception:
                # Skip scopes that don't have configs
                continue

        if not all_servers:
            console.print("[yellow]No servers found[/]")
            return

        if format == "json":
            import json

            # Convert to JSON-serializable format
            json_output = {}
            for display_name, (server, s) in all_servers.items():
                name = display_name.rsplit(" (", 1)[0]
                json_output[name] = {
                    "scope": s.value,
                    **server.model_dump(mode="json"),
                }
            console.print(json.dumps(json_output, indent=2))
        else:
            # Table format
            table = Table(title="[bold cyan]MCP Servers[/]", show_header=True)
            table.add_column("Name", style="cyan", no_wrap=True)
            table.add_column("Type", style="magenta")
            table.add_column("Command/URL", style="green")
            table.add_column("Scope", style="blue")

            for display_name, (server, s) in sorted(all_servers.items()):
                name = display_name.rsplit(" (", 1)[0]
                if server.type == MCPServerType.STDIO:
                    cmd_url = f"{server.command} {' '.join(server.args[:2])}"
                    if len(server.args) > 2:
                        cmd_url += "..."
                else:
                    cmd_url = server.url or ""

                # Get type value (handle both enum and string)
                type_value = (
                    server.type.value
                    if isinstance(server.type, MCPServerType)
                    else str(server.type)
                )
                scope_value = s.value if isinstance(s, Scope) else str(s)

                table.add_row(name, type_value, cmd_url, scope_value)

            console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)


@app.command(rich_help_panel="Server Management")
def show(
    name: str = typer.Argument(..., help="Server name"),
    scope: Scope = typer.Option(
        Scope.USER,
        "--scope",
        "-s",
        help="Configuration scope",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Show all details including environment variables",
    ),
) -> None:
    """
    [green]Show[/] detailed information about a server.

    Display complete configuration for a specific MCP server.
    """
    try:
        manager = ConfigManager(scope=scope)
        server = manager.get_server(name)

        if not server:
            console.print(f"[red]Error:[/] Server '{name}' not found in {scope.value} scope")
            raise typer.Exit(1)

        # Display server details
        console.print(f"\n[bold cyan]Server:[/] {name}")
        # Get type value (handle both enum and string)
        type_value = (
            server.type.value if isinstance(server.type, MCPServerType) else str(server.type)
        )
        console.print(f"[bold]Type:[/] {type_value}")

        if server.type == MCPServerType.STDIO:
            console.print(f"[bold]Command:[/] {server.command}")
            if server.args:
                console.print("[bold]Arguments:[/]")
                for arg in server.args:
                    console.print(f"  - {arg}")
            if verbose and server.env:
                console.print("[bold]Environment:[/]")
                for key, value in server.env.items():
                    console.print(f"  {key}={value}")
        else:
            console.print(f"[bold]URL:[/] {server.url}")
            if verbose and server.headers:
                console.print("[bold]Headers:[/]")
                for key, value in server.headers.items():
                    # Mask sensitive headers
                    if any(x in key.lower() for x in ["auth", "token", "key"]):
                        value = "***"
                    console.print(f"  {key}: {value}")

        console.print(f"[bold]Scope:[/] {scope.value}\n")

    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)


@app.command(rich_help_panel="Server Management")
def add(
    name: str = typer.Argument(..., help="Server name"),
    server_type: Optional[MCPServerType] = typer.Option(
        None,
        "--type",
        "-t",
        help="Server type (stdio/http/sse)",
    ),
    command: Optional[str] = typer.Option(
        None,
        "--command",
        "-c",
        help="Command to run (for stdio)",
    ),
    args: Optional[list[str]] = typer.Option(
        None,
        "--args",
        "-a",
        help="Command arguments (for stdio)",
    ),
    url: Optional[str] = typer.Option(
        None,
        "--url",
        "-u",
        help="Server URL (for http/sse)",
    ),
    env: Optional[list[str]] = typer.Option(
        None,
        "--env",
        "-e",
        help="Environment variable (KEY=VALUE)",
    ),
    scope: Scope = typer.Option(
        Scope.USER,
        "--scope",
        "-s",
        help="Configuration scope",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Interactive mode",
    ),
) -> None:
    """
    [green]Add[/] a new MCP server.

    Add a server with specified configuration. Use --interactive for
    step-by-step guided setup.
    """
    try:
        # Validate server name
        validate_server_name(name)

        # Interactive mode
        if interactive:
            console.print("[bold cyan]Interactive Server Setup[/]\n")

            if not server_type:
                console.print("[bold]Select server type:[/]")
                console.print("  1. stdio (local command)")
                console.print("  2. http (remote HTTP)")
                console.print("  3. sse (Server-Sent Events)")
                choice = typer.prompt("Choice", type=int)
                server_type = {1: MCPServerType.STDIO, 2: MCPServerType.HTTP, 3: MCPServerType.SSE}[
                    choice
                ]

            if server_type == MCPServerType.STDIO:
                if not command:
                    command = typer.prompt("Command")
                if not args:
                    args_str = typer.prompt("Arguments (space-separated)", default="")
                    args = args_str.split() if args_str else []
            else:
                if not url:
                    url = typer.prompt("URL")

        # Validate required fields
        if server_type == MCPServerType.STDIO and not command:
            console.print("[red]Error:[/] --command is required for stdio servers")
            raise typer.Exit(1)

        if server_type in (MCPServerType.HTTP, MCPServerType.SSE) and not url:
            console.print("[red]Error:[/] --url is required for http/sse servers")
            raise typer.Exit(1)

        # Parse environment variables
        env_dict: dict[str, str] = {}
        if env:
            for env_var in env:
                if "=" not in env_var:
                    console.print(f"[red]Error:[/] Invalid env format: {env_var} (use KEY=VALUE)")
                    raise typer.Exit(1)
                key, value = env_var.split("=", 1)
                env_dict[key] = value

        # Create server object
        # Type assertion: server_type is guaranteed to be non-None by validation above
        assert server_type is not None, "server_type must be set"

        if server_type == MCPServerType.STDIO:
            server = MCPServer(
                type=server_type,
                command=command,
                args=args or [],
                env=env_dict,
            )
        else:
            server = MCPServer(
                type=server_type,
                url=url,
                headers=env_dict,
            )

        # Add to config
        manager = ConfigManager(scope=scope)
        manager.add_server(name, server)

        console.print(f"[green]✓[/] Server '[cyan]{name}[/]' added to {scope.value} scope")

    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)


@app.command(rich_help_panel="Server Management")
def remove(
    name: str = typer.Argument(..., help="Server name"),
    scope: Scope = typer.Option(
        Scope.USER,
        "--scope",
        "-s",
        help="Configuration scope",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation",
    ),
) -> None:
    """
    [red]Remove[/] an MCP server.

    Delete a server from the specified scope. Requires confirmation
    unless --force is specified.
    """
    try:
        manager = ConfigManager(scope=scope)

        # Check if server exists
        server = manager.get_server(name)
        if not server:
            console.print(f"[red]Error:[/] Server '{name}' not found in {scope.value} scope")
            raise typer.Exit(1)

        # Confirm deletion
        if not force:
            confirm = typer.confirm(f"Remove server '{name}' from {scope.value} scope?")
            if not confirm:
                console.print("[yellow]Cancelled[/]")
                return

        # Remove server
        manager.remove_server(name)
        console.print(f"[green]✓[/] Server '[cyan]{name}[/]' removed from {scope.value} scope")

    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)


# ============================================================================
# Backup Commands
# ============================================================================

backup_app = typer.Typer(
    help="[bold]Backup[/] management commands",
    rich_markup_mode="rich",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
app.add_typer(backup_app, name="backup", rich_help_panel="Backup & Restore")


@backup_app.command("create")
def backup_create(
    scope: Scope = typer.Option(
        Scope.USER,
        "--scope",
        "-s",
        help="Configuration scope to backup",
    ),
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Backup name/reason",
    ),
) -> None:
    """
    [green]Create[/] a configuration backup.

    Save current configuration to backup directory.
    """
    try:
        manager = ConfigManager(scope=scope)
        config = manager.load()

        backup_manager = BackupManager()
        backup = backup_manager.create(config, reason=name)

        console.print(f"[green]✓[/] Backup created: [cyan]{backup.backup_id}[/]")
        if name:
            console.print(f"  Reason: {name}")

    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)


@backup_app.command("list")
def backup_list(
    limit: int = typer.Option(
        10,
        "--limit",
        "-l",
        help="Number of backups to show",
    ),
) -> None:
    """
    [green]List[/] available backups.

    Display recent backups with timestamps.
    """
    try:
        backup_manager = BackupManager()
        backups = backup_manager.list(limit=limit)

        if not backups:
            console.print("[yellow]No backups found[/]")
            return

        table = Table(title="[bold cyan]Backups[/]", show_header=True)
        table.add_column("ID", style="cyan")
        table.add_column("Timestamp", style="green")
        table.add_column("Servers", style="magenta")
        table.add_column("Reason", style="yellow")

        for backup in backups:
            reason = backup.metadata.get("reason", "-")
            server_count = len(backup.config.mcpServers)
            table.add_row(
                backup.backup_id,
                backup.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                str(server_count),
                reason,
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)


@backup_app.command("restore")
def backup_restore(
    backup_id: str = typer.Argument(..., help="Backup ID to restore"),
    scope: Scope = typer.Option(
        Scope.USER,
        "--scope",
        "-s",
        help="Configuration scope to restore to",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation",
    ),
) -> None:
    """
    [yellow]Restore[/] configuration from backup.

    Replace current configuration with backup. Creates automatic
    backup of current state before restoring.
    """
    try:
        # Confirm restore
        if not force:
            confirm = typer.confirm(
                f"Restore backup '{backup_id}' to {scope.value} scope?\n"
                "Current configuration will be backed up automatically."
            )
            if not confirm:
                console.print("[yellow]Cancelled[/]")
                return

        # Create backup of current state
        manager = ConfigManager(scope=scope)
        current_config = manager.load()

        backup_manager = BackupManager()
        auto_backup = backup_manager.create(current_config, reason="Auto-backup before restore")
        console.print(f"[dim]Current state backed up as: {auto_backup.backup_id}[/]")

        # Restore from backup
        restored_config = backup_manager.restore(backup_id)
        manager.save(restored_config)

        console.print(f"[green]✓[/] Backup '[cyan]{backup_id}[/]' restored to {scope.value} scope")

    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)


@backup_app.command("clean")
def backup_clean(
    keep: int = typer.Option(
        5,
        "--keep",
        "-k",
        help="Number of recent backups to keep",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation",
    ),
) -> None:
    """
    [red]Clean[/] old backups.

    Delete old backups, keeping only the most recent ones.
    """
    try:
        if not force:
            confirm = typer.confirm(f"Delete old backups, keeping {keep} most recent?")
            if not confirm:
                console.print("[yellow]Cancelled[/]")
                return

        backup_manager = BackupManager()
        deleted = backup_manager.cleanup(keep=keep)

        console.print(f"[green]✓[/] Deleted {deleted} old backup(s)")

    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)


# ============================================================================
# Templates Commands
# ============================================================================

templates_app = typer.Typer(
    help="[bold]Template[/] management commands",
    rich_markup_mode="rich",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
app.add_typer(templates_app, name="templates", rich_help_panel="Advanced Features")


@templates_app.command("list")
def templates_list() -> None:
    """
    [green]List[/] available server templates.

    Display all built-in MCP server templates with descriptions.
    """
    try:
        manager = TemplateManager()
        templates = manager.list_templates()

        if not templates:
            console.print("[yellow]No templates found[/]")
            return

        table = Table(title="[bold cyan]MCP Server Templates[/]", show_header=True)
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Description", style="green")
        table.add_column("Category", style="magenta")

        for name, info in sorted(templates.items()):
            table.add_row(
                name,
                info.get("description", ""),
                info.get("category", ""),
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)


@templates_app.command("show")
def templates_show(
    name: str = typer.Argument(..., help="Template name"),
) -> None:
    """
    [green]Show[/] template details.

    Display complete configuration for a specific template.
    """
    try:
        manager = TemplateManager()
        templates = manager.list_templates()

        if name not in templates:
            console.print(f"[red]Error:[/] Template '{name}' not found")
            raise typer.Exit(1)

        info = templates[name]
        server = manager.get_template(name)

        console.print(f"\n[bold cyan]Template:[/] {name}")
        console.print(f"[bold]Description:[/] {info.get('description', 'N/A')}")
        console.print(f"[bold]Category:[/] {info.get('category', 'N/A')}")
        console.print(f"[bold]Author:[/] {info.get('author', 'N/A')}")

        if info.get("notes"):
            console.print(f"[bold]Notes:[/] {info['notes']}")

        console.print("\n[bold]Configuration:[/]")
        # Get type value (handle both enum and string)
        type_value = (
            server.type.value if isinstance(server.type, MCPServerType) else str(server.type)
        )
        console.print(f"  Type: {type_value}")
        console.print(f"  Command: {server.command}")
        if server.args:
            console.print(f"  Args: {' '.join(server.args)}")
        if server.env:
            console.print(f"  Env: {server.env}")

        console.print()

    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)


@templates_app.command("install")
def templates_install(
    template_name: str = typer.Argument(..., help="Template name"),
    server_name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Custom server name (uses template name if not provided)",
    ),
    scope: Scope = typer.Option(
        Scope.USER,
        "--scope",
        "-s",
        help="Configuration scope",
    ),
) -> None:
    """
    [green]Install[/] template as server.

    Install a template configuration as an MCP server.
    """
    try:
        manager = TemplateManager()
        name = server_name or template_name

        manager.install_template(template_name, server_name=server_name, scope=scope)

        console.print(
            f"[green]✓[/] Template '[cyan]{template_name}[/]' installed as '[cyan]{name}[/]' in {scope.value} scope"
        )

    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)


# ============================================================================
# Health Check Commands
# ============================================================================


@app.command(rich_help_panel="Advanced Features")
def health(
    name: Optional[str] = typer.Argument(
        None,
        help="Server name (checks all servers if not provided)",
    ),
    scope: Scope = typer.Option(
        Scope.USER,
        "--scope",
        "-s",
        help="Configuration scope",
    ),
) -> None:
    """
    [green]Check[/] server health.

    Verify that MCP servers are properly configured and accessible.
    """
    try:
        manager = ConfigManager(scope=scope)
        checker = HealthChecker()

        if name:
            # Check single server
            server = manager.get_server(name)
            if not server:
                console.print(f"[red]Error:[/] Server '{name}' not found")
                raise typer.Exit(1)

            status = checker.check(server)
            status_color = (
                "green"
                if status.value == "healthy"
                else "red"
                if status.value == "unhealthy"
                else "yellow"
            )

            console.print(
                f"[bold]{name}:[/] [{status_color}]{status.value.upper()}[/{status_color}]"
            )
        else:
            # Check all servers
            servers = manager.list_servers()

            if not servers:
                console.print("[yellow]No servers found[/]")
                return

            table = Table(title="[bold cyan]Server Health[/]", show_header=True)
            table.add_column("Server", style="cyan")
            table.add_column("Type", style="magenta")
            table.add_column("Status", style="bold")

            for server_name, server in sorted(servers.items()):
                status = checker.check(server)
                status_color = (
                    "green"
                    if status.value == "healthy"
                    else "red"
                    if status.value == "unhealthy"
                    else "yellow"
                )

                # Get type value (handle both enum and string)
                type_value = (
                    server.type.value
                    if isinstance(server.type, MCPServerType)
                    else str(server.type)
                )

                table.add_row(
                    server_name,
                    type_value,
                    f"[{status_color}]{status.value.upper()}[/{status_color}]",
                )

            console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)


# ============================================================================
# Entry Point
# ============================================================================


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
