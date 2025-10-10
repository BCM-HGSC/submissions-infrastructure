"""End-to-end test for full deployment workflow with real resources.

This test implements a complete deployment lifecycle:
- Bootstrap engine
- Deploy to staging
- Promote staging to production
- Deploy new staging
- Test engine rotation

Requires:
- Real mamba/micromamba in PATH
- The --run-e2e flag
- Longer execution time (5-10+ minutes)

Run with: pytest --run-e2e tests/e2e/test_real_workflow.py
"""

import os
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


def get_all_envs():
    """Get all environment definitions for comprehensive deployment."""
    envs = []

    # Get universal environments
    universal_dir = DEFS_DIR / "universal"
    envs.extend(sorted(universal_dir.glob("*.yaml")))

    # Get platform-specific environment
    if sys.platform == "linux":
        linux_yaml = DEFS_DIR / "linux" / "linux.yaml"
        if linux_yaml.exists():
            envs.append(linux_yaml)
    elif sys.platform == "darwin":
        mac_yaml = DEFS_DIR / "mac" / "mac.yaml"
        if mac_yaml.exists():
            envs.append(mac_yaml)

    return envs


def create_git_repo(path: Path):
    """Create a temporary git repository for metadata testing.

    Args:
        path: Directory to initialize as git repo
    """
    subprocess.run(
        ["git", "init"],
        cwd=path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "E2E Test"],
        cwd=path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "e2e@test.local"],
        cwd=path,
        capture_output=True,
        check=True,
    )
    # Create initial commit
    readme = path / "README.md"
    readme.write_text("# E2E Test Repository\n")
    subprocess.run(
        ["git", "add", "README.md"],
        cwd=path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=path,
        capture_output=True,
        check=True,
    )


@pytest.mark.e2e
@pytest.mark.slow
def test_full_workflow_bootstrap_deploy_promote_rotate(tmp_path):  # noqa: PLR0915
    """Comprehensive E2E test of complete deployment workflow.

    Tests the full lifecycle:
    1. Bootstrap engine
    2. Deploy all environments to staging tier
    3. Promote staging to production (blue/green swap)
    4. Deploy new staging to opposite color
    5. Test engine rotation (bootstrap again)

    This test may take 5-10+ minutes depending on environment size.
    """
    target_dir = tmp_path / "e2e_workflow"
    target_dir.mkdir()

    # Create git repo for real metadata if project root doesn't have one
    project_root = Path(__file__).parent.parent.parent
    if not (project_root / ".git").exists():
        create_git_repo(target_dir)

    filesystem = RealFileSystem()
    command_runner = RealCommandRunner()

    # Step 1: Bootstrap infrastructure (engine + directory structure)
    print("\n=== Step 1: Bootstrap Infrastructure ===")
    bootstrap_script = project_root / "scripts" / "bootstrap"

    result = subprocess.run(
        [str(bootstrap_script), str(target_dir)],
        capture_output=True,
        text=True,
        check=False,
        timeout=300,  # 5 minutes for bootstrap
    )

    assert result.returncode == 0, f"Bootstrap failed: {result.stderr}"

    # Verify mamba binary exists and is executable
    engine_symlink = target_dir / "engine_home" / "engine"
    assert engine_symlink.exists(), "engine symlink should exist"
    assert engine_symlink.is_symlink(), "engine should be a symlink"

    mamba_path = engine_symlink / "condabin" / "mamba"
    assert mamba_path.exists(), f"mamba binary should exist at {mamba_path}"

    # Resolve symlink and verify it's executable
    resolved_mamba = mamba_path.resolve()
    assert (
        resolved_mamba.exists()
    ), f"resolved mamba binary should exist at {resolved_mamba}"
    assert os.access(resolved_mamba, os.X_OK), "mamba binary should be executable"

    # Verify initial engine is engine_a
    initial_engine = engine_symlink.readlink()
    assert initial_engine.name == "engine_a", "Initial engine should be engine_a"

    # Step 2: Deploy to staging tier
    print("\n=== Step 2: Deploy to Staging ===")
    env_yamls = get_all_envs()
    assert len(env_yamls) >= 3, "Should have at least 3 environments"

    deploy_tier(
        target=target_dir,
        tier="staging",
        dry_run=False,
        offline=False,
        filesystem=filesystem,
        command_runner=command_runner,
        env_yamls=env_yamls,
        mamba_path=resolved_mamba,
    )

    # Verify staging deployment
    infrastructure_dir = target_dir / "infrastructure"
    staging_symlink = infrastructure_dir / "staging"
    assert staging_symlink.exists(), "staging symlink should exist"
    assert staging_symlink.is_symlink(), "staging should be a symlink"

    staging_color = staging_symlink.readlink().name
    assert staging_color in [
        "blue",
        "green",
    ], f"staging should point to blue or green, got {staging_color}"

    staging_dir = infrastructure_dir / staging_color
    assert staging_dir.exists(), f"staging directory {staging_color} should exist"

    # Verify environments created
    envs_dir = staging_dir / "conda" / "envs"
    assert envs_dir.exists(), "conda/envs directory should exist"

    env_names = [env.stem for env in env_yamls]
    for env_name in env_names:
        env_path = envs_dir / env_name
        assert env_path.exists(), f"Environment {env_name} should be created"
        assert env_path.is_dir(), f"Environment {env_name} should be a directory"

    # Verify bin, etc, meta directories
    assert (staging_dir / "bin").exists(), "bin directory should be copied"
    assert (staging_dir / "etc").exists(), "etc directory should be copied"
    assert (staging_dir / "meta").exists(), "meta directory should exist"

    # Verify real git metadata
    commit_file = staging_dir / "meta" / "commit"
    assert commit_file.exists(), "commit metadata should exist"
    commit_content = commit_file.read_text().strip()
    assert len(commit_content) == 40, "commit should be a valid git SHA"
    assert commit_content.isalnum(), "commit should be alphanumeric"

    # Step 3: Promote staging to production
    print("\n=== Step 3: Promote Staging to Production ===")
    promote_script = project_root / "scripts" / "promote_staging"

    # Set IAC_TIER_DIR to staging target (resolved blue or green directory)
    staging_target = staging_symlink.resolve()
    env = os.environ.copy()
    env["IAC_TIER_DIR"] = str(staging_target)

    result = subprocess.run(
        [str(promote_script)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, f"Promotion failed: {result.stderr}"

    # Verify promotion swapped the symlinks
    production_symlink = infrastructure_dir / "production"
    assert production_symlink.exists(), "production symlink should exist"
    assert production_symlink.is_symlink(), "production should be a symlink"

    production_color = production_symlink.readlink().name
    new_staging_color = staging_symlink.readlink().name

    assert (
        production_color == staging_color
    ), f"production should point to original staging color {staging_color}"
    assert (
        new_staging_color != production_color
    ), "staging should point to opposite color"
    assert new_staging_color in [
        "blue",
        "green",
    ], f"new staging should be blue or green, got {new_staging_color}"

    # Step 4: Deploy new staging to opposite color
    print("\n=== Step 4: Deploy New Staging ===")
    deploy_tier(
        target=target_dir,
        tier="staging",
        dry_run=False,
        offline=False,
        filesystem=filesystem,
        command_runner=command_runner,
        env_yamls=env_yamls,
        mamba_path=resolved_mamba,
    )

    # Verify new staging deployment
    new_staging_dir = infrastructure_dir / new_staging_color
    assert (
        new_staging_dir.exists()
    ), f"new staging directory {new_staging_color} should exist"

    new_envs_dir = new_staging_dir / "conda" / "envs"
    assert new_envs_dir.exists(), "new staging conda/envs should exist"

    for env_name in env_names:
        env_path = new_envs_dir / env_name
        assert (
            env_path.exists()
        ), f"Environment {env_name} should be created in new staging"

    assert (new_staging_dir / "bin").exists(), "new staging bin directory should exist"
    assert (new_staging_dir / "etc").exists(), "new staging etc directory should exist"
    assert (
        new_staging_dir / "meta"
    ).exists(), "new staging meta directory should exist"

    # Verify complete blue/green rotation worked
    blue_dir = infrastructure_dir / "blue"
    green_dir = infrastructure_dir / "green"
    assert blue_dir.exists(), "blue directory should exist"
    assert green_dir.exists(), "green directory should exist"
    assert (blue_dir / "conda" / "envs").exists(), "blue should have environments"
    assert (green_dir / "conda" / "envs").exists(), "green should have environments"

    # Step 5: Test engine rotation
    print("\n=== Step 5: Test Engine Rotation ===")
    bootstrap_engine_script = project_root / "scripts" / "bootstrap-engine"

    result = subprocess.run(
        [
            str(bootstrap_engine_script),
            str(target_dir),
            "-y",
        ],  # -y is valid for bootstrap-engine
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )

    assert result.returncode == 0, f"Engine rotation bootstrap failed: {result.stderr}"

    # Verify engine rotated from engine_a to engine_b
    new_engine = engine_symlink.readlink()
    assert new_engine.name == "engine_b", "Engine should rotate to engine_b"
    assert new_engine.name != initial_engine.name, "Engine should have rotated"

    # Verify new engine has mamba
    new_mamba_path = engine_symlink / "condabin" / "mamba"
    assert new_mamba_path.exists(), "new engine should have mamba binary"
    resolved_new_mamba = new_mamba_path.resolve()
    assert resolved_new_mamba.exists(), "resolved new mamba binary should exist"
    assert os.access(
        resolved_new_mamba, os.X_OK
    ), "new mamba binary should be executable"

    # Verify all metadata tracked throughout workflow
    for tier_color in ["blue", "green"]:
        tier_meta = infrastructure_dir / tier_color / "meta"
        if tier_meta.exists():
            commit_file = tier_meta / "commit"
            tree_hash_file = tier_meta / "tree_hash"
            description_file = tier_meta / "description"

            assert commit_file.exists(), f"{tier_color} should have commit metadata"
            assert (
                tree_hash_file.exists()
            ), f"{tier_color} should have tree_hash metadata"
            assert (
                description_file.exists()
            ), f"{tier_color} should have description metadata"

            # Verify metadata is real git data
            commit = commit_file.read_text().strip()
            tree_hash = tree_hash_file.read_text().strip()
            description = description_file.read_text().strip()

            assert len(commit) == 40, f"{tier_color} commit should be valid git SHA"
            assert (
                len(tree_hash) == 40
            ), f"{tier_color} tree_hash should be valid git SHA"
            assert len(description) > 0, f"{tier_color} description should not be empty"
            assert (
                "mock" not in description.lower()
            ), f"{tier_color} should have real git description"

    print("\n=== Full Workflow Test Complete ===")
