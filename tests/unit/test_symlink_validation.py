"""
Unit tests for symlink validation functionality.
"""

import pytest

from scripts.engine.validators import SymlinkValidationError, validate_symlink_target


def test_validate_symlink_target_valid_symlink(tmp_path):
    """Test validation of a valid symlink pointing to expected target."""
    target_dir = tmp_path / "blue"
    target_dir.mkdir()

    symlink = tmp_path / "staging"
    symlink.symlink_to("blue")

    # Should pass validation
    assert validate_symlink_target(symlink, ["blue", "green"], check_exists=True)


def test_validate_symlink_target_multiple_expected(tmp_path):
    """Test validation with multiple expected target names."""
    target_dir = tmp_path / "green"
    target_dir.mkdir()

    symlink = tmp_path / "production"
    symlink.symlink_to("green")

    # Should pass validation with both blue and green as expected
    assert validate_symlink_target(symlink, ["blue", "green"], check_exists=True)


def test_validate_symlink_target_not_a_symlink(tmp_path):
    """Test validation fails when path is not a symlink."""
    regular_file = tmp_path / "not_a_symlink"
    regular_file.touch()

    with pytest.raises(SymlinkValidationError) as exc_info:
        validate_symlink_target(regular_file, ["blue", "green"])

    assert "not a symlink" in str(exc_info.value).lower()


def test_validate_symlink_target_does_not_exist(tmp_path):
    """Test validation fails when path does not exist."""
    nonexistent = tmp_path / "doesnt_exist"

    with pytest.raises(SymlinkValidationError) as exc_info:
        validate_symlink_target(nonexistent, ["blue", "green"])

    assert "does not exist" in str(exc_info.value).lower()


def test_validate_symlink_target_wrong_target(tmp_path):
    """Test validation fails when symlink points to unexpected target."""
    target_dir = tmp_path / "purple"
    target_dir.mkdir()

    symlink = tmp_path / "staging"
    symlink.symlink_to("purple")

    with pytest.raises(SymlinkValidationError) as exc_info:
        validate_symlink_target(symlink, ["blue", "green"], check_exists=True)

    error_msg = str(exc_info.value)
    assert "purple" in error_msg
    assert "expected one of" in error_msg.lower()


def test_validate_symlink_target_dangling_symlink_with_check(tmp_path):
    """Test validation fails for dangling symlink when check_exists=True."""
    symlink = tmp_path / "staging"
    # Create symlink to non-existent target
    symlink.symlink_to("nonexistent_target")

    with pytest.raises(SymlinkValidationError) as exc_info:
        validate_symlink_target(symlink, ["nonexistent_target"], check_exists=True)

    error_msg = str(exc_info.value)
    assert "non-existent" in error_msg.lower()


def test_validate_symlink_target_dangling_symlink_without_check(tmp_path):
    """Test validation passes for dangling symlink when check_exists=False."""
    symlink = tmp_path / "staging"
    # Create symlink to non-existent target
    symlink.symlink_to("blue")

    # Should pass when check_exists=False (doesn't verify target exists)
    assert validate_symlink_target(symlink, ["blue"], check_exists=False)


def test_validate_symlink_target_relative_path(tmp_path):
    """Test validation works with relative symlink paths."""
    target_dir = tmp_path / "blue"
    target_dir.mkdir()

    symlink = tmp_path / "staging"
    # Use relative path for symlink
    symlink.symlink_to("blue")

    assert validate_symlink_target(symlink, ["blue"], check_exists=True)


def test_validate_symlink_target_absolute_path(tmp_path):
    """Test validation works with absolute symlink paths."""
    target_dir = tmp_path / "green"
    target_dir.mkdir()

    symlink = tmp_path / "staging"
    # Use absolute path for symlink
    symlink.symlink_to(target_dir)

    # Validation should extract the target name from the path
    assert validate_symlink_target(symlink, ["green"], check_exists=True)


def test_validate_symlink_target_nested_path(tmp_path):
    """Test validation with nested directory structures."""
    # Create nested structure
    infrastructure = tmp_path / "infrastructure"
    infrastructure.mkdir()

    target_dir = infrastructure / "blue"
    target_dir.mkdir()

    symlink = infrastructure / "staging"
    symlink.symlink_to("blue")

    assert validate_symlink_target(symlink, ["blue", "green"], check_exists=True)


def test_validate_symlink_target_directory_as_target(tmp_path):
    """Test that symlink can point to a directory and validation works."""
    target_dir = tmp_path / "blue"
    target_dir.mkdir()

    # Create some content in the target directory
    (target_dir / "test.txt").touch()

    symlink = tmp_path / "staging"
    symlink.symlink_to("blue")

    assert validate_symlink_target(symlink, ["blue"], check_exists=True)


def test_validate_symlink_target_single_expected(tmp_path):
    """Test validation with only one expected target name."""
    target_dir = tmp_path / "engine_a"
    target_dir.mkdir()

    symlink = tmp_path / "engine"
    symlink.symlink_to("engine_a")

    assert validate_symlink_target(symlink, ["engine_a"], check_exists=True)


def test_validate_symlink_target_engine_rotation(tmp_path):
    """Test validation for engine rotation scenario (engine_a/engine_b)."""
    engine_a = tmp_path / "engine_a"
    engine_b = tmp_path / "engine_b"
    engine_a.mkdir()
    engine_b.mkdir()

    engine_link = tmp_path / "engine"
    engine_link.symlink_to("engine_a")

    # Validate current engine points to valid target
    assert validate_symlink_target(
        engine_link, ["engine_a", "engine_b"], check_exists=True
    )

    # Simulate rotation
    engine_link.unlink()
    engine_link.symlink_to("engine_b")

    # Validate new engine target
    assert validate_symlink_target(
        engine_link, ["engine_a", "engine_b"], check_exists=True
    )


def test_validate_symlink_target_invalid_target_name_format(tmp_path):
    """Test validation fails gracefully with unusual target names."""
    target_dir = tmp_path / "weird-name_123"
    target_dir.mkdir()

    symlink = tmp_path / "link"
    symlink.symlink_to("weird-name_123")

    # Should fail because target name doesn't match expected
    with pytest.raises(SymlinkValidationError) as exc_info:
        validate_symlink_target(symlink, ["blue", "green"], check_exists=True)

    assert "weird-name_123" in str(exc_info.value)


def test_validate_symlink_target_empty_expected_list(tmp_path):
    """Test validation behavior with empty expected list."""
    target_dir = tmp_path / "blue"
    target_dir.mkdir()

    symlink = tmp_path / "staging"
    symlink.symlink_to("blue")

    # Should fail because no targets are expected
    with pytest.raises(SymlinkValidationError) as exc_info:
        validate_symlink_target(symlink, [], check_exists=True)

    assert "expected one of" in str(exc_info.value).lower()


def test_validate_symlink_target_symlink_chain(tmp_path):
    """Test validation with chained symlinks (symlink -> symlink -> directory)."""
    target_dir = tmp_path / "blue"
    target_dir.mkdir()

    intermediate_link = tmp_path / "intermediate"
    intermediate_link.symlink_to("blue")

    final_link = tmp_path / "staging"
    final_link.symlink_to("intermediate")

    # Validation should check the immediate target, not the final resolved target
    # So this should fail because we're looking for "blue" but immediate target is "intermediate"
    with pytest.raises(SymlinkValidationError):
        validate_symlink_target(final_link, ["blue"], check_exists=True)

    # But it should pass if we expect "intermediate"
    assert validate_symlink_target(final_link, ["intermediate"], check_exists=True)


def test_validate_symlink_target_case_sensitive(tmp_path):
    """Test that validation is case-sensitive."""
    target_dir = tmp_path / "Blue"
    target_dir.mkdir()

    symlink = tmp_path / "staging"
    symlink.symlink_to("Blue")

    # Should fail because "Blue" != "blue"
    with pytest.raises(SymlinkValidationError):
        validate_symlink_target(symlink, ["blue"], check_exists=True)

    # Should pass with correct case
    assert validate_symlink_target(symlink, ["Blue"], check_exists=True)
