"""Template system for common MCP server configurations."""

import json
from pathlib import Path
from typing import Optional

from pydantic import ValidationError as PydanticValidationError

from mcp_manager.config import ConfigManager
from mcp_manager.exceptions import MCPManagerError
from mcp_manager.models import MCPServer, Scope


class TemplateNotFoundError(MCPManagerError):
    """Template not found error."""

    pass


class TemplateCorruptedError(MCPManagerError):
    """Template file is corrupted."""

    pass


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
            # Default to templates/ directory inside package
            self.template_dir = Path(__file__).parent / "templates"

    def list_templates(self) -> dict[str, dict]:
        """List available templates.

        Returns:
            Dictionary of template name to template metadata
        """
        templates: dict[str, dict] = {}

        if not self.template_dir.exists():
            return templates

        for template_file in self.template_dir.glob("*.json"):
            try:
                data = json.loads(template_file.read_text(encoding="utf-8"))
                name = template_file.stem
                templates[name] = {
                    "name": data.get("name", name),
                    "description": data.get("description", ""),
                    "author": data.get("author", ""),
                    "category": data.get("category", ""),
                    "notes": data.get("notes", ""),
                }
            except (json.JSONDecodeError, OSError):
                # Skip corrupted or unreadable templates
                continue

        return templates

    def get_template(self, name: str) -> MCPServer:
        """Get template by name.

        Args:
            name: Template name

        Returns:
            Server configuration from template

        Raises:
            TemplateNotFoundError: Template not found
            TemplateCorruptedError: Template file is corrupted
        """
        template_path = self.template_dir / f"{name}.json"

        if not template_path.exists():
            raise TemplateNotFoundError(
                f"Template '{name}' not found",
                details={"template": name, "path": str(template_path)},
            )

        try:
            data = json.loads(template_path.read_text(encoding="utf-8"))
            server_data = data.get("server")

            if not server_data:
                raise TemplateCorruptedError(
                    f"Template '{name}' missing 'server' field",
                    details={"template": name},
                )

            # Create MCPServer from template data
            server = MCPServer.model_validate(server_data)
            return server

        except json.JSONDecodeError as e:
            raise TemplateCorruptedError(
                f"Template '{name}' has invalid JSON: {e}",
                details={"template": name, "error": str(e)},
            ) from e
        except PydanticValidationError as e:
            raise TemplateCorruptedError(
                f"Template '{name}' has invalid schema: {e}",
                details={"template": name, "error": str(e)},
            ) from e
        except OSError as e:
            raise TemplateCorruptedError(
                f"Failed to read template '{name}': {e}",
                details={"template": name, "error": str(e)},
            ) from e

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

        Raises:
            TemplateNotFoundError: Template not found
            TemplateCorruptedError: Template file is corrupted
            ServerAlreadyExistsError: Server already exists
            ValidationError: Invalid server name
        """
        # Get template
        server = self.get_template(template_name)

        # Use template name if no custom name provided
        name = server_name or template_name

        # Install via ConfigManager
        manager = ConfigManager(scope=scope)
        manager.add_server(name, server)

        return server
