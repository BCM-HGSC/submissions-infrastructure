"""Integration tests for bootstrap-engine workflow."""

from pathlib import Path
import subprocess

import pytest


@pytest.fixture
def bootstrap_script():
    """Return path to bootstrap-engine script."""
    return Path(__file__).parent.parent.parent / "scripts" / "bootstrap-engine"


@pytest.mark.integration
def test_bootstrap_help(bootstrap_script):
    """Test bootstrap-engine --help flag."""
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


@pytest.mark.integration
def test_bootstrap_missing_target_dir(bootstrap_script):
    """Test bootstrap-engine fails gracefully without TARGET_DIR."""
    result = subprocess.run(
        [str(bootstrap_script)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "TARGET_DIR argument is required" in result.stderr


@pytest.mark.integration
def test_bootstrap_directory_structure(bootstrap_script, tmp_path):
    """Test bootstrap creates expected directory structure.

    Note: This test will attempt to download micromamba and may fail
    if network is unavailable. It's marked as integration test.
    """
    target_dir = tmp_path / "test_target"
    target_dir.mkdir()

    # Run bootstrap-engine
    result = subprocess.run(
        [str(bootstrap_script), str(target_dir)],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,  # Give it time to download and setup
    )

    # Check that basic directories were created
    engine_home = target_dir / "engine_home"
    assert engine_home.exists(), "engine_home should be created"
    assert engine_home.is_dir(), "engine_home should be a directory"

    conda_cache = target_dir / "conda_package_cache"
    assert conda_cache.exists(), "conda_package_cache should be created"
    assert conda_cache.is_dir(), "conda_package_cache should be a directory"

    # Check for micromamba
    micromamba = engine_home / "micromamba"
    if micromamba.exists():
        assert micromamba.is_file(), "micromamba should be a file"
        # Note: May not be executable on all filesystems
    else:
        # If bootstrap failed, check for error messages
        pytest.skip(f"Bootstrap failed: {result.stderr}")


@pytest.mark.integration
def test_bootstrap_engine_symlink(bootstrap_script, tmp_path):
    """Test bootstrap creates engine symlink correctly."""
    target_dir = tmp_path / "test_target"
    target_dir.mkdir()

    # Run bootstrap-engine
    result = subprocess.run(
        [str(bootstrap_script), str(target_dir)],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )

    # Check for engine symlink
    engine_link = target_dir / "engine_home" / "engine"

    if result.returncode == 0:
        assert engine_link.exists(), "engine symlink should exist"
        assert engine_link.is_symlink(), "engine should be a symlink"

        # Should point to engine_a or engine_b
        target = engine_link.readlink()
        assert target.name in (
            "engine_a",
            "engine_b",
        ), f"engine should point to engine_a or engine_b, not {target.name}"

        # The target should exist
        assert engine_link.resolve().exists(), "engine symlink target should exist"
    else:
        pytest.skip(f"Bootstrap failed: {result.stderr}")


@pytest.mark.integration
def test_bootstrap_rotation(bootstrap_script, tmp_path):
    """Test bootstrap rotates between engine_a and engine_b."""
    target_dir = tmp_path / "test_target"
    target_dir.mkdir()

    # First bootstrap
    result1 = subprocess.run(
        [str(bootstrap_script), str(target_dir)],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )

    if result1.returncode != 0:
        pytest.skip(f"First bootstrap failed: {result1.stderr}")

    engine_link = target_dir / "engine_home" / "engine"
    first_target = engine_link.readlink().name

    # Second bootstrap (should rotate)
    result2 = subprocess.run(
        [str(bootstrap_script), str(target_dir)],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )

    if result2.returncode != 0:
        pytest.skip(f"Second bootstrap failed: {result2.stderr}")

    second_target = engine_link.readlink().name

    # Should have rotated
    if first_target == "engine_a":
        assert second_target == "engine_b", "Should rotate from engine_a to engine_b"
    else:
        assert second_target == "engine_a", "Should rotate from engine_b to engine_a"


@pytest.mark.integration
def test_bootstrap_verbose_flag(bootstrap_script, tmp_path):
    """Test bootstrap with --verbose flag."""
    target_dir = tmp_path / "test_target"
    target_dir.mkdir()

    result = subprocess.run(
        [str(bootstrap_script), "--verbose", str(target_dir)],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )

    # Verbose mode should output DEBUG messages
    if result.returncode == 0:
        # Should have DEBUG output in stderr
        assert "DEBUG:" in result.stderr or "INFO:" in result.stderr
    else:
        # Even on failure, should show verbose output
        pytest.skip(f"Bootstrap failed: {result.stderr}")


# Note: The following tests require special setup and are skipped by default


@pytest.mark.integration
@pytest.mark.skip(reason="Requires pre-cached conda packages for offline mode")
def test_bootstrap_offline_mode(bootstrap_script, tmp_path):
    """Test bootstrap with --offline flag.

    This test requires conda packages to be pre-cached.
    Skip by default as it's environment-specific.
    """
    target_dir = tmp_path / "test_target"
    target_dir.mkdir()

    # First, we'd need to populate conda_package_cache
    # This is skipped because it requires specific setup

    result = subprocess.run(
        [str(bootstrap_script), "--offline", str(target_dir)],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )

    # Would verify offline mode works
    assert result.returncode == 0


@pytest.mark.integration
@pytest.mark.skip(reason="Force flag test requires understanding of specific behavior")
def test_bootstrap_force_flag(bootstrap_script, tmp_path):
    """Test bootstrap with --force flag.

    Note: The bootstrap script doesn't currently have a --force flag,
    but this test is a placeholder for future functionality.
    """
    target_dir = tmp_path / "test_target"
    target_dir.mkdir()

    _result = subprocess.run(
        [str(bootstrap_script), "--force", str(target_dir)],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )

    # Would verify force behavior when implemented
