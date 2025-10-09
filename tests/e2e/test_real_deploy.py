"""End-to-end tests for deploy workflow with real mamba installation.

These tests require:
- Real mamba/micromamba in PATH
- The --run-e2e flag
- Longer execution time (5-10+ minutes for comprehensive tests)

Run with: pytest --run-e2e tests/e2e/test_real_deploy.py
"""

from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from scripts.engine.command_runner import RealCommandRunner
from scripts.engine.deploy import DEFS_DIR, deploy_tier
from scripts.engine.filesystem import RealFileSystem


@pytest.fixture(scope="session", autouse=True)
def check_mamba_available():
    """Check that mamba is available in PATH before running E2E tests."""
    if not shutil.which("mamba"):
        pytest.exit("E2E tests require mamba in PATH. Install mamba/micromamba first.")


@pytest.fixture
def e2e_bootstrap_env(tmp_path):
    """Create a bootstrapped environment for E2E testing.

    This runs the actual bootstrap-engine script to create a real deployment
    environment with a working mamba installation.
    """
    target_dir = tmp_path / "e2e_target"
    target_dir.mkdir()

    # Run bootstrap-engine script
    bootstrap_script = (
        Path(__file__).parent.parent.parent / "scripts" / "bootstrap-engine"
    )

    result = subprocess.run(
        [str(bootstrap_script), str(target_dir)],
        capture_output=True,
        text=True,
        check=False,
        timeout=300,  # 5 minutes for bootstrap
    )

    if result.returncode != 0:
        pytest.fail(f"Bootstrap failed for E2E test: {result.stderr}")

    return target_dir


# Helper function to get environment definitions
def get_universal_envs():
    """Get universal environment definitions."""
    universal_dir = DEFS_DIR / "universal"
    return sorted(universal_dir.glob("*.yaml"))


def get_platform_env():
    """Get platform-specific environment definition."""
    if sys.platform == "linux":
        return DEFS_DIR / "linux" / "linux.yaml"
    if sys.platform == "darwin":
        return DEFS_DIR / "mac" / "mac.yaml"
    return None


def get_quick_test_envs():
    """Get subset of environments for quick E2E test (excludes python.yaml)."""
    envs = []
    universal_dir = DEFS_DIR / "universal"

    # Add specific universal environments, excluding python.yaml
    for env_name in ["conda.yaml", "unix.yaml"]:
        env_path = universal_dir / env_name
        if env_path.exists():
            envs.append(env_path)

    # Add platform-specific environment
    platform_env = get_platform_env()
    if platform_env and platform_env.exists():
        envs.append(platform_env)

    return envs


def get_all_envs():
    """Get all environment definitions (comprehensive test)."""
    envs = list(get_universal_envs())
    platform_env = get_platform_env()
    if platform_env and platform_env.exists():
        envs.append(platform_env)
    return envs


@pytest.mark.e2e
def test_quick_deploy_subset(e2e_bootstrap_env):
    """Quick E2E test: Deploy subset of environments (excludes python.yaml)."""
    filesystem = RealFileSystem()
    command_runner = RealCommandRunner()

    # Get subset of environments for quick test
    env_yamls = get_quick_test_envs()

    assert len(env_yamls) >= 2, "Should have at least 2 environments for quick test"

    # Deploy to staging tier with subset
    deploy_tier(
        target=e2e_bootstrap_env,
        tier="staging",
        dry_run=False,
        offline=False,
        filesystem=filesystem,
        command_runner=command_runner,
        env_yamls=env_yamls,
    )

    # Verify directory structure
    staging_dir = e2e_bootstrap_env / "infrastructure" / "staging"
    assert staging_dir.exists(), "staging directory should exist"
    assert staging_dir.is_dir(), "staging should be a directory"

    # Verify conda environments were created
    envs_dir = staging_dir / "conda" / "envs"
    assert envs_dir.exists(), "conda/envs directory should exist"

    created_envs = list(envs_dir.iterdir())
    assert (
        len(created_envs) >= 2
    ), f"Should create at least 2 environments, got {len(created_envs)}"

    # Verify specific environments exist
    env_names = [env.stem for env in env_yamls]
    for env_name in env_names:
        env_path = envs_dir / env_name
        assert env_path.exists(), f"Environment {env_name} should be created"

    # Verify bin and etc directories copied
    assert (staging_dir / "bin").exists(), "bin directory should be copied"
    assert (staging_dir / "etc").exists(), "etc directory should be copied"

    # Verify git metadata stored
    meta_dir = staging_dir / "meta"
    assert meta_dir.exists(), "meta directory should exist"
    assert (meta_dir / "commit").exists(), "commit metadata should exist"
    assert (meta_dir / "tree_hash").exists(), "tree_hash metadata should exist"
    assert (meta_dir / "description").exists(), "description metadata should exist"


@pytest.mark.e2e
@pytest.mark.slow
def test_comprehensive_deploy_all_environments(e2e_bootstrap_env):
    """Comprehensive E2E test: Deploy all environments including python.yaml.

    This test may take 5-10+ minutes depending on environment size.
    """
    filesystem = RealFileSystem()
    command_runner = RealCommandRunner()

    # Get all environment definitions
    env_yamls = get_all_envs()

    assert len(env_yamls) >= 3, "Should have at least 3 environments"

    # Verify python.yaml is included
    env_names = [env.stem for env in env_yamls]
    assert "python" in env_names, "python.yaml should be included in comprehensive test"

    # Deploy to staging tier with all environments
    deploy_tier(
        target=e2e_bootstrap_env,
        tier="staging",
        dry_run=False,
        offline=False,
        filesystem=filesystem,
        command_runner=command_runner,
        env_yamls=env_yamls,
    )

    # Verify all environments were created
    staging_dir = e2e_bootstrap_env / "infrastructure" / "staging"
    envs_dir = staging_dir / "conda" / "envs"

    for env_name in env_names:
        env_path = envs_dir / env_name
        assert env_path.exists(), f"Environment {env_name} should be created"
        assert env_path.is_dir(), f"Environment {env_name} should be a directory"

        # Verify environment has basic structure
        conda_meta = env_path / "conda-meta"
        assert conda_meta.exists(), f"{env_name} should have conda-meta directory"


@pytest.mark.e2e
@pytest.mark.skipif(sys.platform != "darwin", reason="macOS-specific test")
def test_deploy_mac_environment(e2e_bootstrap_env):
    """Test deploying macOS-specific environment."""
    filesystem = RealFileSystem()
    command_runner = RealCommandRunner()

    mac_yaml = DEFS_DIR / "mac" / "mac.yaml"
    assert mac_yaml.exists(), "mac.yaml should exist"

    deploy_tier(
        target=e2e_bootstrap_env,
        tier="staging",
        dry_run=False,
        offline=False,
        filesystem=filesystem,
        command_runner=command_runner,
        env_yamls=[mac_yaml],
    )

    staging_dir = e2e_bootstrap_env / "infrastructure" / "staging"
    mac_env = staging_dir / "conda" / "envs" / "mac"

    assert mac_env.exists(), "mac environment should be created"
    assert mac_env.is_dir(), "mac environment should be a directory"


@pytest.mark.e2e
@pytest.mark.skipif(sys.platform != "linux", reason="Linux-specific test")
def test_deploy_linux_environment(e2e_bootstrap_env):
    """Test deploying Linux-specific environment."""
    filesystem = RealFileSystem()
    command_runner = RealCommandRunner()

    linux_yaml = DEFS_DIR / "linux" / "linux.yaml"
    assert linux_yaml.exists(), "linux.yaml should exist"

    deploy_tier(
        target=e2e_bootstrap_env,
        tier="staging",
        dry_run=False,
        offline=False,
        filesystem=filesystem,
        command_runner=command_runner,
        env_yamls=[linux_yaml],
    )

    staging_dir = e2e_bootstrap_env / "infrastructure" / "staging"
    linux_env = staging_dir / "conda" / "envs" / "linux"

    assert linux_env.exists(), "linux environment should be created"
    assert linux_env.is_dir(), "linux environment should be a directory"


@pytest.mark.e2e
def test_deploy_dry_run_mode(e2e_bootstrap_env):
    """Test that --dry-run mode doesn't create actual environments."""
    filesystem = RealFileSystem()
    command_runner = RealCommandRunner()

    env_yamls = get_quick_test_envs()

    deploy_tier(
        target=e2e_bootstrap_env,
        tier="staging",
        dry_run=True,
        offline=False,
        filesystem=filesystem,
        command_runner=command_runner,
        env_yamls=env_yamls,
    )

    staging_dir = e2e_bootstrap_env / "infrastructure" / "staging"

    # Directory should be created
    assert staging_dir.exists(), "staging directory created even in dry-run"

    # But bin, etc, and meta should NOT be deployed in dry-run
    assert not (staging_dir / "bin").exists(), "bin should not be deployed in dry-run"
    assert not (staging_dir / "etc").exists(), "etc should not be deployed in dry-run"
    assert not (staging_dir / "meta").exists(), "meta should not be deployed in dry-run"


@pytest.mark.e2e
def test_deploy_keep_mode_preserves_environments(e2e_bootstrap_env):
    """Test that --keep mode preserves existing environments."""
    filesystem = RealFileSystem()
    command_runner = RealCommandRunner()

    env_yamls = get_quick_test_envs()

    # First deployment
    deploy_tier(
        target=e2e_bootstrap_env,
        tier="staging",
        dry_run=False,
        offline=False,
        filesystem=filesystem,
        command_runner=command_runner,
        env_yamls=env_yamls,
    )

    staging_dir = e2e_bootstrap_env / "infrastructure" / "staging"
    envs_dir = staging_dir / "conda" / "envs"

    # Record environment creation times
    first_deploy_times = {}
    for env_path in envs_dir.iterdir():
        if env_path.is_dir():
            first_deploy_times[env_path.name] = env_path.stat().st_mtime

    # Second deployment with keep mode
    deploy_tier(
        target=e2e_bootstrap_env,
        tier="staging",
        dry_run=False,
        offline=False,
        mode="keep",
        filesystem=filesystem,
        command_runner=command_runner,
        env_yamls=env_yamls,
    )

    # Verify environments were not recreated (same mtime)
    for env_name, original_mtime in first_deploy_times.items():
        env_path = envs_dir / env_name
        assert env_path.exists(), f"Environment {env_name} should still exist"
        current_mtime = env_path.stat().st_mtime
        assert (
            current_mtime == original_mtime
        ), f"Environment {env_name} should not be recreated in keep mode"


@pytest.mark.e2e
def test_deploy_stores_real_git_metadata(e2e_bootstrap_env):
    """Test that deployment stores real git metadata (not mocked)."""
    filesystem = RealFileSystem()
    command_runner = RealCommandRunner()

    env_yamls = get_quick_test_envs()

    deploy_tier(
        target=e2e_bootstrap_env,
        tier="staging",
        dry_run=False,
        offline=False,
        filesystem=filesystem,
        command_runner=command_runner,
        env_yamls=env_yamls,
    )

    staging_dir = e2e_bootstrap_env / "infrastructure" / "staging"
    meta_dir = staging_dir / "meta"

    # Verify git metadata files exist
    commit_file = meta_dir / "commit"
    tree_hash_file = meta_dir / "tree_hash"
    description_file = meta_dir / "description"

    assert commit_file.exists(), "commit metadata should exist"
    assert tree_hash_file.exists(), "tree_hash metadata should exist"
    assert description_file.exists(), "description metadata should exist"

    # Verify content is real git data (not mock strings)
    commit_content = commit_file.read_text().strip()
    tree_hash_content = tree_hash_file.read_text().strip()
    description_content = description_file.read_text().strip()

    # Real git commits are 40 hex characters
    assert len(commit_content) == 40, "commit should be a valid git SHA"
    assert commit_content.isalnum(), "commit should be alphanumeric"
    assert "mock" not in commit_content.lower(), "should not contain mock data"

    # Tree hash is also 40 hex characters
    assert len(tree_hash_content) == 40, "tree_hash should be a valid git SHA"
    assert tree_hash_content.isalnum(), "tree_hash should be alphanumeric"
    assert "mock" not in tree_hash_content.lower(), "should not contain mock data"

    # Description should be a real git description
    assert len(description_content) > 0, "description should not be empty"
    assert "mock" not in description_content.lower(), "should not contain mock data"
