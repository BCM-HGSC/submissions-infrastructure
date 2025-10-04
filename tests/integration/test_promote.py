"""Integration tests for promote_staging workflow."""

import os
from pathlib import Path
import subprocess

import pytest


@pytest.fixture
def promote_test_env(tmp_path):
    """Create a minimal infrastructure directory for testing promote_staging.

    Creates:
    - infrastructure/blue/ (directory)
    - infrastructure/green/ (directory)
    - infrastructure/staging -> blue (symlink)
    - infrastructure/production -> green (symlink)
    """
    target_dir = tmp_path / "test_target"
    target_dir.mkdir()

    infrastructure = target_dir / "infrastructure"
    infrastructure.mkdir()

    # Create blue and green directories
    blue = infrastructure / "blue"
    blue.mkdir()

    green = infrastructure / "green"
    green.mkdir()

    # Create staging symlink pointing to blue
    staging = infrastructure / "staging"
    staging.symlink_to("blue")

    # Create production symlink pointing to green
    production = infrastructure / "production"
    production.symlink_to("green")

    return infrastructure


@pytest.fixture
def promote_script():
    """Return path to promote_staging script."""
    return Path(__file__).parent.parent.parent / "scripts" / "promote_staging"


@pytest.mark.integration
def test_promote_blue_to_green(promote_test_env, promote_script):
    """Test promotion when staging points to blue and production to green."""
    # Initial state: staging -> blue, production -> green
    staging = promote_test_env / "staging"
    production = promote_test_env / "production"

    assert staging.readlink().name == "blue"
    assert production.readlink().name == "green"

    # Set IAC_TIER_DIR to staging (which points to blue)
    staging_target = staging.resolve()
    env = os.environ.copy()
    env["IAC_TIER_DIR"] = str(staging_target)

    # Run promote_staging
    result = subprocess.run(
        [str(promote_script)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, f"promote_staging failed: {result.stderr}"

    # After promotion: staging -> green, production -> blue
    assert staging.readlink().name == "green", "staging should now point to green"
    assert production.readlink().name == "blue", "production should now point to blue"


@pytest.mark.integration
def test_promote_green_to_blue(promote_test_env, promote_script):
    """Test promotion when staging points to green and production to blue."""
    # Set up initial state: staging -> green, production -> blue
    staging = promote_test_env / "staging"
    production = promote_test_env / "production"

    staging.unlink()
    staging.symlink_to("green")
    production.unlink()
    production.symlink_to("blue")

    assert staging.readlink().name == "green"
    assert production.readlink().name == "blue"

    # Set IAC_TIER_DIR to staging (which points to green)
    staging_target = staging.resolve()
    env = os.environ.copy()
    env["IAC_TIER_DIR"] = str(staging_target)

    # Run promote_staging
    result = subprocess.run(
        [str(promote_script)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, f"promote_staging failed: {result.stderr}"

    # After promotion: staging -> blue, production -> green
    assert staging.readlink().name == "blue", "staging should now point to blue"
    assert production.readlink().name == "green", "production should now point to green"


@pytest.mark.integration
def test_promote_requires_iac_tier_dir(promote_test_env, promote_script):
    """Test that promote_staging requires IAC_TIER_DIR environment variable."""
    # Run without IAC_TIER_DIR in environment
    env = os.environ.copy()
    if "IAC_TIER_DIR" in env:
        del env["IAC_TIER_DIR"]

    result = subprocess.run(
        [str(promote_script)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode != 0, "Should fail without IAC_TIER_DIR"
    assert "IAC_TIER_DIR" in result.stdout or "IAC_TIER_DIR" in result.stderr


@pytest.mark.integration
def test_promote_error_same_color(promote_test_env, promote_script):
    """Test error when staging and production point to same tier."""
    # Set up initial state: staging -> blue, production -> blue (invalid)
    staging = promote_test_env / "staging"
    production = promote_test_env / "production"

    staging.unlink()
    staging.symlink_to("blue")
    production.unlink()
    production.symlink_to("blue")

    assert staging.readlink().name == "blue"
    assert production.readlink().name == "blue"

    # Set IAC_TIER_DIR to staging
    staging_target = staging.resolve()
    env = os.environ.copy()
    env["IAC_TIER_DIR"] = str(staging_target)

    # Run promote_staging - should fail
    result = subprocess.run(
        [str(promote_script)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode != 0, "Should fail when staging and production same color"
    assert (
        "same color" in result.stdout.lower() or "same color" in result.stderr.lower()
    )


@pytest.mark.integration
def test_promote_creates_production_if_missing(promote_test_env, promote_script):
    """Test that promote_staging creates production symlink if it doesn't exist."""
    # Initial state: staging -> blue, no production symlink
    staging = promote_test_env / "staging"
    production = promote_test_env / "production"

    # Remove production symlink
    production.unlink()
    assert not production.exists()

    # Set IAC_TIER_DIR to staging (which points to blue)
    staging_target = staging.resolve()
    env = os.environ.copy()
    env["IAC_TIER_DIR"] = str(staging_target)

    # Run promote_staging
    result = subprocess.run(
        [str(promote_script)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, f"promote_staging failed: {result.stderr}"

    # After promotion: staging -> green, production -> blue (newly created)
    assert staging.exists()
    assert staging.is_symlink()
    assert production.exists()
    assert production.is_symlink()
    assert staging.readlink().name == "green", "staging should now point to green"
    assert production.readlink().name == "blue", "production should now point to blue"


@pytest.mark.integration
def test_promote_error_staging_not_symlink(promote_test_env, promote_script):
    """Test error when staging is not a symlink."""
    # Replace staging symlink with a regular directory
    staging = promote_test_env / "staging"
    staging.unlink()
    staging.mkdir()

    # Set IAC_TIER_DIR to the staging directory
    env = os.environ.copy()
    env["IAC_TIER_DIR"] = str(staging)

    # Run promote_staging - should fail
    result = subprocess.run(
        [str(promote_script)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode != 0, "Should fail when staging is not a symlink"
    assert "symlink" in result.stdout.lower() or "symlink" in result.stderr.lower()


@pytest.mark.integration
def test_promote_error_invalid_color(promote_test_env, promote_script):
    """Test error when staging points to neither blue nor green."""
    # Create staging pointing to invalid color
    staging = promote_test_env / "staging"
    staging.unlink()

    # Create a "red" directory and point staging to it
    red = promote_test_env / "red"
    red.mkdir()
    staging.symlink_to("red")

    # Set IAC_TIER_DIR to staging target
    staging_target = staging.resolve()
    env = os.environ.copy()
    env["IAC_TIER_DIR"] = str(staging_target)

    # Run promote_staging - should fail
    result = subprocess.run(
        [str(promote_script)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode != 0, "Should fail when staging points to invalid color"
    assert (
        "blue" in result.stdout.lower()
        or "blue" in result.stderr.lower()
        or "green" in result.stdout.lower()
        or "green" in result.stderr.lower()
    )
