"""
Source the tier's profile.sh in bare shells and check what it sets up.

The tier is a copy of resources/etc with stand-ins for the conda scripts
the profile sources, so no deployment is needed.
"""

from pathlib import Path
import shutil
import subprocess

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
BARE_SHELLS = {
    "bash": ["bash", "--noprofile", "--norc", "-c"],
    "zsh": ["zsh", "-f", "-c"],
}


@pytest.fixture
def tier_profile(tmp_path: Path) -> Path:
    """The profile.sh of a staging tier, reached through its symlink."""
    infrastructure = tmp_path / "target" / "infrastructure"
    blue = infrastructure / "blue"
    shutil.copytree(REPO_ROOT / "resources/etc", blue / "etc")
    shutil.copytree(REPO_ROOT / "resources/bin", blue / "bin")
    conda_profile = blue / "conda/envs/conda/etc/profile.d"
    conda_profile.mkdir(parents=True)
    (conda_profile / "conda.sh").write_text("")
    (conda_profile / "mamba.sh").write_text("")
    (blue / "conda/envs/unix/bin").mkdir(parents=True)
    (infrastructure / "staging").symlink_to("blue")
    return infrastructure / "staging/etc/profile.sh"


@pytest.fixture(params=sorted(BARE_SHELLS))
def source_profile(request, tier_profile: Path, tmp_path: Path):
    """Source the profile in a bare shell, then run a script."""
    shell = BARE_SHELLS[request.param]
    if shutil.which(shell[0]) is None:
        pytest.skip(f"{shell[0]} is not installed")
    home = tmp_path / "home"
    home.mkdir()
    env = {
        "HOME": str(home),
        "USER": "tester",
        "PATH": "/original/bin:/usr/bin:/bin",
        "TERM": "dumb",
    }

    def run(script: str, **extra_env: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [*shell, f'source "{tier_profile}"\n{script}'],
            capture_output=True,
            text=True,
            check=False,
            env={**env, **extra_env},
            cwd=tmp_path,
            timeout=60,
        )

    return run


def test_profile_sources_without_complaint(source_profile):
    """Issue #27: a zsh that never ran compinit reported compdef errors."""
    result = source_profile("true")

    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout == ""


def test_profile_sets_the_iac_variables(source_profile, tier_profile):
    target = tier_profile.parents[3]

    result = source_profile("iac_dump_vars")

    assert result.stdout.splitlines() == [
        f"IAC_TIER_DIR={target.resolve()}/infrastructure/blue",
        "IAC_TIER_NAME=staging",
        f"IAC_DIR={target.resolve()}/infrastructure",
        f"IAC_PARENT={target.resolve()}",
        "IAC_ORIGINAL_PATH=/original/bin:/usr/bin:/bin",
        f"CONDARC={target.resolve()}/infrastructure/blue/etc/condarc",
        f"PIP_CACHE_DIR={target.resolve()}/users/tester/pip_cache",
    ]


def test_profile_puts_the_tier_first_on_path(source_profile, tier_profile):
    blue = tier_profile.resolve().parents[1]

    result = source_profile('echo "$PATH"')

    path = result.stdout.strip().split(":")
    assert str(blue / "bin") in path
    assert str(blue / "conda/envs/unix/bin") in path
    assert path.index(str(blue / "bin")) < path.index("/usr/bin")


def test_profile_keeps_a_pip_cache_the_user_chose(source_profile):
    result = source_profile('echo "$PIP_CACHE_DIR"', PIP_CACHE_DIR="/my/own/cache")

    assert result.stdout.strip() == "/my/own/cache"


def test_profile_registers_completions_in_zsh(tier_profile, tmp_path):
    if shutil.which("zsh") is None:
        pytest.skip("zsh is not installed")
    home = tmp_path / "home"
    home.mkdir()

    result = subprocess.run(
        ["zsh", "-f", "-c", f'source "{tier_profile}"; print $_comps[go] $_comps[ca]'],
        capture_output=True,
        text=True,
        check=False,
        env={"HOME": str(home), "USER": "tester", "PATH": "/usr/bin:/bin"},
        timeout=60,
    )

    assert result.stderr == ""
    assert result.stdout.split() == ["_list_alias_store", "_ca_complete"]
