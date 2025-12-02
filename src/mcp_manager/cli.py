"""Command-line interface for MCP Manager."""

# TODO: Implement CLI commands using Typer and Rich
# This is the main entry point for the CLI application

from typing import Optional

import typer
from rich.console import Console

app = typer.Typer(
    name="mcpm",
    help="MCP Manager - Manage Model Context Protocol servers",
    add_completion=False,
)
console = Console()


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
