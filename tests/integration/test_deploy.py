"""Integration tests for deploy workflow."""

from pathlib import Path
import subprocess
from unittest.mock import MagicMock

import pytest

from scripts.engine.command_runner import RealCommandRunner
from scripts.engine.deploy import deploy_tier
from scripts.engine.filesystem import RealFileSystem


@pytest.fixture
def deploy_test_env(tmp_path):
    """Create a minimal deployment test environment.

    This creates the necessary directory structure and installs
    a minimal engine environment for testing deploy functionality.
    """
    target_dir = tmp_path / "test_deploy"
    target_dir.mkdir()

    # Create necessary directories
    engine_home = target_dir / "engine_home"
    engine_home.mkdir()

    conda_cache = target_dir / "conda_package_cache"
    conda_cache.mkdir()

    infrastructure = target_dir / "infrastructure"
    infrastructure.mkdir()

    # Bootstrap the engine using the bootstrap-engine script
    bootstrap_script = (
        Path(__file__).parent.parent.parent / "scripts" / "bootstrap-engine"
    )

    result = subprocess.run(
        [str(bootstrap_script), str(target_dir)],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )

    if result.returncode != 0:
        pytest.skip(f"Bootstrap failed, cannot test deploy: {result.stderr}")

    return target_dir


@pytest.fixture
def mock_git_command_runner():
    """Create a command runner that mocks git commands but runs real mamba."""

    class GitMockingCommandRunner(RealCommandRunner):
        def run(self, command, **kwargs):
            # Mock git commands
            if command[0] == "git":
                mock_result = MagicMock()
                if "rev-parse" in command:
                    if "HEAD:" in command:
                        mock_result.stdout = b"mock_tree_hash_12345\n"
                    else:
                        mock_result.stdout = b"mock_commit_hash_67890\n"
                elif "describe" in command:
                    mock_result.stdout = b"v1.0.0-test-dirty\n"
                else:
                    mock_result.stdout = b"mock_output\n"
                mock_result.returncode = 0
                return mock_result
            # Run real commands for everything else
            return super().run(command, **kwargs)

    return GitMockingCommandRunner()


@pytest.fixture
def minimal_env_yaml(tmp_path):
    """Create a minimal environment YAML for testing."""
    env_yaml = tmp_path / "test_env.yaml"
    env_yaml.write_text("""name: test_env
channels:
  - conda-forge
dependencies:
  - python=3.11
""")
    return env_yaml


@pytest.mark.integration
def test_deploy_to_staging_creates_structure(deploy_test_env, mock_git_command_runner):
    """Test that deploy creates expected directory structure."""
    filesystem = RealFileSystem()

    # Deploy to staging tier
    deploy_tier(
        target=deploy_test_env,
        tier="staging",
        dry_run=False,
        offline=False,
        filesystem=filesystem,
        command_runner=mock_git_command_runner,
    )

    # Verify directory structure created
    staging_dir = deploy_test_env / "infrastructure" / "staging"
    assert staging_dir.exists(), "staging directory should be created"
    assert staging_dir.is_dir(), "staging should be a directory"

    # Check for conda environments directory
    envs_dir = staging_dir / "conda" / "envs"
    assert envs_dir.exists(), "conda/envs directory should be created"

    # Check for logs directory
    logs_dir = staging_dir / "logs"
    assert logs_dir.exists(), "logs directory should be created"


@pytest.mark.integration
def test_deploy_creates_conda_environments(deploy_test_env, mock_git_command_runner):
    """Test that deploy creates conda environments."""
    filesystem = RealFileSystem()

    # Deploy to staging tier
    deploy_tier(
        target=deploy_test_env,
        tier="staging",
        dry_run=False,
        offline=False,
        filesystem=filesystem,
        command_runner=mock_git_command_runner,
    )

    staging_dir = deploy_test_env / "infrastructure" / "staging"
    envs_dir = staging_dir / "conda" / "envs"

    # Check that at least one environment was created
    # (The actual environments depend on resources/defs/ content)
    created_envs = list(envs_dir.iterdir()) if envs_dir.exists() else []
    assert len(created_envs) > 0, "At least one conda environment should be created"


@pytest.mark.integration
def test_deploy_copies_bin_directory(deploy_test_env, mock_git_command_runner):
    """Test that deploy copies bin/ directory."""
    filesystem = RealFileSystem()

    # Deploy to staging tier
    deploy_tier(
        target=deploy_test_env,
        tier="staging",
        dry_run=False,
        offline=False,
        filesystem=filesystem,
        command_runner=mock_git_command_runner,
    )

    staging_dir = deploy_test_env / "infrastructure" / "staging"
    bin_dir = staging_dir / "bin"

    assert bin_dir.exists(), "bin directory should be copied"
    assert bin_dir.is_dir(), "bin should be a directory"

    # Verify some content was copied
    bin_contents = list(bin_dir.iterdir())
    assert len(bin_contents) > 0, "bin directory should contain files"


@pytest.mark.integration
def test_deploy_copies_etc_directory(deploy_test_env, mock_git_command_runner):
    """Test that deploy copies etc/ directory."""
    filesystem = RealFileSystem()

    # Deploy to staging tier
    deploy_tier(
        target=deploy_test_env,
        tier="staging",
        dry_run=False,
        offline=False,
        filesystem=filesystem,
        command_runner=mock_git_command_runner,
    )

    staging_dir = deploy_test_env / "infrastructure" / "staging"
    etc_dir = staging_dir / "etc"

    assert etc_dir.exists(), "etc directory should be copied"
    assert etc_dir.is_dir(), "etc should be a directory"


@pytest.mark.integration
def test_deploy_stores_git_metadata(deploy_test_env, mock_git_command_runner):
    """Test that deploy stores git metadata with mocked git commands."""
    filesystem = RealFileSystem()

    # Deploy to staging tier
    deploy_tier(
        target=deploy_test_env,
        tier="staging",
        dry_run=False,
        offline=False,
        filesystem=filesystem,
        command_runner=mock_git_command_runner,
    )

    staging_dir = deploy_test_env / "infrastructure" / "staging"
    meta_dir = staging_dir / "meta"

    assert meta_dir.exists(), "meta directory should be created"
    assert meta_dir.is_dir(), "meta should be a directory"

    # Check for git metadata files
    commit_file = meta_dir / "commit"
    tree_hash_file = meta_dir / "tree_hash"
    description_file = meta_dir / "description"

    assert commit_file.exists(), "commit metadata file should exist"
    assert tree_hash_file.exists(), "tree_hash metadata file should exist"
    assert description_file.exists(), "description metadata file should exist"

    # Verify mocked content
    assert b"mock_commit_hash" in commit_file.read_bytes()
    assert b"mock_tree_hash" in tree_hash_file.read_bytes()


@pytest.mark.integration
def test_deploy_dry_run_mode(deploy_test_env, mock_git_command_runner):
    """Test that --dry-run mode doesn't create actual environments."""
    filesystem = RealFileSystem()

    # Deploy in dry-run mode
    deploy_tier(
        target=deploy_test_env,
        tier="staging",
        dry_run=True,
        offline=False,
        filesystem=filesystem,
        command_runner=mock_git_command_runner,
    )

    staging_dir = deploy_test_env / "infrastructure" / "staging"

    # Directory should be created
    assert staging_dir.exists(), "staging directory created even in dry-run"

    # But bin and etc should NOT be deployed in dry-run
    bin_dir = staging_dir / "bin"
    etc_dir = staging_dir / "etc"
    meta_dir = staging_dir / "meta"

    assert not bin_dir.exists(), "bin should not be deployed in dry-run mode"
    assert not etc_dir.exists(), "etc should not be deployed in dry-run mode"
    assert not meta_dir.exists(), "meta should not be stored in dry-run mode"


@pytest.mark.integration
def test_deploy_keep_mode(deploy_test_env, mock_git_command_runner):
    """Test that --keep mode preserves existing environments."""
    filesystem = RealFileSystem()

    # First deployment
    deploy_tier(
        target=deploy_test_env,
        tier="staging",
        dry_run=False,
        offline=False,
        filesystem=filesystem,
        command_runner=mock_git_command_runner,
    )

    staging_dir = deploy_test_env / "infrastructure" / "staging"
    envs_dir = staging_dir / "conda" / "envs"

    # Record which environments exist
    first_deploy_envs = set(envs_dir.iterdir()) if envs_dir.exists() else set()

    # Second deployment with keep mode
    deploy_tier(
        target=deploy_test_env,
        tier="staging",
        dry_run=False,
        offline=False,
        mode="keep",
        filesystem=filesystem,
        command_runner=mock_git_command_runner,
    )

    # Environments should still exist (not recreated)
    second_deploy_envs = set(envs_dir.iterdir()) if envs_dir.exists() else set()

    # Should have same environments
    assert (
        first_deploy_envs == second_deploy_envs
    ), "keep mode should preserve environments"
