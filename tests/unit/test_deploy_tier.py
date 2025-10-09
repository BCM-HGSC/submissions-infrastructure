"""Unit tests for deploy_tier function with env_yamls parameter."""

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

import pytest

from scripts.engine.deploy import DEFS_DIR, MambaDeployer, deploy_tier


@pytest.fixture
def mock_dependencies(
    monkeypatch, tmp_target_dir, mock_filesystem, mock_command_runner
):
    """Mock all external dependencies for deploy_tier."""
    # Add target directory and subdirectories to mock filesystem
    mock_filesystem.directories.add(tmp_target_dir)
    mock_filesystem.directories.add(tmp_target_dir / "infrastructure")

    # Mock MAMBA binary path
    mock_mamba = tmp_target_dir / "engine_home" / "engine" / "bin" / "mamba"
    mock_filesystem.files.add(mock_mamba)

    # Patch the MAMBA global variable to point to our mock location
    with (
        patch("scripts.engine.deploy.MAMBA", mock_mamba),
        patch("scripts.engine.deploy.check_disk_space") as mock_check,
    ):
        mock_check.return_value = (True, "")
        yield mock_check


def test_deploy_tier_uses_list_conda_environment_defs_when_env_yamls_is_none(
    tmp_target_dir, mock_filesystem, mock_command_runner, mock_dependencies
):
    """Test deploy_tier uses list_conda_environment_defs when env_yamls is None."""
    with patch("scripts.engine.deploy.list_conda_environment_defs") as mock_list:
        mock_list.return_value = [Path("/fake/conda.yaml"), Path("/fake/python.yaml")]

        # Create fake YAML files
        for yaml_file in mock_list.return_value:
            mock_filesystem.files.add(yaml_file)

        deploy_tier(
            target=tmp_target_dir,
            tier="staging",
            dry_run=True,  # Use dry run to avoid actual deployment
            offline=False,
            filesystem=mock_filesystem,
            command_runner=mock_command_runner,
            env_yamls=None,  # Explicitly pass None
        )

        # Verify list_conda_environment_defs was called
        mock_list.assert_called_once()


def test_deploy_tier_uses_provided_env_yamls_when_specified(
    tmp_target_dir, mock_filesystem, mock_command_runner, mock_dependencies
):
    """Test deploy_tier uses provided env_yamls when specified."""
    # Create custom environment list
    custom_envs = [
        Path("/custom/env1.yaml"),
        Path("/custom/env2.yaml"),
    ]

    # Create fake YAML files
    for yaml_file in custom_envs:
        mock_filesystem.files.add(yaml_file)

    with patch("scripts.engine.deploy.list_conda_environment_defs") as mock_list:
        deploy_tier(
            target=tmp_target_dir,
            tier="staging",
            dry_run=True,
            offline=False,
            filesystem=mock_filesystem,
            command_runner=mock_command_runner,
            env_yamls=custom_envs,  # Provide custom list
        )

        # Verify list_conda_environment_defs was NOT called
        mock_list.assert_not_called()


def test_deploy_tier_deploys_only_specified_environments(
    tmp_target_dir, mock_filesystem, mock_command_runner, mock_dependencies
):
    """Test deploy_tier uses only the environments specified in env_yamls."""
    # Create subset of environments (using actual files from the repo)
    subset_envs = [
        DEFS_DIR / "universal" / "conda.yaml",
        DEFS_DIR / "universal" / "unix.yaml",
    ]

    # Track environment deployment calls
    deployment_calls = []

    def track_deployments(worklist):
        # Track which environments were passed to deploy
        deployment_calls.extend(worklist)
        # Don't actually deploy in this unit test

    # Patch the deploy_conda_environments method
    with patch.object(
        MambaDeployer,
        "deploy_conda_environments",
        side_effect=track_deployments,
        autospec=False,
    ):
        deploy_tier(
            target=tmp_target_dir,
            tier="staging",
            dry_run=True,
            offline=False,
            filesystem=mock_filesystem,
            command_runner=mock_command_runner,
            env_yamls=subset_envs,
        )

    # Verify only specified environments were passed for deployment
    assert len(deployment_calls) == 2
    assert any("conda.yaml" in str(e) for e in deployment_calls)
    assert any("unix.yaml" in str(e) for e in deployment_calls)
    assert not any("python.yaml" in str(e) for e in deployment_calls)


def test_deploy_tier_empty_env_yamls_list(
    tmp_target_dir, mock_filesystem, mock_command_runner, mock_dependencies
):
    """Test deploy_tier with empty env_yamls list deploys nothing."""
    deployed_envs = []

    def track_deploy(command, **kwargs):
        if "mamba" in str(command[0]) and "-n" in command:
            n_index = command.index("-n")
            env_name = command[n_index + 1]
            deployed_envs.append(env_name)
        return CompletedProcess(args=command, returncode=0, stdout=b"", stderr=b"")

    mock_command_runner.run = MagicMock(side_effect=track_deploy)

    deploy_tier(
        target=tmp_target_dir,
        tier="staging",
        dry_run=True,  # Use dry-run for unit test
        offline=False,
        filesystem=mock_filesystem,
        command_runner=mock_command_runner,
        env_yamls=[],  # Empty list
    )

    # Verify no environments were deployed
    assert len(deployed_envs) == 0


def test_deploy_tier_respects_disk_space_check_with_custom_envs(
    tmp_target_dir, mock_filesystem, mock_command_runner
):
    """Test that disk space check receives custom env_yamls list."""
    custom_envs = [
        Path("/custom/env1.yaml"),
        Path("/custom/env2.yaml"),
    ]

    # Set up mock filesystem
    mock_filesystem.directories.add(tmp_target_dir)
    mock_filesystem.directories.add(tmp_target_dir / "infrastructure")

    # Create fake YAML files
    for yaml_file in custom_envs:
        mock_filesystem.files.add(yaml_file)

    # Mock MAMBA binary
    mock_mamba = tmp_target_dir / "engine_home" / "engine" / "bin" / "mamba"
    mock_filesystem.files.add(mock_mamba)

    with (
        patch("scripts.engine.deploy.MAMBA", mock_mamba),
        patch("scripts.engine.deploy.check_disk_space") as mock_check,
    ):
        mock_check.return_value = (True, "")

        deploy_tier(
            target=tmp_target_dir,
            tier="staging",
            dry_run=True,
            offline=False,
            filesystem=mock_filesystem,
            command_runner=mock_command_runner,
            env_yamls=custom_envs,
        )

        # Verify check_disk_space was called with custom env list
        mock_check.assert_called_once()
        call_args = mock_check.call_args
        assert call_args[0][0] == tmp_target_dir
        assert call_args[1]["operation"] == "deploy"
        assert call_args[1]["env_yamls"] == custom_envs
        assert call_args[1]["force"] is False
