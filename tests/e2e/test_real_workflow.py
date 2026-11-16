"""The whole life cycle through scripts/iac, installing every environment."""

from pathlib import Path
import subprocess

import pytest

from tests.conftest import REPO_ROOT, run_iac

pytestmark = [pytest.mark.e2e, pytest.mark.slow]

BUILD_TIMEOUT = 900
DEPLOY_TIMEOUT = 3600


def test_bootstrap_deploy_promote_and_roll_back(tmp_path):
    target = tmp_path / "target"
    infrastructure = target / "infrastructure"

    def iac(*args: str, timeout: int = 60) -> subprocess.CompletedProcess:
        result = run_iac(*args, "--target", str(target), timeout=timeout)
        assert result.returncode == 0, result.stdout + result.stderr
        return result

    def links() -> tuple[str, str]:
        return (
            str((infrastructure / "staging").readlink()),
            str((infrastructure / "production").readlink()),
        )

    iac("bootstrap", timeout=BUILD_TIMEOUT)
    assert links() == ("blue", "green")

    # First deploy goes to staging, which is blue.
    iac("deploy", timeout=DEPLOY_TIMEOUT)
    assert_deployed(infrastructure / "blue")
    assert not (infrastructure / "green/meta").exists()
    assert "staging:     -> blue, commit " in iac("status").stdout
    assert_profile_works(infrastructure / "staging/etc/profile.sh", tmp_path)

    iac("promote")
    assert links() == ("green", "blue")

    # The second deploy goes to the other color and leaves production alone.
    iac("deploy", timeout=DEPLOY_TIMEOUT)
    assert_deployed(infrastructure / "green")
    assert_deployed(infrastructure / "blue")

    # --keep reuses the environments and still completes the tier.
    environments = environment_ids(infrastructure / "green")
    iac("deploy", "--keep", timeout=DEPLOY_TIMEOUT)
    assert environment_ids(infrastructure / "green") == environments
    assert_deployed(infrastructure / "green")

    # Promoting again is the rollback.
    iac("promote")
    assert links() == ("blue", "green")
    iac("promote")
    assert links() == ("green", "blue")

    # Production cannot be deployed to under any name.
    refused = run_iac(
        "deploy", "--tier", "blue", "--overwrite", "--target", str(target)
    )
    assert refused.returncode == 4
    assert_deployed(infrastructure / "blue")


def assert_deployed(tier: Path) -> None:
    head = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
        env={"PATH": "/usr/bin:/bin"},  # no GIT_DIR from a hook
    ).stdout
    assert (tier / "meta/commit").read_text() == head
    assert len((tier / "meta/tree_hash").read_text().strip()) == 40
    assert (tier / "meta/description").read_text().strip() != "unknown"
    assert (tier / "etc/profile.sh").is_file()
    assert (tier / "bin/path").is_file()
    for environment in ("conda", "python", "unix"):
        assert (tier / "conda/envs" / environment / "conda-meta").is_dir()


def environment_ids(tier: Path) -> dict[str, int]:
    """Each environment's inode, which changes if it is rebuilt."""
    return {path.name: path.stat().st_ino for path in (tier / "conda/envs").iterdir()}


def assert_profile_works(profile: Path, home: Path) -> None:
    """A bare bash that sources the tier gets the tier's tools."""
    script = f'source "{profile}" && command -v mamba python uv && iac_dump_vars'
    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-c", script],
        capture_output=True,
        text=True,
        check=False,
        env={"HOME": str(home), "USER": "tester", "PATH": "/usr/bin:/bin"},
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert "IAC_TIER_NAME=staging" in result.stdout
