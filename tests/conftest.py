"""Pytest configuration and fixtures."""

import json
from pathlib import Path

import pytest


@pytest.fixture
def valid_config_data():
    """Valid config JSON data."""
    return {
        "mcpServers": {
            "time": {
                "type": "stdio",
                "command": "uvx",
                "args": ["mcp-server-time"],
                "env": {},
            },
            "fetch": {
                "type": "stdio",
                "command": "uvx",
                "args": ["mcp-server-fetch"],
                "env": {},
            },
        }
    }


@pytest.fixture
def corrupted_config_data():
    """Corrupted JSON data."""
    return "{invalid json syntax"


@pytest.fixture
def mock_claude_home(tmp_path, monkeypatch):
    """Mock home directory for testing."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def temp_config(tmp_path):
    """Create temporary config file."""
    config_path = tmp_path / "config.json"
    config_data = {
        "mcpServers": {
            "existing": {
                "type": "stdio",
                "command": "uvx",
                "args": ["mcp-server-time"],
                "env": {},
            }
        }
    }
    config_path.write_text(json.dumps(config_data, indent=2))
    return config_path
