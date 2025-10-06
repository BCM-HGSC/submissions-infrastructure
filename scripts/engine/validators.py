"""
Validation functions for environment definitions and configuration files.
"""

from pathlib import Path
from typing import Any

import yaml


class ValidationError(Exception):
    """Exception raised when validation fails."""


def validate_env_yaml(path: Path) -> bool:
    """
    Validate a conda environment YAML file.

    Args:
        path: Path to the YAML file to validate

    Returns:
        True if validation passes

    Raises:
        ValidationError: If validation fails with details about what failed
    """
    # Check file exists
    if not path.exists():
        raise ValidationError(f"File does not exist: {path}")

    # Check file is readable
    if not path.is_file():
        raise ValidationError(f"Path is not a file: {path}")

    try:
        # Read and parse YAML
        with path.open("r") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValidationError(f"Invalid YAML syntax in {path}: {e}") from e
    except OSError as e:
        raise ValidationError(f"Cannot read file {path}: {e}") from e

    # Validate data is a dictionary
    if not isinstance(data, dict):
        raise ValidationError(
            f"Expected YAML to contain a dictionary, got {type(data).__name__}"
        )

    # Validate required keys
    _validate_required_keys(data, path)

    # Validate channels
    _validate_channels(data["channels"], path)

    # Validate dependencies
    _validate_dependencies(data["dependencies"], path)

    return True


def _validate_required_keys(data: dict[str, Any], path: Path) -> None:
    """Validate that required keys are present."""
    required_keys = {"channels", "dependencies"}
    missing = required_keys - set(data.keys())
    if missing:
        raise ValidationError(
            f"Missing required keys in {path}: {', '.join(sorted(missing))}"
        )


def _validate_channels(channels: Any, path: Path) -> None:
    """Validate the channels field."""
    if not isinstance(channels, list):
        raise ValidationError(
            f"'channels' must be a list in {path}, got {type(channels).__name__}"
        )

    if not channels:
        raise ValidationError(f"'channels' list cannot be empty in {path}")

    for i, channel in enumerate(channels):
        if not isinstance(channel, str):
            raise ValidationError(
                f"Channel at index {i} must be a string in {path}, got {type(channel).__name__}"
            )
        if not channel.strip():
            raise ValidationError(f"Channel at index {i} cannot be empty in {path}")

        # Validate channel name format (basic validation)
        _validate_channel_name(channel, i, path)


def _validate_channel_name(channel: str, index: int, path: Path) -> None:
    """Validate channel name format."""
    # Common conda channels
    valid_channels = {
        "conda-forge",
        "bioconda",
        "defaults",
        "anaconda",
        "r",
        "pytorch",
        "nvidia",
    }

    # Allow common channel patterns
    # 1. Standard channel names
    # 2. URLs (http://, https://, file://)
    # 3. Channel aliases with namespace (e.g., "conda-forge/label/main")

    if channel in valid_channels:
        return

    if channel.startswith(("http://", "https://", "file://")):
        return

    if "/" in channel:
        # Format: channel/label or user/channel
        parts = channel.split("/")
        if len(parts) >= 2 and all(part.strip() for part in parts):
            return

    # Warn about potentially invalid channels, but don't fail
    # (conda will fail later if the channel is truly invalid)
    # Only fail on obviously malformed input
    if any(c in channel for c in [" ", "\n", "\t", "\r"]):
        raise ValidationError(
            f"Channel at index {index} contains invalid whitespace in {path}: {channel!r}"
        )


def _validate_dependencies(dependencies: Any, path: Path) -> None:
    """Validate the dependencies field."""
    if not isinstance(dependencies, list):
        raise ValidationError(
            f"'dependencies' must be a list in {path}, got {type(dependencies).__name__}"
        )

    if not dependencies:
        raise ValidationError(f"'dependencies' list cannot be empty in {path}")

    for i, dep in enumerate(dependencies):
        if isinstance(dep, str):
            _validate_string_dependency(dep, i, path)
        elif isinstance(dep, dict):
            _validate_dict_dependency(dep, i, path)
        else:
            raise ValidationError(
                f"Dependency at index {i} must be a string or dict in {path}, got {type(dep).__name__}"
            )


def _validate_string_dependency(dep: str, index: int, path: Path) -> None:
    """Validate a string dependency format."""
    if not dep.strip():
        raise ValidationError(f"Dependency at index {index} cannot be empty in {path}")

    # Basic format validation
    # Valid formats:
    # - package
    # - package=version
    # - package>=version
    # - package~=version
    # - package<version, package<=version, package!=version
    # - channel::package
    # - channel::package=version

    # Check for obviously invalid characters
    invalid_chars = ["\n", "\r", "\t"]
    for char in invalid_chars:
        if char in dep:
            raise ValidationError(
                f"Dependency at index {index} contains invalid character {char!r} in {path}: {dep!r}"
            )


def _validate_dict_dependency(dep: dict[str, Any], index: int, path: Path) -> None:
    """Validate a dictionary dependency (e.g., pip dependencies)."""
    # Most common case: {"pip": ["package1", "package2"]}
    if "pip" in dep:
        pip_deps = dep["pip"]
        if not isinstance(pip_deps, list):
            raise ValidationError(
                f"Dependency at index {index}: 'pip' value must be a list in {path}, got {type(pip_deps).__name__}"
            )
        for j, pip_dep in enumerate(pip_deps):
            if not isinstance(pip_dep, str):
                raise ValidationError(
                    f"Dependency at index {index}: pip dependency at index {j} must be a string in {path}, got {type(pip_dep).__name__}"
                )
            if not pip_dep.strip():
                raise ValidationError(
                    f"Dependency at index {index}: pip dependency at index {j} cannot be empty in {path}"
                )
    else:
        # Unknown dict format - allow but could warn
        pass
