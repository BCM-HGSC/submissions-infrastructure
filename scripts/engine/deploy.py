"""
Module responsible for actually deploying sofwware to a tier.
(A "tier" is a top-level directory or symlink such as "staging" or "production".)
"""

from logging import critical, info
from pathlib import Path
from subprocess import run
from sys import executable


def deploy_tier(target: Path, tier: str, offline: bool, run_function=run) -> None:
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
    env = dict(
        HOME=engine_home_path,
        # CONDARC=tier_path / "condarc",
        CONDA_ENVS_DIRS=tier_path / "conda/envs",
        CONDA_PKGS_DIRS=target / "conda_package_cache",
        CONDA_CHANNELS="conda-forge",
    )
    info(f"{env=}")
    run([mamba, "info"], env=env)
    env_path = Path("universal/conda.yaml")
    deploy_env(run_function, env, mamba, offline, env_path)
    env_path = Path("universal/unix.yaml")
    deploy_env(run_function, env, mamba, offline, env_path)


def deploy_env(run_function, env, mamba, offline, env_path: Path):
    defs_dir = Path(__file__).parent.parent.parent / "resources/defs"
    run(["/Users/hale/conda/unix/bin/tree", defs_dir])
    env_name = env_path.stem
    offline_opt = ["--offline"] if offline else []
    mamba_command = [mamba, "env", "create", "--force"] + offline_opt
    mamba_command += ["-n", env_name, "-f", defs_dir / env_path]
    info(f"{mamba_command=}")
    run_function(mamba_command, check=True, env=env)
