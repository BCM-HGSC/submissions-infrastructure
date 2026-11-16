"""Shared pytest fixtures for submissions-infrastructure tests."""

import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from engine.command_runner import MockCommandRunner
from engine.filesystem import MockFileSystem

REPO_ROOT = Path(__file__).parent.parent
IAC = REPO_ROOT / "scripts" / "iac"


def run_iac(*args: str, timeout: int = 60, **kwargs) -> subprocess.CompletedProcess:
    """
    Run the real scripts/iac with no default target and no git variables.

    A git hook exports GIT_DIR and friends. Without this, any git command a
    test starts would act on this repository instead of the one it means.
    """
    env = {
        key: value
        for key, value in os.environ.items()
        if key != "IAC_PARENT" and not key.startswith("GIT_")
    }
    return subprocess.run(
        [str(IAC), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        timeout=timeout,
        **kwargs,
    )


@pytest.fixture
def tmp_target_dir(tmp_path: Path) -> Path:
    """
    Create a temporary target directory structure for testing deployments.

    Creates:
    - conda_package_cache/
    - engine_home/
    - infrastructure/

    Returns:
        Path to the temporary target directory.
    """
    target_dir = tmp_path / "target"
    target_dir.mkdir()

    # Create standard subdirectories
    (target_dir / "conda_package_cache").mkdir()
    (target_dir / "engine_home").mkdir()
    (target_dir / "infrastructure").mkdir()

    return target_dir


@pytest.fixture
def mock_filesystem() -> MockFileSystem:
    """
    Create a mock filesystem for testing.

    Returns:
        MockFileSystem instance for testing filesystem operations.
    """
    return MockFileSystem()


@pytest.fixture
def mock_command_runner() -> MockCommandRunner:
    """
    Create a mock command runner for testing.

    Returns:
        MockCommandRunner instance for testing command execution.
    """
    return MockCommandRunner()


@pytest.fixture
def sample_env_yaml(tmp_path: Path) -> Path:
    """
    Create a sample environment YAML file for testing.

    Returns:
        Path to the temporary YAML file.
    """
    yaml_content = """channels:
  - conda-forge
dependencies:
  - python~=3.13
  - pytest
  - pip
"""
    yaml_file = tmp_path / "test_env.yaml"
    yaml_file.write_text(yaml_content)
    return yaml_file


def pytest_configure(config: Any) -> None:
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires --run-integration)",
    )
    config.addinivalue_line(
        "markers",
        "e2e: mark test as end-to-end test (requires real mamba and --run-e2e)",
    )


def pytest_addoption(parser: Any) -> None:
    """Add custom command-line options to pytest."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="run integration tests",
    )
    parser.addoption(
        "--run-e2e",
        action="store_true",
        default=False,
        help="run end-to-end tests (requires real mamba installation)",
    )


def pytest_collection_modifyitems(config: Any, items: list) -> None:
    """Skip integration and e2e tests unless appropriate flags are provided."""
    skip_integration = not config.getoption("--run-integration")
    skip_e2e = not config.getoption("--run-e2e")

    for item in items:
        if skip_integration and "integration" in item.keywords:
            item.add_marker(
                pytest.mark.skip(reason="need --run-integration option to run")
            )
        if skip_e2e and "e2e" in item.keywords:
            item.add_marker(pytest.mark.skip(reason="need --run-e2e option to run"))
