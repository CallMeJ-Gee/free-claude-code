"""Utility functions for managing .env file."""

import os
import re
from pathlib import Path
from typing import Any


def read_env_file(env_path: Path = None) -> dict[str, str]:
    """Read .env file and return as dictionary."""
    if env_path is None:
        env_path = Path(".env")

    env_vars = {}
    if not env_path.exists():
        return env_vars

    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            # Parse KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                env_vars[key] = value

    return env_vars


def write_env_file(env_vars: dict[str, str], env_path: Path = None) -> None:
    """Write dictionary to .env file, preserving comments and structure."""
    if env_path is None:
        env_path = Path(".env")

    if not env_path.exists():
        # Create new .env file
        with open(env_path, 'w') as f:
            for key, value in env_vars.items():
                f.write(f'{key}="{value}"\n')
        return

    # Read existing file to preserve structure
    lines = []
    with open(env_path, 'r') as f:
        lines = f.readlines()

    # Update values while preserving structure
    updated_lines = []
    seen_keys = set()

    for line in lines:
        stripped = line.strip()
        # Preserve empty lines and comments
        if not stripped or stripped.startswith('#'):
            updated_lines.append(line)
            continue

        # Parse and update KEY=VALUE
        if '=' in stripped:
            key, _ = stripped.split('=', 1)
            key = key.strip()
            if key in env_vars:
                # Update existing key - preserve original format
                value = env_vars[key]
                # Check if original line had quotes by looking at the value part
                _, original_value = stripped.split('=', 1)
                original_value = original_value.strip()
                if (original_value.startswith('"') and original_value.endswith('"')) or \
                   (original_value.startswith("'") and original_value.endswith("'")):
                    # Original had quotes, preserve format
                    updated_lines.append(f'{key}="{value}"\n')
                else:
                    # Original didn't have quotes
                    updated_lines.append(f'{key}={value}\n')
                seen_keys.add(key)
            else:
                # Keep existing line
                updated_lines.append(line)
        else:
            # Keep lines without =
            updated_lines.append(line)

    # Add new keys at the end
    for key, value in env_vars.items():
        if key not in seen_keys:
            updated_lines.append(f'{key}="{value}"\n')

    # Write back
    with open(env_path, 'w') as f:
        f.writelines(updated_lines)


def update_env_var(key: str, value: Any, env_path: Path = None) -> None:
    """Update a single environment variable in .env file."""
    env_vars = read_env_file(env_path)
    env_vars[key] = str(value)
    write_env_file(env_vars, env_path)


def delete_env_var(key: str, env_path: Path = None) -> None:
    """Delete a single environment variable from .env file."""
    env_vars = read_env_file(env_path)
    if key in env_vars:
        del env_vars[key]
        write_env_file(env_vars, env_path)


def reload_settings() -> None:
    """Reload settings by clearing the cached settings instance."""
    # Import here to avoid circular dependency
    from config.settings import get_settings

    # Clear the lru_cache
    if hasattr(get_settings, 'cache_clear'):
        get_settings.cache_clear()
