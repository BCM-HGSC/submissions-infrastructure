"""Unit tests for environment definition loading."""

from pathlib import Path
import sys
from unittest.mock import patch

import pytest

from scripts.engine.deploy import DEFS_DIR, list_conda_environment_defs


def test_list_conda_environment_defs_returns_list():
    """Test list_conda_environment_defs returns a list."""
    result = list_conda_environment_defs()
    assert isinstance(result, list)


def test_list_conda_environment_defs_contains_paths():
    """Test list_conda_environment_defs returns Path objects."""
    result = list_conda_environment_defs()
    for item in result:
        assert isinstance(item, Path)


def test_list_conda_environment_defs_on_darwin():
    """Test list_conda_environment_defs on Darwin (macOS)."""
    with patch("sys.platform", "darwin"):
        result = list_conda_environment_defs()

        # Should include universal files
        universal_files = [f for f in result if "universal" in str(f)]
        assert len(universal_files) > 0

        # Should include mac.yaml
        mac_files = [f for f in result if "mac.yaml" in str(f)]
        assert len(mac_files) == 1

        # Should NOT include linux.yaml
        linux_files = [f for f in result if "linux.yaml" in str(f)]
        assert len(linux_files) == 0


def test_list_conda_environment_defs_on_linux():
    """Test list_conda_environment_defs on Linux."""
    with patch("sys.platform", "linux"):
        result = list_conda_environment_defs()

        # Should include universal files
        universal_files = [f for f in result if "universal" in str(f)]
        assert len(universal_files) > 0

        # Should include linux.yaml
        linux_files = [f for f in result if "linux.yaml" in str(f)]
        assert len(linux_files) == 1

        # Should NOT include mac.yaml
        mac_files = [f for f in result if "mac.yaml" in str(f)]
        assert len(mac_files) == 0


def test_list_conda_environment_defs_on_unknown_platform():
    """Test list_conda_environment_defs on unknown platform."""
    with patch("sys.platform", "win32"):
        result = list_conda_environment_defs()

        # Should include universal files
        universal_files = [f for f in result if "universal" in str(f)]
        assert len(universal_files) > 0

        # Should NOT include platform-specific files
        platform_files = [
            f for f in result if "linux.yaml" in str(f) or "mac.yaml" in str(f)
        ]
        assert len(platform_files) == 0


def test_list_conda_environment_defs_filters_non_files():
    """Test list_conda_environment_defs filters out non-file items.

    This tests the bug fix from deploy.py:124 where the list comprehension
    filters to only include files.
    """
    result = list_conda_environment_defs()

    # All items should be files (or may not exist in test environment)
    for item in result:
        # Item should either be a file or not exist
        # (it might not exist if we're testing in an environment without the files)
        if item.exists():
            assert item.is_file(), f"{item} exists but is not a file"


def test_list_conda_environment_defs_sorted():
    """Test list_conda_environment_defs returns sorted results."""
    result = list_conda_environment_defs()

    # Universal files should be sorted
    universal_files = [f for f in result if "universal" in str(f)]
    assert universal_files == sorted(universal_files)


def test_list_conda_environment_defs_glob_pattern():
    """Test glob pattern matches *.yaml files in universal directory."""
    result = list_conda_environment_defs()

    # All universal files should end with .yaml
    universal_files = [f for f in result if "universal" in str(f)]
    for item in universal_files:
        assert item.suffix == ".yaml", f"{item} does not end with .yaml"


def test_list_conda_environment_defs_includes_expected_files():
    """Test list_conda_environment_defs includes expected files."""
    result = list_conda_environment_defs()

    # Convert to string paths for easier checking
    result_strs = [str(f) for f in result]

    # Should include some expected universal files
    # (these files should exist in the actual repository)
    expected_universal = ["conda.yaml", "python.yaml", "unix.yaml"]
    for expected_file in expected_universal:
        matching = [f for f in result_strs if expected_file in f]
        assert len(matching) == 1, f"Expected to find {expected_file} exactly once"


def test_list_conda_environment_defs_platform_file_appended_last():
    """Test platform-specific file is appended after universal files."""
    result = list_conda_environment_defs()

    if not result:
        pytest.skip("No environment definitions found")

    # Last file should be platform-specific
    last_file = result[-1]
    is_platform_specific = "linux.yaml" in str(last_file) or "mac.yaml" in str(
        last_file
    )

    # On Linux or Darwin, should be platform-specific
    if sys.platform in ("linux", "darwin"):
        assert is_platform_specific, f"Last file {last_file} is not platform-specific"


def test_list_conda_environment_defs_no_duplicates():
    """Test list_conda_environment_defs doesn't include duplicates."""
    result = list_conda_environment_defs()

    # No duplicates
    assert len(result) == len(set(result))


def test_defs_dir_structure():
    """Test DEFS_DIR points to expected directory structure."""
    # DEFS_DIR should be resources/defs
    assert DEFS_DIR.name == "defs"
    assert DEFS_DIR.parent.name == "resources"

    # Should have universal subdirectory
    universal_dir = DEFS_DIR / "universal"
    assert universal_dir.exists(), "universal directory should exist"
    assert universal_dir.is_dir(), "universal should be a directory"


def test_universal_yaml_files_exist():
    """Test universal/*.yaml files actually exist."""
    universal_dir = DEFS_DIR / "universal"
    yaml_files = list(universal_dir.glob("*.yaml"))

    # Should have at least some yaml files
    assert len(yaml_files) > 0, "Should have at least one universal YAML file"

    # All should be files
    for f in yaml_files:
        assert f.is_file(), f"{f} is not a file"


def test_platform_specific_files_exist():
    """Test platform-specific YAML files exist."""
    # Linux file should exist
    linux_yaml = DEFS_DIR / "linux" / "linux.yaml"
    if linux_yaml.exists():
        assert linux_yaml.is_file()

    # Mac file should exist
    mac_yaml = DEFS_DIR / "mac" / "mac.yaml"
    if mac_yaml.exists():
        assert mac_yaml.is_file()

    # At least one should exist
    assert (
        linux_yaml.exists() or mac_yaml.exists()
    ), "At least one platform-specific file should exist"


def test_list_iteration_bug_fixed():
    """Test that the list iteration bug (modifying list while iterating) is fixed.

    The original bug was:
        for item in worklist:
            if not item.is_file():
                worklist.remove(item)  # BUG!

    The fix is:
        worklist = [item for item in worklist if item.is_file()]
    """
    # This is more of a regression test - if the function works, the bug is fixed
    result = list_conda_environment_defs()

    # Function should complete without error
    assert isinstance(result, list)

    # All items should be files
    for item in result:
        if item.exists():
            assert item.is_file()
