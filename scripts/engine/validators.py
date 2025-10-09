"""
Validation functions for environment definitions and configuration files.
"""

import os
from pathlib import Path
import shutil
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


class BinaryNotFoundError(Exception):
    """Exception raised when a required binary is not found."""


def check_binary_available(
    binary_name: str, search_paths: list[str] | None = None
) -> Path | None:
    """
    Check if a binary is available in the system PATH or specified paths.

    Args:
        binary_name: Name of the binary to check for
        search_paths: Optional list of specific paths to check (e.g., ["/usr/bin", "/bin"])

    Returns:
        Path to the binary if found, None otherwise
    """
    if search_paths:
        # Check specific paths first
        for search_path in search_paths:
            binary_path = Path(search_path) / binary_name
            if binary_path.exists() and binary_path.is_file():
                return binary_path

    # Check system PATH
    binary_path = shutil.which(binary_name)
    return Path(binary_path) if binary_path else None


def check_required_binaries(
    binaries: list[str],
    search_paths: dict[str, list[str]] | None = None,
    optional: list[str] | None = None,
) -> dict[str, Path | None]:
    """
    Check for required binaries and return their paths.

    Args:
        binaries: List of binary names to check for
        search_paths: Optional dict mapping binary names to specific search paths
        optional: List of binary names that are optional (won't raise error if missing)

    Returns:
        Dictionary mapping binary names to their paths (or None if not found)

    Raises:
        BinaryNotFoundError: If a required binary is not found
    """
    search_paths = search_paths or {}
    optional = optional or []
    results = {}
    missing_required = []

    for binary in binaries:
        specific_paths = search_paths.get(binary)
        binary_path = check_binary_available(binary, specific_paths)
        results[binary] = binary_path

        if binary_path is None and binary not in optional:
            missing_required.append(binary)

    if missing_required:
        error_msg = _format_missing_binaries_error(missing_required)
        raise BinaryNotFoundError(error_msg)

    return results


def _format_missing_binaries_error(missing_binaries: list[str]) -> str:
    """Format a helpful error message for missing binaries."""
    lines = ["Required binaries not found:", ""]

    for binary in missing_binaries:
        lines.append(f"  - {binary}")

        # Add installation instructions
        if binary == "curl":
            lines.append("    Install with: apt-get install curl (Debian/Ubuntu)")
            lines.append("                  yum install curl (RHEL/CentOS)")
            lines.append("                  brew install curl (macOS)")
        elif binary == "git":
            lines.append("    Install with: apt-get install git (Debian/Ubuntu)")
            lines.append("                  yum install git (RHEL/CentOS)")
            lines.append("                  brew install git (macOS)")
        elif binary == "tar":
            lines.append("    Usually pre-installed on Unix systems")
            lines.append("    Install with: apt-get install tar (Debian/Ubuntu)")
            lines.append("                  yum install tar (RHEL/CentOS)")
        elif binary in ("mamba", "micromamba"):
            lines.append("    Mamba should be installed via bootstrap process")
            lines.append("    See: https://mamba.readthedocs.io/")

        lines.append("")

    return "\n".join(lines)


def check_bootstrap_binaries() -> dict[str, Path | None]:
    """
    Check for binaries required during bootstrap process.

    Returns:
        Dictionary mapping binary names to their paths

    Raises:
        BinaryNotFoundError: If required binaries are not found
    """
    # These are the binaries used by fetch-micromamba script
    return check_required_binaries(
        binaries=["curl", "tar"],
        search_paths={
            "curl": ["/usr/bin"],
            "tar": ["/usr/bin"],
        },
    )


def check_deploy_binaries(require_git: bool = True) -> dict[str, Path | None]:
    """
    Check for binaries required during deployment process.

    Args:
        require_git: Whether git is required (default True)

    Returns:
        Dictionary mapping binary names to their paths

    Raises:
        BinaryNotFoundError: If required binaries are not found
    """
    binaries = ["git"]
    optional = [] if require_git else ["git"]

    return check_required_binaries(
        binaries=binaries,
        optional=optional,
    )


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
            error_msg += "WARNING: Proceeding anyway due to --force flag"
            return True, error_msg
        error_msg += f"{operation.capitalize()} requires at least {minimum_gb}GB of free space.\nUse --force to override."
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


class SymlinkValidationError(Exception):
    """Exception raised when symlink validation fails."""


def validate_symlink_target(
    link: Path, expected: list[str], check_exists: bool = True
) -> bool:
    """
    Validate that a symlink points to one of the expected targets.

    Args:
        link: Path to the symlink to validate
        expected: List of expected target names (not full paths)
        check_exists: If True, verify that the symlink target exists

    Returns:
        True if validation passes

    Raises:
        SymlinkValidationError: If validation fails with details about what failed
    """
    # Check if path exists
    if not link.exists() and not link.is_symlink():
        raise SymlinkValidationError(f"Path does not exist: {link}")

    # Check if it's actually a symlink
    if not link.is_symlink():
        raise SymlinkValidationError(f"Path is not a symlink: {link}")

    # Read the symlink target
    try:
        target = link.readlink()
    except OSError as e:
        raise SymlinkValidationError(f"Cannot read symlink {link}: {e}") from e

    # Get the target name (last component of path)
    target_name = target.name if isinstance(target, Path) else Path(target).name

    # Check if target name is in expected list
    if target_name not in expected:
        expected_str = ", ".join(expected)
        raise SymlinkValidationError(
            f"Symlink {link} points to '{target_name}', expected one of: {expected_str}"
        )

    # Check if target exists (if requested)
    if check_exists:
        # Resolve relative to the symlink's parent directory
        resolved_target = link.parent / target
        if not resolved_target.exists():
            raise SymlinkValidationError(
                f"Symlink {link} points to non-existent target: {target} (resolved to {resolved_target})"
            )

    return True
