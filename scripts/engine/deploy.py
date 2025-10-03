"""
Module responsible for actually deploying sofwware to a tier.
(A "tier" is a top-level directory or symlink such as "staging" or "production".)
"""

from datetime import datetime as dt
from logging import critical, debug, error, info, warning
from pathlib import Path
from re import match
from subprocess import DEVNULL, PIPE, STDOUT
import sys

from rich.console import Console

from .command_runner import CommandRunnerProtocol, RealCommandRunner
from .filesystem import FileSystemProtocol, RealFileSystem

MAMBA = Path(sys.executable).with_name("mamba")  # mamba in same bin/ as python3
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
    mode: str | None = None,
    run_function=None,  # Deprecated, use command_runner  # noqa: ARG001
    filesystem: FileSystemProtocol | None = None,
    command_runner: CommandRunnerProtocol | None = None,
) -> None:
    if filesystem is None:
        filesystem = RealFileSystem()
    if command_runner is None:
        command_runner = RealCommandRunner()

    check_mamba(filesystem)
    prod_path = setup_tier_path(target, "production", filesystem)
    tier_path = setup_tier_path(target, tier, filesystem)
    if tier_path == prod_path:
        critical(f"attempt to modify {prod_path=}")
        sys.exit(4)
    keep = mode == "keep"
    if (
        filesystem.exists(tier_path)
        and not keep
        and (match(r"^(dev.*|test.*|staging)$", tier) or mode == "force")
    ):
        filesystem.rmtree(tier_path)
        filesystem.mkdir(tier_path)
    deployer = MambaDeployer(
        target, tier_path, dry_run, offline, keep, command_runner, filesystem
    )
    if deployer.keep:
        deployer.info()
    worklist = list_conda_environment_defs()
    deployer.deploy_conda_environments(worklist)
    if deployer.dry_run:
        return
    deployer.deploy_bin()
    deployer.deploy_etc()
    deployer.store_git_info()


def check_mamba(filesystem: FileSystemProtocol):
    info(f"{MAMBA=}")
    if not filesystem.is_file(MAMBA):
        critical("mamba is missing")
        sys.exit(2)


def validate_tier_path(target: Path, tier: str) -> Path:
    """
    Pure function to compute and validate tier path.

    Args:
        target: Target directory path
        tier: Tier name (e.g., "staging", "production", "blue", "green")

    Returns:
        Resolved tier path

    Note:
        This is a pure function that only computes the path.
        It does not perform I/O or create directories.
    """
    return (target / "infrastructure" / tier).resolve()


def setup_tier_path(target, tier, filesystem: FileSystemProtocol):
    """
    Setup tier path with validation and directory creation.

    Args:
        target: Target directory path
        tier: Tier name
        filesystem: Filesystem abstraction for I/O operations

    Returns:
        Resolved tier path
    """
    info(f"{target=}")
    info(f"{tier=}")
    if not filesystem.is_dir(target):
        critical("target is not a directory")
        sys.exit(3)
    tier_path = validate_tier_path(target, tier)
    info(f"{tier_path=}")
    if not filesystem.is_dir(tier_path):
        filesystem.mkdir(tier_path, parents=True, exist_ok=True)
    return tier_path


def list_conda_environment_defs() -> list[Path]:
    worklist = sorted(DEFS_DIR.glob("universal/*.yaml"))
    if sys.platform == "linux":
        worklist.append(DEFS_DIR / "linux/linux.yaml")
    elif sys.platform == "darwin":
        worklist.append(DEFS_DIR / "mac/mac.yaml")
    worklist = [item for item in worklist if item.is_file()]
    debug(f"{worklist=}")
    return worklist


class MambaDeployer:
    def __init__(
        self,
        target: Path,
        tier_path: Path,
        dry_run: bool,
        offline: bool,
        keep: bool = False,
        command_runner: CommandRunnerProtocol | None = None,
        filesystem: FileSystemProtocol | None = None,
    ):
        self.dry_run = dry_run
        self.offline = offline
        self.keep = keep
        self.command_runner = (
            command_runner if command_runner is not None else RealCommandRunner()
        )
        self.filesystem = filesystem if filesystem is not None else RealFileSystem()
        self.envs_dir = tier_path / "conda/envs"
        self.bin_dir = tier_path / "bin"
        self.etc_dir = tier_path / "etc"
        self.meta_dir = tier_path / "meta"
        self.env = {
            "HOME": str(target / "engine_home"),
            "CONDA_ENVS_DIRS": str(self.envs_dir),
            "CONDA_PKGS_DIRS": str(target / "conda_package_cache"),
            "CONDA_CHANNELS": "conda-forge",
        }
        info(f"{self.env=}")
        self.log_dir = tier_path / "logs"
        self.filesystem.mkdir(self.log_dir, parents=True, exist_ok=True)
        self.console = Console()
        debug(f"vars(deployer)={vars(self)}")

    def info(self):
        self.command_runner.run([MAMBA, "info"], env=self.env)

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
            if self.filesystem.is_dir(env_dir):
                info(f"using existing environment: {env_dir!s}")
                return 0
        if self.offline:
            options.append("--offline")
        mamba_command = [MAMBA, "env", "create", "-y", *options]
        mamba_command += ["-n", env_name, "-f", DEFS_DIR / env_yaml]
        if self.dry_run:
            mamba_command[:0] = ["/usr/bin/env", "echo"]
        info(f"{mamba_command=}")
        timestamp = dt.now().strftime("%Y%m%d-%H%M%S")
        log_path = self.log_dir / f"{timestamp}-{env_yaml.stem}.log"
        info(f"{log_path=}")
        with (
            log_path.open("wb") as fout,
            self.console.status(f"Installing {env_yaml}..."),
        ):
            result = self.command_runner.run(
                mamba_command, env=self.env, stderr=STDOUT, stdout=fout
            )
        return result.returncode

    def deploy_bin(self):
        self.copy_resource_dir(BIN_SOURCE_DIR, self.bin_dir)

    def deploy_etc(self):
        self.copy_resource_dir(ETC_SOURCE_DIR, self.etc_dir)

    def copy_resource_dir(self, src_dir, dst_dir):
        if self.filesystem.exists(dst_dir):
            if self.keep:
                warning(f"destination dir already exists: {dst_dir}")
            info(f"clearing {dst_dir}")
            self.filesystem.rmtree(dst_dir)
        info(f"copying {src_dir} to {dst_dir}")
        self.filesystem.copytree(
            src=src_dir,
            dst=dst_dir,
            symlinks=True,
            dirs_exist_ok=True,
        )

    def store_git_info(self) -> None:
        self.filesystem.mkdir(self.meta_dir, exist_ok=True)
        self.write_meta("commit", ["rev-parse", "HEAD"], True)
        self.write_meta("tree_hash", ["rev-parse", "HEAD:"], True)
        (
            self.write_meta("description", ["describe", "--dirty"])
            or self.write_meta("description", ["describe", "--dirty", "--tags"])
            or self.write_meta("description", ["describe", "--dirty", "--all"])
        )

    def write_meta(self, dest_name, subcommand, expect_fail=True) -> bool:
        command_prefix = ["git", "-C", str(CODE_ROOT_DIR)]
        command = command_prefix + subcommand
        stderr = DEVNULL if expect_fail else None
        result = self.command_runner.run(command, stdout=PIPE, stderr=stderr)
        dest_path = self.meta_dir / dest_name
        dest_path.write_bytes(result.stdout or b"ERROR\n")
        return result.returncode == 0
