"""Tests for the validators module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.engine.validators import (
    BinaryNotFoundError,
    ValidationError,
    check_binary_available,
    check_bootstrap_binaries,
    check_deploy_binaries,
    check_required_binaries,
    validate_env_yaml,
)


def test_validate_env_yaml_valid_file(tmp_path):
    """Test validation passes for a valid environment YAML file."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        """channels:
  - conda-forge
dependencies:
  - python~=3.13
  - pytest
"""
    )
    assert validate_env_yaml(yaml_file) is True


def test_validate_env_yaml_with_pip_deps(tmp_path):
    """Test validation passes for YAML with pip dependencies."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        """channels:
  - conda-forge
dependencies:
  - python
  - pip
  - pip:
    - cogapp
    - xkcdpass
"""
    )
    assert validate_env_yaml(yaml_file) is True


def test_validate_env_yaml_multiple_channels(tmp_path):
    """Test validation passes for multiple channels."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        """channels:
  - conda-forge
  - bioconda
  - defaults
dependencies:
  - samtools
"""
    )
    assert validate_env_yaml(yaml_file) is True


def test_validate_env_yaml_file_not_exists(tmp_path):
    """Test validation fails when file doesn't exist."""
    yaml_file = tmp_path / "nonexistent.yaml"
    with pytest.raises(ValidationError, match="File does not exist"):
        validate_env_yaml(yaml_file)


def test_validate_env_yaml_path_is_directory(tmp_path):
    """Test validation fails when path is a directory."""
    with pytest.raises(ValidationError, match="Path is not a file"):
        validate_env_yaml(tmp_path)


def test_validate_env_yaml_invalid_syntax(tmp_path):
    """Test validation fails for invalid YAML syntax."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        """channels:
  - conda-forge
dependencies: [unclosed bracket
"""
    )
    with pytest.raises(ValidationError, match="Invalid YAML syntax"):
        validate_env_yaml(yaml_file)


def test_validate_env_yaml_not_dict(tmp_path):
    """Test validation fails when YAML root is not a dictionary."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("- item1\n- item2\n")
    with pytest.raises(ValidationError, match="Expected YAML to contain a dictionary"):
        validate_env_yaml(yaml_file)


def test_validate_env_yaml_missing_channels(tmp_path):
    """Test validation fails when channels key is missing."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        """dependencies:
  - python
"""
    )
    with pytest.raises(ValidationError, match="Missing required keys.*channels"):
        validate_env_yaml(yaml_file)


def test_validate_env_yaml_missing_dependencies(tmp_path):
    """Test validation fails when dependencies key is missing."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        """channels:
  - conda-forge
"""
    )
    with pytest.raises(ValidationError, match="Missing required keys.*dependencies"):
        validate_env_yaml(yaml_file)


def test_validate_env_yaml_missing_both_keys(tmp_path):
    """Test validation fails when both required keys are missing."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("name: test\n")
    with pytest.raises(
        ValidationError, match="Missing required keys.*channels.*dependencies"
    ):
        validate_env_yaml(yaml_file)


def test_validate_env_yaml_channels_not_list(tmp_path):
    """Test validation fails when channels is not a list."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        """channels: conda-forge
dependencies:
  - python
"""
    )
    with pytest.raises(ValidationError, match="'channels' must be a list"):
        validate_env_yaml(yaml_file)


def test_validate_env_yaml_channels_empty(tmp_path):
    """Test validation fails when channels list is empty."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        """channels: []
dependencies:
  - python
"""
    )
    with pytest.raises(ValidationError, match="'channels' list cannot be empty"):
        validate_env_yaml(yaml_file)


def test_validate_env_yaml_channel_not_string(tmp_path):
    """Test validation fails when a channel is not a string."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        """channels:
  - conda-forge
  - 123
dependencies:
  - python
"""
    )
    with pytest.raises(ValidationError, match="Channel at index 1 must be a string"):
        validate_env_yaml(yaml_file)


def test_validate_env_yaml_channel_empty_string(tmp_path):
    """Test validation fails when a channel is an empty string."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        """channels:
  - conda-forge
  - ""
dependencies:
  - python
"""
    )
    with pytest.raises(ValidationError, match="Channel at index 1 cannot be empty"):
        validate_env_yaml(yaml_file)


def test_validate_env_yaml_channel_whitespace_only(tmp_path):
    """Test validation fails when a channel is only whitespace."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        """channels:
  - conda-forge
  - "   "
dependencies:
  - python
"""
    )
    with pytest.raises(ValidationError, match="Channel at index 1 cannot be empty"):
        validate_env_yaml(yaml_file)


def test_validate_env_yaml_channel_with_invalid_whitespace(tmp_path):
    """Test validation fails when channel contains invalid whitespace."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        """channels:
  - conda-forge
  - "conda forge"
dependencies:
  - python
"""
    )
    with pytest.raises(
        ValidationError, match="Channel at index 1 contains invalid whitespace"
    ):
        validate_env_yaml(yaml_file)


def test_validate_env_yaml_channel_url(tmp_path):
    """Test validation passes for channel URLs."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        """channels:
  - https://repo.anaconda.com/pkgs/main
  - file:///local/channel
dependencies:
  - python
"""
    )
    assert validate_env_yaml(yaml_file) is True


def test_validate_env_yaml_channel_with_namespace(tmp_path):
    """Test validation passes for channels with namespace."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        """channels:
  - conda-forge/label/main
  - user/channel
dependencies:
  - python
"""
    )
    assert validate_env_yaml(yaml_file) is True


def test_validate_env_yaml_dependencies_not_list(tmp_path):
    """Test validation fails when dependencies is not a list."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        """channels:
  - conda-forge
dependencies: python
"""
    )
    with pytest.raises(ValidationError, match="'dependencies' must be a list"):
        validate_env_yaml(yaml_file)


def test_validate_env_yaml_dependencies_empty(tmp_path):
    """Test validation fails when dependencies list is empty."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        """channels:
  - conda-forge
dependencies: []
"""
    )
    with pytest.raises(ValidationError, match="'dependencies' list cannot be empty"):
        validate_env_yaml(yaml_file)


def test_validate_env_yaml_dependency_not_string_or_dict(tmp_path):
    """Test validation fails when a dependency is not a string or dict."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        """channels:
  - conda-forge
dependencies:
  - python
  - 123
"""
    )
    with pytest.raises(
        ValidationError, match="Dependency at index 1 must be a string or dict"
    ):
        validate_env_yaml(yaml_file)


def test_validate_env_yaml_dependency_empty_string(tmp_path):
    """Test validation fails when a dependency is an empty string."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        """channels:
  - conda-forge
dependencies:
  - python
  - ""
"""
    )
    with pytest.raises(ValidationError, match="Dependency at index 1 cannot be empty"):
        validate_env_yaml(yaml_file)


def test_validate_env_yaml_dependency_with_newline(tmp_path):
    """Test validation fails when dependency contains newline."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        """channels:
  - conda-forge
dependencies:
  - python
  - "pack\\nage"
"""
    )
    with pytest.raises(
        ValidationError, match="Dependency at index 1 contains invalid character"
    ):
        validate_env_yaml(yaml_file)


def test_validate_env_yaml_versioned_dependencies(tmp_path):
    """Test validation passes for versioned dependencies."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        """channels:
  - conda-forge
dependencies:
  - python=3.13
  - pytest>=7.0
  - numpy~=1.24
  - scipy<2.0
  - pandas<=1.5
  - matplotlib!=3.6.0
"""
    )
    assert validate_env_yaml(yaml_file) is True


def test_validate_env_yaml_channel_prefix_dependency(tmp_path):
    """Test validation passes for dependencies with channel prefix."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        """channels:
  - conda-forge
dependencies:
  - conda-forge::python
  - bioconda::samtools=1.15
"""
    )
    assert validate_env_yaml(yaml_file) is True


def test_validate_env_yaml_pip_not_list(tmp_path):
    """Test validation fails when pip value is not a list."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        """channels:
  - conda-forge
dependencies:
  - python
  - pip: cogapp
"""
    )
    with pytest.raises(
        ValidationError, match="Dependency at index 1: 'pip' value must be a list"
    ):
        validate_env_yaml(yaml_file)


def test_validate_env_yaml_pip_dep_not_string(tmp_path):
    """Test validation fails when a pip dependency is not a string."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        """channels:
  - conda-forge
dependencies:
  - python
  - pip:
    - cogapp
    - 123
"""
    )
    with pytest.raises(
        ValidationError,
        match="Dependency at index 1: pip dependency at index 1 must be a string",
    ):
        validate_env_yaml(yaml_file)


def test_validate_env_yaml_pip_dep_empty(tmp_path):
    """Test validation fails when a pip dependency is empty."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        """channels:
  - conda-forge
dependencies:
  - python
  - pip:
    - cogapp
    - ""
"""
    )
    with pytest.raises(
        ValidationError,
        match="Dependency at index 1: pip dependency at index 1 cannot be empty",
    ):
        validate_env_yaml(yaml_file)


def test_validate_env_yaml_complex_valid_file(tmp_path):
    """Test validation passes for a complex, valid YAML file."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        """channels:
  - conda-forge
  - bioconda
  - https://custom.repo.com/channel
dependencies:
  - python~=3.13
  - conda-forge::pytest>=7.0
  - numpy=1.24
  - scipy
  - pandas!=1.5.0
  - pip
  - pip:
    - cogapp
    - rerun>=0.1.0
    - xkcdpass
"""
    )
    assert validate_env_yaml(yaml_file) is True


def test_validate_env_yaml_real_engine_file():
    """Test validation passes for the real engine.yaml file."""
    # This tests against an actual file in the project
    engine_yaml = (
        Path(__file__).parent.parent.parent / "resources/defs/special/engine.yaml"
    )
    if engine_yaml.exists():
        assert validate_env_yaml(engine_yaml) is True
    else:
        pytest.skip("engine.yaml not found")


def test_validate_env_yaml_real_python_file():
    """Test validation passes for the real python.yaml file."""
    # This tests against an actual file in the project
    python_yaml = (
        Path(__file__).parent.parent.parent / "resources/defs/universal/python.yaml"
    )
    if python_yaml.exists():
        assert validate_env_yaml(python_yaml) is True
    else:
        pytest.skip("python.yaml not found")


# Binary checking tests


def test_check_binary_available_found_in_path():
    """Test that check_binary_available finds a binary in PATH."""
    # Python should always be available since we're running tests with it
    result = check_binary_available("python3")
    assert result is not None
    assert result.exists()


def test_check_binary_available_not_found():
    """Test that check_binary_available returns None for nonexistent binary."""
    result = check_binary_available("nonexistent-binary-xyz-123")
    assert result is None


def test_check_binary_available_with_specific_path(tmp_path):
    """Test that check_binary_available checks specific paths first."""
    # Create a fake binary in a specific path
    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()
    fake_binary = fake_bin_dir / "testbin"
    fake_binary.write_text("#!/bin/sh\necho test")
    fake_binary.chmod(0o755)

    # Check with specific path
    result = check_binary_available("testbin", [str(fake_bin_dir)])
    assert result is not None
    assert result == fake_binary


def test_check_binary_available_specific_path_not_found(tmp_path):
    """Test that check_binary_available falls back to PATH if not in specific paths."""
    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()

    # Binary not in specific path, but check that it falls back to PATH
    result = check_binary_available("python3", [str(fake_bin_dir)])
    # Should find python3 in system PATH
    assert result is not None


def test_check_required_binaries_all_found():
    """Test check_required_binaries when all binaries are found."""
    # Use binaries that should always exist
    result = check_required_binaries(["sh", "echo"])
    assert "sh" in result
    assert "echo" in result
    assert result["sh"] is not None
    assert result["echo"] is not None


def test_check_required_binaries_missing_required():
    """Test check_required_binaries raises error for missing required binaries."""
    with pytest.raises(BinaryNotFoundError, match="Required binaries not found"):
        check_required_binaries(["nonexistent-binary-xyz-123"])


def test_check_required_binaries_missing_optional():
    """Test check_required_binaries allows missing optional binaries."""
    result = check_required_binaries(
        ["sh", "nonexistent-binary-xyz-123"], optional=["nonexistent-binary-xyz-123"]
    )
    assert "sh" in result
    assert result["sh"] is not None
    assert "nonexistent-binary-xyz-123" in result
    assert result["nonexistent-binary-xyz-123"] is None


def test_check_required_binaries_with_search_paths(tmp_path):
    """Test check_required_binaries with specific search paths."""
    # Create a fake binary
    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()
    fake_binary = fake_bin_dir / "testbin"
    fake_binary.write_text("#!/bin/sh\necho test")
    fake_binary.chmod(0o755)

    result = check_required_binaries(
        ["testbin"], search_paths={"testbin": [str(fake_bin_dir)]}
    )
    assert result["testbin"] == fake_binary


def test_check_required_binaries_error_message_format():
    """Test that error message contains helpful installation instructions."""
    with pytest.raises(BinaryNotFoundError) as exc_info:
        check_required_binaries(["nonexistent-curl-xyz", "nonexistent-git-xyz"])

    error_msg = str(exc_info.value)
    assert "nonexistent-curl-xyz" in error_msg
    assert "nonexistent-git-xyz" in error_msg
    assert "Required binaries not found" in error_msg


@patch("scripts.engine.validators.check_binary_available")
def test_check_required_binaries_installation_instructions(mock_check):
    """Test that error message includes installation instructions for known binaries."""
    mock_check.return_value = None

    with pytest.raises(BinaryNotFoundError) as exc_info:
        check_required_binaries(["curl", "git"])

    error_msg = str(exc_info.value)
    assert "curl" in error_msg
    assert "git" in error_msg
    assert "apt-get install" in error_msg or "yum install" in error_msg


@patch("scripts.engine.validators.check_binary_available")
def test_check_bootstrap_binaries_success(mock_check):
    """Test check_bootstrap_binaries when all binaries are found."""
    mock_check.return_value = Path("/usr/bin/curl")

    result = check_bootstrap_binaries()
    assert "curl" in result
    assert "tar" in result


@patch("scripts.engine.validators.check_binary_available")
def test_check_bootstrap_binaries_missing(mock_check):
    """Test check_bootstrap_binaries raises error when binaries are missing."""
    mock_check.return_value = None

    with pytest.raises(BinaryNotFoundError):
        check_bootstrap_binaries()


@patch("scripts.engine.validators.check_binary_available")
def test_check_deploy_binaries_success(mock_check):
    """Test check_deploy_binaries when git is found."""
    mock_check.return_value = Path("/usr/bin/git")

    result = check_deploy_binaries()
    assert "git" in result
    assert result["git"] is not None


@patch("scripts.engine.validators.check_binary_available")
def test_check_deploy_binaries_missing_required(mock_check):
    """Test check_deploy_binaries raises error when git is required but missing."""
    mock_check.return_value = None

    with pytest.raises(BinaryNotFoundError):
        check_deploy_binaries(require_git=True)


@patch("scripts.engine.validators.check_binary_available")
def test_check_deploy_binaries_missing_optional(mock_check):
    """Test check_deploy_binaries allows missing git when optional."""
    mock_check.return_value = None

    result = check_deploy_binaries(require_git=False)
    assert "git" in result
    assert result["git"] is None
