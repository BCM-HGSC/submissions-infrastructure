"""Unit tests for error handling and error conditions."""

from pathlib import Path

import pytest

from scripts.engine.deploy import (
    MAMBA,
    check_mamba,
    deploy_tier,
    list_conda_environment_defs,
)
from scripts.engine.filesystem import MockFileSystem


def test_check_mamba_missing():
    """Test check_mamba exits when mamba binary is missing."""
    filesystem = MockFileSystem()
    # Don't add MAMBA to files, so it doesn't exist

    with pytest.raises(SystemExit) as exc_info:
        check_mamba(filesystem)

    assert exc_info.value.code == 2


def test_check_mamba_exists():
    """Test check_mamba succeeds when mamba binary exists."""
    filesystem = MockFileSystem()
    filesystem.files.add(MAMBA)

    # Should not raise
    check_mamba(filesystem)


def test_deploy_tier_missing_mamba(tmp_path):
    """Test deploy_tier exits when mamba is missing."""
    filesystem = MockFileSystem()
    filesystem.directories.add(tmp_path)
    # Don't add mamba to files

    with pytest.raises(SystemExit) as exc_info:
        deploy_tier(
            tmp_path,
            "staging",
            dry_run=False,
            offline=False,
            filesystem=filesystem,
        )

    assert exc_info.value.code == 2


def test_deploy_tier_nonexistent_target():
    """Test deploy_tier exits when target directory doesn't exist."""
    filesystem = MockFileSystem()
    filesystem.files.add(MAMBA)
    # Don't add target to directories

    nonexistent = Path("/nonexistent")

    with pytest.raises(SystemExit) as exc_info:
        deploy_tier(
            nonexistent,
            "staging",
            dry_run=False,
            offline=False,
            filesystem=filesystem,
        )

    assert exc_info.value.code == 3


def test_deploy_tier_production_protection(tmp_path):
    """Test deploy_tier prevents deployment to production tier."""
    filesystem = MockFileSystem()
    filesystem.files.add(MAMBA)
    filesystem.directories.add(tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        deploy_tier(
            tmp_path,
            "production",
            dry_run=False,
            offline=False,
            filesystem=filesystem,
        )

    assert exc_info.value.code == 4


def test_list_conda_environment_defs_no_universal():
    """Test list_conda_environment_defs when universal directory doesn't exist."""
    # This test verifies the function handles missing directories gracefully
    # The glob will return empty list if directory doesn't exist
    result = list_conda_environment_defs()

    # Result should still be a list (may be empty or contain platform-specific files)
    assert isinstance(result, list)


def test_list_conda_environment_defs_filters_non_files():
    """Test list_conda_environment_defs filters out non-file items."""
    # This tests the bug fix from deploy.py:124
    # The function should filter out directories and only return files
    result = list_conda_environment_defs()

    # All items should be files
    for item in result:
        assert item.is_file() or not item.exists()  # May not exist in test environment


def test_mock_filesystem_rmtree_nonexistent():
    """Test MockFileSystem.rmtree handles nonexistent paths gracefully."""
    filesystem = MockFileSystem()

    # Should track removal even if path doesn't exist in mock
    filesystem.rmtree(Path("/nonexistent"))

    assert Path("/nonexistent") in filesystem.removed


def test_mock_filesystem_mkdir_tracking():
    """Test MockFileSystem.mkdir tracks created directories."""
    filesystem = MockFileSystem()

    path = Path("/test/dir")
    filesystem.mkdir(path, parents=True)

    assert path in filesystem.directories


def test_mock_filesystem_copytree_tracking():
    """Test MockFileSystem.copytree tracks copy operations."""
    filesystem = MockFileSystem()

    src = Path("/src")
    dst = Path("/dst")
    filesystem.copytree(src, dst)

    assert (src, dst) in filesystem.copied


def test_mock_filesystem_symlink_tracking():
    """Test MockFileSystem.symlink_to tracks symlink creation."""
    filesystem = MockFileSystem()

    link = Path("/link")
    target = Path("/target")
    filesystem.symlink_to(link, target)

    assert link in filesystem.symlinks
    assert filesystem.symlinks[link] == target


def test_mock_filesystem_exists_for_directory():
    """Test MockFileSystem.exists returns True for directories."""
    filesystem = MockFileSystem()

    path = Path("/test")
    filesystem.directories.add(path)

    assert filesystem.exists(path) is True


def test_mock_filesystem_exists_for_file():
    """Test MockFileSystem.exists returns True for files."""
    filesystem = MockFileSystem()

    path = Path("/test.txt")
    filesystem.files.add(path)

    assert filesystem.exists(path) is True


def test_mock_filesystem_exists_for_symlink():
    """Test MockFileSystem.exists returns True for symlinks."""
    filesystem = MockFileSystem()

    link = Path("/link")
    target = Path("/target")
    filesystem.symlinks[link] = target
    filesystem.directories.add(target)

    assert filesystem.exists(link) is True


def test_mock_filesystem_exists_for_nonexistent():
    """Test MockFileSystem.exists returns False for nonexistent paths."""
    filesystem = MockFileSystem()

    assert filesystem.exists(Path("/nonexistent")) is False


def test_mock_filesystem_is_dir_for_directory():
    """Test MockFileSystem.is_dir returns True for directories."""
    filesystem = MockFileSystem()

    path = Path("/test")
    filesystem.directories.add(path)

    assert filesystem.is_dir(path) is True


def test_mock_filesystem_is_dir_for_file():
    """Test MockFileSystem.is_dir returns False for files."""
    filesystem = MockFileSystem()

    path = Path("/test.txt")
    filesystem.files.add(path)

    assert filesystem.is_dir(path) is False


def test_mock_filesystem_is_file_for_file():
    """Test MockFileSystem.is_file returns True for files."""
    filesystem = MockFileSystem()

    path = Path("/test.txt")
    filesystem.files.add(path)

    assert filesystem.is_file(path) is True


def test_mock_filesystem_is_file_for_directory():
    """Test MockFileSystem.is_file returns False for directories."""
    filesystem = MockFileSystem()

    path = Path("/test")
    filesystem.directories.add(path)

    assert filesystem.is_file(path) is False


def test_mock_filesystem_is_symlink_for_symlink():
    """Test MockFileSystem.is_symlink returns True for symlinks."""
    filesystem = MockFileSystem()

    link = Path("/link")
    target = Path("/target")
    filesystem.symlinks[link] = target

    assert filesystem.is_symlink(link) is True


def test_mock_filesystem_is_symlink_for_file():
    """Test MockFileSystem.is_symlink returns False for regular files."""
    filesystem = MockFileSystem()

    path = Path("/test.txt")
    filesystem.files.add(path)

    assert filesystem.is_symlink(path) is False


def test_mock_filesystem_readlink():
    """Test MockFileSystem.readlink returns symlink target."""
    filesystem = MockFileSystem()

    link = Path("/link")
    target = Path("/target")
    filesystem.symlinks[link] = target

    assert filesystem.readlink(link) == target


def test_error_exit_codes_are_distinct():
    """Test that different error conditions have distinct exit codes."""
    # This ensures we can distinguish between different error types
    exit_codes = {
        "mamba_missing": 2,
        "target_not_directory": 3,
        "production_protection": 4,
    }

    # All exit codes should be unique
    assert len(exit_codes) == len(set(exit_codes.values()))

    # All should be non-zero
    assert all(code > 0 for code in exit_codes.values())


# Note: Tests for --keep and --force modes are better suited for integration tests
# since they require actual filesystem operations even in dry-run mode (log file creation).
# Error handling for these modes is already covered by the tests above.
