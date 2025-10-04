"""Unit tests for bootstrap-engine script argument parsing."""

from pathlib import Path
import subprocess

import pytest


@pytest.fixture
def bootstrap_script():
    """Return path to bootstrap-engine script."""
    return Path(__file__).parent.parent.parent / "scripts" / "bootstrap-engine"


def test_bootstrap_help_flag(bootstrap_script):
    """Test that --help flag displays help message and exits 0."""
    result = subprocess.run(
        [str(bootstrap_script), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert "TARGET_DIR" in result.stdout
    assert "--offline" in result.stdout
    assert "--verbose" in result.stdout


def test_bootstrap_missing_target_dir(bootstrap_script):
    """Test that missing TARGET_DIR argument causes error."""
    result = subprocess.run(
        [str(bootstrap_script)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "TARGET_DIR argument is required" in result.stderr


def test_bootstrap_unknown_flag(bootstrap_script):
    """Test that unknown flag causes error."""
    result = subprocess.run(
        [str(bootstrap_script), "--unknown-flag", "/tmp/test"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Unknown option: --unknown-flag" in result.stderr


def test_bootstrap_too_many_arguments(bootstrap_script, tmp_path):
    """Test that too many positional arguments causes error."""
    result = subprocess.run(
        [str(bootstrap_script), str(tmp_path), "extra_arg"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Too many arguments" in result.stderr


# Note: Positive tests for flag parsing (--offline, --verbose, -y, etc.) are not
# included as unit tests because they require actually executing the bootstrap script,
# which would download micromamba and create environments. Those are better suited for
# integration tests. The unit tests here focus on error conditions that fail fast.
