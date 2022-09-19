"""
Module responsible for actually deploying sofwware to a tier.
(A "tier" is a top-level directory or symlink such as "staging" or "production".)
"""

from logging import critical, info
from pathlib import Path
from subprocess import run
from sys import executable


def deploy(target: Path, tier: str) -> None:
    info(f"{target=}")
    info(f"{tier=}")
    if not target.is_dir():
        critical("target is not a directory")
    mamba = Path(executable).with_name("mamba")
    info(f"{mamba=}")
    if not mamba.is_file():
        critical(f"mamba is missing")
        exit(2)
    engine_home_path = target / "engine_home"
    tier_path = target / "infrastructure" / tier
    defs_dir = Path(__file__).parent.parent.parent / "resources/defs"
    env = dict(
        HOME=engine_home_path,
        # CONDARC=tier_path / "condarc",
        CONDA_ENVS_DIRS=tier_path / "conda/envs",
        CONDA_PKGS_DIRS=target / "conda_package_cache",
        CONDA_CHANNELS="conda-forge",
    )
    run("/usr/bin/env", env=env)
    run([mamba, "info"], env=env)
    run(["/Users/hale/conda/unix/bin/tree", defs_dir])
    exit("TODO")
