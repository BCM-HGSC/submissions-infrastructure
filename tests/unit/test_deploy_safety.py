"""Tests that deploy does not destroy data or report false success."""

from pathlib import Path
import sys
from unittest.mock import patch

import pytest

from scripts.engine.command_runner import MockCommandRunner
from scripts.engine.deploy import deploy_tier, find_mamba
from scripts.engine.filesystem import RealFileSystem


@pytest.fixture
def real_target(tmp_target_dir: Path) -> Path:
    """A bootstrapped-looking target on the real filesystem."""
    infrastructure = tmp_target_dir / "infrastructure"
    (infrastructure / "blue").mkdir()
    (infrastructure / "green").mkdir()
    (infrastructure / "staging").symlink_to("blue")
    (infrastructure / "production").symlink_to("green")
    return tmp_target_dir


@pytest.fixture
def fake_mamba(tmp_path: Path) -> Path:
    mamba = tmp_path / "fake_bin" / "mamba"
    mamba.parent.mkdir()
    mamba.write_text("#!/bin/sh\n")
    return mamba


@pytest.fixture
def enough_disk():
    with patch("scripts.engine.deploy.check_disk_space", return_value=(True, "")):
        yield


def test_dry_run_changes_nothing(real_target, fake_mamba, sample_env_yaml, enough_disk):
    marker = real_target / "infrastructure" / "blue" / "marker"
    marker.write_text("keep me\n")
    before = snapshot(real_target)
    runner = MockCommandRunner()

    deploy_tier(
        real_target,
        "staging",
        dry_run=True,
        offline=False,
        filesystem=RealFileSystem(),
        command_runner=runner,
        env_yamls=[sample_env_yaml],
        mamba_path=fake_mamba,
    )

    assert snapshot(real_target) == before
    assert runner.get_call_count() == 0


def test_dry_run_with_force_changes_nothing(
    real_target, fake_mamba, sample_env_yaml, enough_disk
):
    marker = real_target / "infrastructure" / "blue" / "marker"
    marker.write_text("keep me\n")
    before = snapshot(real_target)

    deploy_tier(
        real_target,
        "blue",
        dry_run=True,
        offline=False,
        mode="force",
        filesystem=RealFileSystem(),
        command_runner=MockCommandRunner(),
        env_yamls=[sample_env_yaml],
        mamba_path=fake_mamba,
    )

    assert snapshot(real_target) == before


def test_failed_environment_exits_nonzero(
    real_target, fake_mamba, sample_env_yaml, enough_disk
):
    runner = MockCommandRunner()
    runner.set_return_value(returncode=1)

    with pytest.raises(SystemExit) as exc_info:
        deploy_tier(
            real_target,
            "staging",
            dry_run=False,
            offline=False,
            filesystem=RealFileSystem(),
            command_runner=runner,
            env_yamls=[sample_env_yaml],
            mamba_path=fake_mamba,
        )

    assert exc_info.value.code == 4
    # A tier with failed environments must not look deployed.
    assert not (real_target / "infrastructure" / "blue" / "meta").exists()


def test_all_environments_attempted_after_a_failure(
    real_target, fake_mamba, sample_env_yaml, enough_disk
):
    second_yaml = sample_env_yaml.with_name("second_env.yaml")
    second_yaml.write_text(sample_env_yaml.read_text())
    runner = MockCommandRunner()
    runner.set_return_value(returncode=1)

    with pytest.raises(SystemExit):
        deploy_tier(
            real_target,
            "staging",
            dry_run=False,
            offline=False,
            filesystem=RealFileSystem(),
            command_runner=runner,
            env_yamls=[sample_env_yaml, second_yaml],
            mamba_path=fake_mamba,
        )

    assert runner.get_call_count() == 2


def test_missing_production_symlink_is_not_created(
    real_target, fake_mamba, sample_env_yaml, enough_disk
):
    production = real_target / "infrastructure" / "production"
    production.unlink()

    deploy_tier(
        real_target,
        "staging",
        dry_run=False,
        offline=False,
        filesystem=RealFileSystem(),
        command_runner=MockCommandRunner(),
        env_yamls=[sample_env_yaml],
        mamba_path=fake_mamba,
    )

    assert not production.exists()
    assert not production.is_symlink()


def test_logs_survive_redeploy(real_target, fake_mamba, sample_env_yaml, enough_disk):
    def deploy() -> None:
        deploy_tier(
            real_target,
            "staging",
            dry_run=False,
            offline=False,
            filesystem=RealFileSystem(),
            command_runner=MockCommandRunner(),
            env_yamls=[sample_env_yaml],
            mamba_path=fake_mamba,
        )

    deploy()
    logs = sorted((real_target / "logs").iterdir())
    assert len(logs) == 1
    assert logs[0].name.endswith("-blue-test_env.log")

    deploy()  # removes and recreates the staging tier
    assert logs[0].exists()
    assert not (real_target / "infrastructure" / "blue" / "logs").exists()


def test_find_mamba_prefers_engine_over_path(tmp_path, monkeypatch):
    engine_bin = tmp_path / "engine" / "bin"
    engine_bin.mkdir(parents=True)
    engine_mamba = engine_bin / "mamba"
    engine_mamba.write_text("")
    monkeypatch.setattr(sys, "executable", str(engine_bin / "python3"))
    # The deploy wrapper runs the engine with this PATH.
    monkeypatch.setenv("PATH", "/usr/bin:/bin")

    assert find_mamba() == engine_mamba


def test_find_mamba_uses_condabin(tmp_path, monkeypatch):
    engine = tmp_path / "engine"
    (engine / "bin").mkdir(parents=True)
    (engine / "condabin").mkdir()
    condabin_mamba = engine / "condabin" / "mamba"
    condabin_mamba.write_text("")
    monkeypatch.setattr(sys, "executable", str(engine / "bin" / "python3"))
    monkeypatch.setenv("PATH", "/usr/bin:/bin")

    assert find_mamba() == condabin_mamba


def test_find_mamba_falls_back_to_path(tmp_path, monkeypatch):
    path_dir = tmp_path / "on_path"
    path_dir.mkdir()
    path_mamba = path_dir / "mamba"
    path_mamba.write_text("#!/bin/sh\n")
    path_mamba.chmod(0o755)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "nowhere" / "python3"))
    monkeypatch.setenv("PATH", str(path_dir))

    assert find_mamba() == path_mamba


def test_find_mamba_returns_none_when_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "executable", str(tmp_path / "nowhere" / "python3"))
    monkeypatch.setenv("PATH", str(tmp_path))

    assert find_mamba() is None


def snapshot(root: Path) -> dict[str, str]:
    """Map every path under root to its kind and content or link target."""
    result = {}
    for path in sorted(root.rglob("*")):
        key = str(path.relative_to(root))
        if path.is_symlink():
            result[key] = f"link:{path.readlink()}"
        elif path.is_dir():
            result[key] = "dir"
        else:
            result[key] = f"file:{path.read_text()}"
    return result
