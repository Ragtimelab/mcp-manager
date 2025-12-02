"""Template system for common MCP server configurations."""

# TODO: Implement template management

from pathlib import Path
from typing import Optional

from mcp_manager.models import MCPServer, Scope


class TemplateManager:
    """Manage MCP server templates."""

    def __init__(self, template_dir: Optional[Path] = None):
        """Initialize template manager.

        Args:
            template_dir: Directory containing templates
        """
        if template_dir:
            self.template_dir = template_dir
        else:
            # Default to templates/ directory next to package
            self.template_dir = Path(__file__).parent.parent.parent / "templates"

    def list_templates(self) -> dict[str, dict]:
        """List available templates.

        Returns:
            Dictionary of template name to template metadata
        """
        # TODO: Implement
        return {}

    def get_template(self, name: str) -> MCPServer:
        """Get template by name.

        Args:
            name: Template name

        Returns:
            Server configuration from template
        """
        # TODO: Implement
        raise NotImplementedError

    def install_template(
        self,
        template_name: str,
        server_name: Optional[str] = None,
        scope: Scope = Scope.USER,
    ) -> MCPServer:
        """Install template as server.

        Args:
            template_name: Template to install
            server_name: Custom server name (uses template name if None)
            scope: Configuration scope

        Returns:
            Installed server configuration
        """
        # TODO: Implement
        raise NotImplementedError
