"""Unit tests for path validation logic in deploy.py."""

from pathlib import Path

import pytest

from scripts.engine.deploy import setup_tier_path, validate_tier_path
from scripts.engine.filesystem import MockFileSystem


def test_validate_tier_path_basic():
    """Test validate_tier_path computes correct path."""
    target = Path("/tmp/test")
    tier = "staging"

    result = validate_tier_path(target, tier)

    # Should be target/infrastructure/tier resolved
    expected = (target / "infrastructure" / tier).resolve()
    assert result == expected


def test_validate_tier_path_blue():
    """Test validate_tier_path with blue tier."""
    target = Path("/var/data")
    tier = "blue"

    result = validate_tier_path(target, tier)

    assert result == (target / "infrastructure" / "blue").resolve()


def test_validate_tier_path_green():
    """Test validate_tier_path with green tier."""
    target = Path("/var/data")
    tier = "green"

    result = validate_tier_path(target, tier)

    assert result == (target / "infrastructure" / "green").resolve()


def test_validate_tier_path_production():
    """Test validate_tier_path with production tier."""
    target = Path("/var/data")
    tier = "production"

    result = validate_tier_path(target, tier)

    assert result == (target / "infrastructure" / "production").resolve()


def test_validate_tier_path_custom_tier():
    """Test validate_tier_path with custom tier names."""
    target = Path("/tmp/test")

    # Test dev.* pattern
    result = validate_tier_path(target, "dev-feature-x")
    assert result == (target / "infrastructure" / "dev-feature-x").resolve()

    # Test test.* pattern
    result = validate_tier_path(target, "test-pr-123")
    assert result == (target / "infrastructure" / "test-pr-123").resolve()


def test_setup_tier_path_with_existing_directory(tmp_path):
    """Test setup_tier_path when target directory exists."""
    filesystem = MockFileSystem()
    # Mock the target directory as existing
    filesystem.directories.add(tmp_path)
    tier_path = tmp_path / "infrastructure" / "staging"
    filesystem.directories.add(tier_path)

    result = setup_tier_path(tmp_path, "staging", filesystem)

    assert result == tier_path.resolve()


def test_setup_tier_path_creates_directory(tmp_path):
    """Test setup_tier_path creates directory if it doesn't exist."""
    filesystem = MockFileSystem()
    # Mock only the target directory as existing
    filesystem.directories.add(tmp_path)

    result = setup_tier_path(tmp_path, "staging", filesystem)

    tier_path = (tmp_path / "infrastructure" / "staging").resolve()
    assert result == tier_path
    # Verify directory was created
    assert tier_path in filesystem.directories


def test_setup_tier_path_nonexistent_target():
    """Test setup_tier_path exits when target doesn't exist."""
    filesystem = MockFileSystem()
    # Don't add target to directories, so it doesn't exist
    target = Path("/nonexistent")

    with pytest.raises(SystemExit) as exc_info:
        setup_tier_path(target, "staging", filesystem)

    assert exc_info.value.code == 3


def test_setup_tier_path_with_symlink(tmp_path):
    """Test setup_tier_path works with symlink as tier_path."""
    filesystem = MockFileSystem()
    filesystem.directories.add(tmp_path)

    # Create a tier that's a symlink
    tier_link = tmp_path / "infrastructure" / "staging"
    actual_dir = tmp_path / "infrastructure" / "blue"
    filesystem.symlinks[tier_link] = actual_dir
    filesystem.directories.add(actual_dir)

    # Mock is_dir to return True for the symlink
    # (In real filesystem, is_dir follows symlinks)
    original_is_dir = filesystem.is_dir

    def is_dir_with_symlink(path):
        if path in filesystem.symlinks:
            target = filesystem.symlinks[path]
            return target in filesystem.directories
        return original_is_dir(path)

    filesystem.is_dir = is_dir_with_symlink

    result = setup_tier_path(tmp_path, "staging", filesystem)

    # Should resolve through the symlink
    assert result == tier_link.resolve()


def test_production_tier_protection(tmp_path):
    """Test that deploying to production tier is protected.

    This test verifies the protection logic in deploy_tier() that prevents
    direct modification of production tier.
    """
    from scripts.engine.deploy import MAMBA, deploy_tier

    filesystem = MockFileSystem()
    filesystem.directories.add(tmp_path)

    # Mock mamba binary as existing
    filesystem.files.add(MAMBA)

    # Attempting to deploy to production should fail
    with pytest.raises(SystemExit) as exc_info:
        deploy_tier(
            tmp_path,
            "production",
            dry_run=False,
            offline=False,
            filesystem=filesystem,
        )

    assert exc_info.value.code == 4


def test_production_tier_different_from_staging(tmp_path):
    """Test that production and staging paths are different."""
    # This is a sanity check to ensure tier isolation
    prod_path = validate_tier_path(tmp_path, "production")
    staging_path = validate_tier_path(tmp_path, "staging")

    assert prod_path != staging_path


def test_validate_tier_path_is_pure_function():
    """Test that validate_tier_path is deterministic and has no side effects."""
    target = Path("/test")
    tier = "staging"

    # Call multiple times with same inputs
    result1 = validate_tier_path(target, tier)
    result2 = validate_tier_path(target, tier)
    result3 = validate_tier_path(target, tier)

    # Should always return the same result
    assert result1 == result2 == result3


def test_setup_tier_path_creates_parent_directories(tmp_path):
    """Test setup_tier_path creates parent directories."""
    filesystem = MockFileSystem()
    filesystem.directories.add(tmp_path)

    setup_tier_path(tmp_path, "blue", filesystem)

    # Verify the tier path was created with parents=True
    tier_path = (tmp_path / "infrastructure" / "blue").resolve()
    assert tier_path in filesystem.directories
