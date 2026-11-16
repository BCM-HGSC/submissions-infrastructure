"""
Run the real entry points: scripts/iac and the deprecated shims.

These start subprocesses through uv. They need no network, no engine, and
no target.
"""

import os
from pathlib import Path
import shutil
import subprocess

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"

pytestmark = pytest.mark.skipif(
    shutil.which("uv") is None, reason="scripts/iac runs under uv"
)


@pytest.fixture
def run_script(tmp_path):
    """Run a script with no target configured anywhere."""
    if (REPO_ROOT / "iac_config.toml").exists():
        pytest.skip("this checkout has its own iac_config.toml")
    home = tmp_path / "home"
    home.mkdir()
    env = {key: value for key, value in os.environ.items() if key != "IAC_PARENT"}
    env["HOME"] = str(home)
    # uv keeps its cache under the real home.
    env.setdefault("UV_CACHE_DIR", str(Path.home() / ".cache/uv"))

    def run(name: str, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(SCRIPTS_DIR / name), *args],
            capture_output=True,
            text=True,
            check=False,
            cwd=tmp_path,
            env=env,
            timeout=60,
        )

    return run


@pytest.mark.parametrize(
    "args",
    [
        ["--help"],
        ["bootstrap", "--help"],
        ["engine", "--help"],
        ["deploy", "--help"],
        ["promote", "--help"],
        ["status", "--help"],
    ],
)
def test_iac_help_needs_no_target_or_engine(run_script, args):
    result = run_script("iac", *args)

    assert result.returncode == 0, result.stderr
    assert "usage: iac" in result.stdout


def test_iac_without_a_target_explains_how_to_give_one(run_script):
    result = run_script("iac", "deploy")

    assert result.returncode == 1
    assert "No target directory" in result.stderr


def test_iac_status_of_an_empty_target(run_script, tmp_path):
    result = run_script("iac", "status", "--target", str(tmp_path))

    assert result.returncode == 0, result.stderr
    assert "engine:      missing" in result.stdout


def test_iac_bootstrap_dry_run_creates_nothing(run_script, tmp_path):
    target = tmp_path / "deployment"

    result = run_script("iac", "--dry-run", "bootstrap", "--target", str(target))

    assert result.returncode == 0, result.stderr
    assert "[DRY RUN]" in result.stderr
    assert not target.exists()


# Deprecated shims


@pytest.mark.parametrize(
    ("script", "subcommand"),
    [("deploy", "deploy"), ("bootstrap", "bootstrap"), ("bootstrap-engine", "engine")],
)
def test_shim_help_works_without_a_target(run_script, script, subcommand):
    result = run_script(script, "--help")

    assert result.returncode == 0, result.stderr
    assert f"usage: iac {subcommand}" in result.stdout
    assert "deprecated" in result.stderr


def test_deploy_shim_without_arguments_is_a_usage_error(run_script):
    result = run_script("deploy")

    assert result.returncode == 1
    assert "No target directory" in result.stderr


def test_deploy_shim_translates_old_arguments(run_script, tmp_path):
    # --force is accepted and translated; the run then stops for lack of
    # an engine, which shows the target was understood.
    result = run_script("deploy", str(tmp_path), "staging", "--force", "--dry-run")

    assert result.returncode == 2
    assert f"No engine at {tmp_path}/engine_home/engine" in result.stderr


def test_bootstrap_shim_refuses_force(run_script, tmp_path):
    target = tmp_path / "deployment"

    result = run_script("bootstrap", "--force", str(target))

    assert result.returncode == 1
    assert "no longer erases" in result.stderr
    assert not target.exists()


@pytest.mark.parametrize("script", ["deploy", "bootstrap", "bootstrap-engine"])
def test_shims_reject_extra_arguments(run_script, script):
    result = run_script(script, "one", "two", "three")

    assert result.returncode == 1
    assert "Too many arguments" in result.stderr


def test_bootstrap_engine_shim_dry_run(run_script, tmp_path):
    target = tmp_path / "deployment"

    result = run_script("bootstrap-engine", "--dry-run", "-y", "--force", str(target))

    assert result.returncode == 0, result.stderr
    assert "micromamba env create" in result.stderr
    assert not target.exists()
