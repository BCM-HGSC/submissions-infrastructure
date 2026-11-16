"""Bootstrap a real target once, then exercise it through scripts/iac."""

from pathlib import Path

import pytest

from scripts.iac_cli import micromamba
from tests.conftest import run_iac

pytestmark = pytest.mark.integration

BUILD_TIMEOUT = 900


@pytest.fixture(scope="module")
def target(tmp_path_factory) -> Path:
    """A target that `iac bootstrap` has just created."""
    target = tmp_path_factory.mktemp("integration") / "target"
    result = run_iac("bootstrap", "--target", str(target), timeout=BUILD_TIMEOUT)
    assert result.returncode == 0, result.stderr
    return target


def test_bootstrap_creates_the_layout(target):
    assert (target / "conda_package_cache").is_dir()
    assert (target / "engine_home/engine").readlink() == Path("engine_a")
    assert (target / "infrastructure/staging").readlink() == Path("blue")
    assert (target / "infrastructure/production").readlink() == Path("green")


def test_bootstrap_installs_the_pinned_micromamba(target):
    installed = micromamba.file_sha256(target / "engine_home/micromamba")

    assert installed == micromamba.SHA256[micromamba.current_platform()]


def test_engine_has_the_tools_deploy_needs(target):
    engine_bin = target / "engine_home/engine/bin"

    for tool in ("python3", "mamba", "git"):
        assert (engine_bin / tool).is_file(), tool


def test_status_reports_an_undeployed_target(target):
    result = run_iac("status", "--target", str(target))

    assert result.returncode == 0, result.stderr
    assert "engine:      -> engine_a" in result.stdout
    assert "staging:     -> blue, not deployed" in result.stdout


def test_second_bootstrap_changes_nothing(target):
    before = sorted(path.name for path in (target / "engine_home").iterdir())

    result = run_iac("bootstrap", "--target", str(target))

    assert result.returncode == 0, result.stderr
    assert "Engine already installed" in result.stderr
    assert sorted(path.name for path in (target / "engine_home").iterdir()) == before


def test_deploy_dry_run_finds_mamba_in_the_engine(target):
    result = run_iac("deploy", "--dry-run", "--verbose", "--target", str(target))

    output = "".join((result.stdout + result.stderr).split())  # rich wraps lines
    assert result.returncode == 0, result.stderr
    assert "engine_home/engine/bin/mamba" in output
    assert "[DRYRUN]Wouldrun:" in output
    assert list((target / "infrastructure/blue").iterdir()) == []
    assert not (target / "logs").exists()


def test_promote_refuses_a_tier_that_was_never_deployed(target):
    result = run_iac("promote", "--target", str(target))

    assert result.returncode == 3
    assert "has not been deployed" in result.stderr
    assert (target / "infrastructure/production").readlink() == Path("green")


def test_engine_rotates_to_the_other_slot(target):
    """Last: it replaces the engine the other tests look at."""
    result = run_iac("engine", "--target", str(target), timeout=BUILD_TIMEOUT)

    assert result.returncode == 0, result.stderr
    assert (target / "engine_home/engine").readlink() == Path("engine_b")
    assert (target / "engine_home/engine_a").is_dir()  # previous engine kept
    assert (target / "engine_home/engine/bin/mamba").is_file()
