"""Unit tests for promote_staging script."""

from importlib.machinery import SourceFileLoader
import importlib.util
from pathlib import Path
import sys

import pytest

# Load the promote_staging script as a module
# (It doesn't have a .py extension, so we need to load it manually)
_script_path = str(Path(__file__).parent.parent.parent / "scripts" / "promote_staging")
_loader = SourceFileLoader("promote_staging", _script_path)
_spec = importlib.util.spec_from_file_location(
    "promote_staging", _script_path, loader=_loader
)
_promote_staging = importlib.util.module_from_spec(_spec)
sys.modules["promote_staging"] = _promote_staging
_spec.loader.exec_module(_promote_staging)

# Import the functions we need
BLUE_GREEN_TRANSITIONS = _promote_staging.BLUE_GREEN_TRANSITIONS
validate_color = _promote_staging.validate_color
get_opposite_color = _promote_staging.get_opposite_color
validate_and_get_color = _promote_staging.validate_and_get_color


def test_validate_color_blue():
    """Test validate_color accepts 'blue'."""
    assert validate_color("blue") is True


def test_validate_color_green():
    """Test validate_color accepts 'green'."""
    assert validate_color("green") is True


def test_validate_color_invalid():
    """Test validate_color rejects invalid colors."""
    assert validate_color("red") is False
    assert validate_color("staging") is False
    assert validate_color("production") is False
    assert validate_color("") is False
    assert validate_color("Blue") is False  # Case sensitive


def test_get_opposite_color_blue():
    """Test get_opposite_color returns green for blue."""
    assert get_opposite_color("blue") == "green"


def test_get_opposite_color_green():
    """Test get_opposite_color returns blue for green."""
    assert get_opposite_color("green") == "blue"


def test_get_opposite_color_invalid():
    """Test get_opposite_color raises KeyError for invalid color."""
    with pytest.raises(KeyError):
        get_opposite_color("red")

    with pytest.raises(KeyError):
        get_opposite_color("staging")


def test_blue_green_transitions_dictionary():
    """Test BLUE_GREEN_TRANSITIONS dictionary structure."""
    assert "blue" in BLUE_GREEN_TRANSITIONS
    assert "green" in BLUE_GREEN_TRANSITIONS
    assert BLUE_GREEN_TRANSITIONS["blue"] == "green"
    assert BLUE_GREEN_TRANSITIONS["green"] == "blue"
    assert len(BLUE_GREEN_TRANSITIONS) == 2


def test_validate_and_get_color_blue_symlink(tmp_path):
    """Test validate_and_get_color with symlink pointing to blue."""
    # Create blue directory
    infrastructure = tmp_path / "infrastructure"
    blue_dir = infrastructure / "blue"
    blue_dir.mkdir(parents=True)

    # Create staging symlink pointing to blue
    staging_link = infrastructure / "staging"
    staging_link.symlink_to("blue")

    color = validate_and_get_color(staging_link, infrastructure)

    assert color == "blue"


def test_validate_and_get_color_green_symlink(tmp_path):
    """Test validate_and_get_color with symlink pointing to green."""
    # Create green directory
    infrastructure = tmp_path / "infrastructure"
    green_dir = infrastructure / "green"
    green_dir.mkdir(parents=True)

    # Create production symlink pointing to green
    prod_link = infrastructure / "production"
    prod_link.symlink_to("green")

    color = validate_and_get_color(prod_link, infrastructure)

    assert color == "green"


def test_validate_and_get_color_not_a_symlink_file(tmp_path):
    """Test validate_and_get_color exits when path is a regular file."""
    # Create a regular file instead of a symlink
    infrastructure = tmp_path / "infrastructure"
    infrastructure.mkdir()
    test_file = infrastructure / "staging"
    test_file.write_text("not a symlink")

    with pytest.raises(SystemExit):
        validate_and_get_color(test_file, infrastructure)


def test_validate_and_get_color_not_a_symlink_directory(tmp_path):
    """Test validate_and_get_color exits when path is a directory."""
    # Create a regular directory instead of a symlink
    infrastructure = tmp_path / "infrastructure"
    infrastructure.mkdir()
    test_dir = infrastructure / "staging"
    test_dir.mkdir()

    with pytest.raises(SystemExit):
        validate_and_get_color(test_dir, infrastructure)


def test_validate_and_get_color_broken_symlink(tmp_path):
    """Test validate_and_get_color exits when symlink is broken."""
    # Create a symlink to a nonexistent target
    infrastructure = tmp_path / "infrastructure"
    infrastructure.mkdir()
    broken_link = infrastructure / "staging"
    broken_link.symlink_to("nonexistent")

    with pytest.raises(SystemExit):
        validate_and_get_color(broken_link, infrastructure)


def test_validate_and_get_color_invalid_target(tmp_path):
    """Test validate_and_get_color exits when symlink points to invalid color."""
    # Create a directory with invalid color name
    infrastructure = tmp_path / "infrastructure"
    invalid_dir = infrastructure / "red"
    invalid_dir.mkdir(parents=True)

    # Create symlink pointing to invalid color
    test_link = infrastructure / "staging"
    test_link.symlink_to("red")

    with pytest.raises(SystemExit):
        validate_and_get_color(test_link, infrastructure)


def test_validate_and_get_color_symlink_to_staging(tmp_path):
    """Test validate_and_get_color rejects symlink to 'staging'."""
    # Create staging directory
    infrastructure = tmp_path / "infrastructure"
    staging_dir = infrastructure / "staging"
    staging_dir.mkdir(parents=True)

    # Create a symlink pointing to staging (invalid)
    test_link = infrastructure / "test"
    test_link.symlink_to("staging")

    with pytest.raises(SystemExit):
        validate_and_get_color(test_link, infrastructure)


def test_validate_and_get_color_with_absolute_symlink(tmp_path):
    """Test validate_and_get_color works with absolute path symlink."""
    # Create blue directory
    infrastructure = tmp_path / "infrastructure"
    blue_dir = infrastructure / "blue"
    blue_dir.mkdir(parents=True)

    # Create staging symlink with absolute path
    staging_link = infrastructure / "staging"
    staging_link.symlink_to(blue_dir)

    color = validate_and_get_color(staging_link, infrastructure)

    # readlink().name should still extract "blue" from the absolute path
    assert color == "blue"


def test_validate_color_is_pure_function():
    """Test that validate_color is deterministic and has no side effects."""
    # Call multiple times with same input
    result1 = validate_color("blue")
    result2 = validate_color("blue")
    result3 = validate_color("blue")

    assert result1 == result2 == result3 is True

    # Test with invalid input
    result4 = validate_color("invalid")
    result5 = validate_color("invalid")

    assert result4 == result5 is False


def test_get_opposite_color_is_pure_function():
    """Test that get_opposite_color is deterministic and has no side effects."""
    # Call multiple times with same input
    result1 = get_opposite_color("blue")
    result2 = get_opposite_color("blue")
    result3 = get_opposite_color("blue")

    assert result1 == result2 == result3 == "green"
