"""
Module responsible for actually deploying sofwware to a tier.
(A "tier" is a top-level directory or symlink such as "staging" or "production".)
"""

from datetime import datetime as dt
from logging import critical, debug, error, info, warning
from pathlib import Path
from shutil import copytree, rmtree
from subprocess import STDOUT, run
from sys import executable, platform
from typing import Optional

from rich.console import Console


MAMBA = Path(executable).with_name("mamba")  # mamba in same bin/ as python3
RESOURCES_DIR = Path(__file__).parent.parent.parent / "resources"
DEFS_DIR = RESOURCES_DIR / "defs"
ETC_SOURCE_DIR = RESOURCES_DIR / "etc"


def deploy_tier(
    target: Path,
    tier: str,
    dry_run: bool,
    offline: bool,
    mode: Optional[str] = None,
    run_function=run,
) -> None:
    check_mamba()
    tier_path = setup_tier_path(target, tier)
    deployer = MambaDeployer(target, tier_path, dry_run, offline, mode, run_function)
    if deployer.mode != "keep":
        deployer.info()
    worklist = list_conda_environment_defs()
    deployer.deploy_conda_environments(worklist)
    deployer.deploy_etc()


def check_mamba():
    info(f"{MAMBA=}")
    if not MAMBA.is_file():
        critical(f"mamba is missing")
        exit(2)


def setup_tier_path(target, tier):
    info(f"{target=}")
    info(f"{tier=}")
    if not target.is_dir():
        critical("target is not a directory")
        exit(3)
    tier_path = (target / "infrastructure" / tier).resolve()
    info(f"{tier_path=}")
    if not tier_path.is_dir():
        tier_path.mkdir(parents=True, exist_ok=True)
    return tier_path


def list_conda_environment_defs() -> list[Path]:
    worklist = sorted(DEFS_DIR.glob("universal/*.yaml"))
    if platform == "darwin":
        worklist.append(DEFS_DIR / "mac/mac.yaml")
    for item in worklist:
        if not item.is_file():
            error(f"not a file: {item}")
            worklist.remove(item)
    debug(f"{worklist=}")
    return worklist


class MambaDeployer:
    def __init__(
        self,
        target: Path,
        tier_path: Path,
        dry_run: bool,
        offline: bool,
        mode: Optional[str],
        run_function=run,
    ):
        self.dry_run = dry_run
        self.offline = offline
        self.mode = mode
        self.run_function = run_function
        self.envs_dir = tier_path / "conda/envs"
        self.etc_dir = tier_path / "etc"
        self.env = dict(
            HOME=target / "engine_home",
            # CONDARC=tier_path / "condarc",
            CONDA_ENVS_DIRS=self.envs_dir,
            CONDA_PKGS_DIRS=target / "conda_package_cache",
            CONDA_CHANNELS="conda-forge",
        )
        info(f"{self.env=}")
        self.log_dir = tier_path / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.console = Console()
        debug(f"vars(deployer)={vars(self)}")

    def info(self):
        self.run_function([MAMBA, "info"], env=self.env)

    def deploy_conda_environments(self, worklist):
        for env_yaml in worklist:
            info(f"{env_yaml=}")
            returncode = self.deploy_env(env_yaml)
            if returncode:
                error(f"{returncode=} for {env_yaml.name}")

    def deploy_env(self, env_yaml: Path) -> int:
        env_name = env_yaml.stem
        options = []
        if self.mode == "keep":
            env_dir = self.envs_dir / env_name
            if env_dir.is_dir():
                info(f"using existing environment: {env_dir!s}")
                return 0
        elif self.mode == "force":
            options.append("--force")
        options.append("--offline")
        mamba_command = [MAMBA, "env", "create"] + options
        mamba_command += ["-n", env_name, "-f", DEFS_DIR / env_yaml]
        if self.dry_run:
            mamba_command[:0] = ["/usr/bin/env", "echo"]
        debug(f"{mamba_command=}")
        timestamp = dt.now().strftime("%Y%m%d-%H%M%S")
        log_path = self.log_dir / f"{timestamp}-{env_yaml.stem}.log"
        info(f"{log_path=}")
        with log_path.open("wb") as fout:
            with self.console.status(f"Installing {env_yaml}..."):
                result = self.run_function(
                    mamba_command, env=self.env, stderr=STDOUT, stdout=fout
                )
        return result.returncode

    def deploy_etc(self):
        if self.etc_dir.exists():
            if self.mode != "keep":
                warning(f"etc dir already exists {self.etc_dir}")
            info(f"clearing {self.etc_dir}")
            rmtree(self.etc_dir)
        info(f"copying {ETC_SOURCE_DIR} to {self.etc_dir}")
        copytree(
            src=ETC_SOURCE_DIR,
            dst=self.etc_dir,
            symlinks=True,
            dirs_exist_ok=True,
        )
