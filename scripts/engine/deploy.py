"""
Module responsible for actually deploying sofwware to a tier.
(A "tier" is a top-level directory or symlink such as "staging" or "production".)
"""

from datetime import datetime as dt
from logging import critical, debug, error, info, warning
from pathlib import Path
from re import match
from shutil import copytree, rmtree
from subprocess import DEVNULL, PIPE, STDOUT, run
from sys import executable, platform
from typing import Optional

from rich.console import Console


MAMBA = Path(executable).with_name("mamba")  # mamba in same bin/ as python3
CODE_ROOT_DIR = Path(__file__).parent.parent.parent
RESOURCES_DIR = CODE_ROOT_DIR / "resources"
DEFS_DIR = RESOURCES_DIR / "defs"
BIN_SOURCE_DIR = RESOURCES_DIR / "bin"
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
    prod_path = setup_tier_path(target, "production")
    tier_path = setup_tier_path(target, tier)
    if tier_path == prod_path:
        critical(f"attempt to modify {prod_path=}")
        exit(4)
    keep = (mode == "keep")
    if tier_path.exists() and not keep:
        if match(r"^(dev.*|test.*|staging)$", tier) or  mode == "force":
            rmtree(tier_path)
            tier_path.mkdir()
    deployer = MambaDeployer(target, tier_path, dry_run, offline, keep, run_function)
    if deployer.keep:
        deployer.info()
    worklist = list_conda_environment_defs()
    deployer.deploy_conda_environments(worklist)
    if deployer.dry_run:
        return
    deployer.deploy_bin()
    deployer.deploy_etc()
    deployer.store_git_info()


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
        keep: bool=False,
        run_function=run,
    ):
        self.dry_run = dry_run
        self.offline = offline
        self.keep = keep
        self.run_function = run_function
        self.envs_dir = tier_path / "conda/envs"
        self.bin_dir = tier_path / "bin"
        self.etc_dir = tier_path / "etc"
        self.meta_dir = tier_path / "meta"
        self.env = dict(
            HOME=target / "engine_home",
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
        if self.keep:
            env_dir = self.envs_dir / env_name
            if env_dir.is_dir():
                info(f"using existing environment: {env_dir!s}")
                return 0
        if self.offline:
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

    def deploy_bin(self):
        self.copy_resource_dir(BIN_SOURCE_DIR, self.bin_dir)

    def deploy_etc(self):
        self.copy_resource_dir(ETC_SOURCE_DIR, self.etc_dir)

    def copy_resource_dir(self, src_dir, dst_dir):
        if dst_dir.exists():
            if self.keep:
                warning(f"destination dir already exists: {dst_dir}")
            info(f"clearing {dst_dir}")
            rmtree(dst_dir)
        info(f"copying {src_dir} to {dst_dir}")
        copytree(
            src=src_dir,
            dst=dst_dir,
            symlinks=True,
            dirs_exist_ok=True,
        )

    def store_git_info(self) -> None:
        self.meta_dir.mkdir(exist_ok=True)
        self.write_meta("commit", ["rev-parse", "HEAD"], True)
        self.write_meta("tree_hash", ["rev-parse", "HEAD:"], True)
        (
            self.write_meta("description", ["describe", "--dirty"])
            or self.write_meta("description", ["describe", "--dirty", "--tags"])
            or self.write_meta("description", ["describe", "--dirty", "--all"])
        )

    def write_meta(self, dest_name, subcommand, expect_fail=True) -> bool:
        command_prefix = ["git", "-C", CODE_ROOT_DIR]
        command = command_prefix + subcommand
        stderr = DEVNULL if expect_fail else None
        result = self.run_function(command, stdout=PIPE, stderr=stderr)
        dest_path = self.meta_dir / dest_name
        dest_path.write_bytes(result.stdout or b"ERROR\n")
        return result.returncode == 0
