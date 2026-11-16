"""
Validation functions for environment definitions and configuration files.
"""

import os
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


class DiskSpaceError(Exception):
    """Exception raised when insufficient disk space is available."""


def get_available_space_gb(path: Path) -> float:
    """
    Get available disk space in gigabytes for a given path.

    Args:
        path: Path to check disk space for (will check parent if path doesn't exist)

    Returns:
        Available space in GB as a float
    """
    # Use the directory if it exists, otherwise use parent directory
    check_path = path if path.is_dir() else path.parent

    # Ensure the path exists
    if not check_path.exists():
        check_path = check_path.parent

    # Get filesystem statistics
    stat = os.statvfs(check_path)
    # Calculate available space: available blocks * block size / 1GB
    available_bytes = stat.f_bavail * stat.f_frsize
    return available_bytes / (1024**3)


def estimate_env_size_gb(yaml_path: Path) -> float:
    """
    Estimate conda environment size based on package count.

    This is a heuristic estimate. Actual size depends on:
    - Transitive dependencies (typically 3-5x direct deps)
    - Package sizes (vary greatly)
    - Platform-specific binaries

    Args:
        yaml_path: Path to the environment YAML file

    Returns:
        Estimated size in GB
    """
    try:
        with yaml_path.open("r") as f:
            env_def = yaml.safe_load(f)
    except (OSError, yaml.YAMLError):
        # If we can't read the file, return a conservative estimate
        return 2.0

    # Count direct dependencies
    pkg_count = len(env_def.get("dependencies", []))

    # Account for pip dependencies
    for dep in env_def.get("dependencies", []):
        if isinstance(dep, dict) and "pip" in dep:
            pkg_count += len(dep["pip"])

    # Rough estimate: 50MB per package (includes transitive deps)
    estimated_gb = (pkg_count * 50) / 1024  # MB to GB

    # Add 50% buffer for transitive dependencies
    return estimated_gb * 1.5


def check_disk_space(
    path: Path,
    operation: str = "deploy",
    env_yamls: list[Path] | None = None,
    force: bool = False,
) -> tuple[bool, str]:
    """
    Check available disk space using hybrid static/dynamic estimation.

    Uses conservative static thresholds combined with YAML-based estimation
    to provide both safety and helpful feedback.

    Thresholds based on empirical data (~21GB full system):
    - bootstrap: 5 GB minimum
    - deploy: 15 GB minimum, 30 GB recommended

    Args:
        path: Path to check disk space for
        operation: Type of operation ('bootstrap' or 'deploy')
        env_yamls: Optional list of YAML files to estimate size from
        force: If True, bypass hard minimum check (still warn)

    Returns:
        Tuple of (success: bool, message: str)
        - success is False only if below hard minimum and not force
        - message is empty if plenty of space, otherwise contains warning/error

    Raises:
        DiskSpaceError: If insufficient space and force=False
    """
    # Get actual available space
    available_gb = get_available_space_gb(path)

    # Static thresholds
    thresholds = {
        "bootstrap": (5, 10),  # (minimum, recommended)
        "deploy": (15, 30),
    }

    minimum_gb, recommended_gb = thresholds.get(operation, (10, 20))

    # Dynamic estimate based on YAMLs
    estimated_need = 0.0
    if env_yamls:
        for yaml_path in env_yamls:
            estimated_need += estimate_env_size_gb(yaml_path)
        # Add buffer for cache and overhead
        estimated_need += 10

    # Determine severity
    if available_gb < minimum_gb:
        error_msg = (
            f"Insufficient disk space for {operation}\n"
            f"Available: {available_gb:.1f}GB\n"
            f"Required: {minimum_gb}GB minimum\n"
        )
        if force:
            error_msg += "WARNING: Proceeding anyway due to --skip-disk-check"
            return True, error_msg
        error_msg += f"{operation.capitalize()} requires at least {minimum_gb}GB of free space.\nUse --skip-disk-check to override."
        raise DiskSpaceError(error_msg)

    if env_yamls and available_gb < estimated_need:
        warning_msg = (
            f"WARNING: Disk space may be tight for {operation}\n"
            f"Available: {available_gb:.1f}GB\n"
            f"Estimated need: ~{estimated_need:.1f}GB\n"
            f"Operation may fail if estimate is accurate."
        )
        return True, warning_msg

    if available_gb < recommended_gb:
        info_msg = (
            f"INFO: {available_gb:.1f}GB available. "
            f"{recommended_gb}GB recommended for comfortable {operation}."
        )
        return True, info_msg

    # Plenty of space
    return True, ""


class PathTraversalError(Exception):
    """Exception raised when path traversal attack is detected."""


def validate_safe_path(path: Path, base: Path) -> bool:
    """
    Validate that a path is safely within a base directory.

    This function protects against path traversal attacks by ensuring that
    the given path, after resolving symlinks and normalizing, is actually
    within the expected base directory.

    Args:
        path: Path to validate (may be relative or absolute)
        base: Base directory that path must be within

    Returns:
        True if validation passes

    Raises:
        PathTraversalError: If path escapes the base directory

    Examples:
        >>> validate_safe_path(Path("/tmp/foo/bar"), Path("/tmp"))
        True
        >>> validate_safe_path(Path("/tmp/foo/../../../etc/passwd"), Path("/tmp"))
        PathTraversalError: Path traversal detected...
    """
    try:
        # Resolve both paths to absolute, canonical forms
        # This handles symlinks, .., ., and makes paths absolute
        resolved_path = path.resolve()
        resolved_base = base.resolve()
    except (OSError, RuntimeError) as e:
        # OSError: permission denied, path doesn't exist, etc.
        # RuntimeError: infinite loop in symlinks
        raise PathTraversalError(
            f"Cannot resolve path {path} relative to base {base}: {e}"
        ) from e

    if not resolved_path.is_relative_to(resolved_base):
        raise PathTraversalError(
            f"Path traversal detected: {path} resolves to {resolved_path}, "
            f"which is outside base directory {base} (resolved to {resolved_base})"
        )
    return True
