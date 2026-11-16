"""
Module responsible for actually deploying sofwware to a tier.
(A "tier" is a top-level directory or symlink such as "staging" or "production".)
"""

from datetime import datetime as dt
from logging import critical, debug, error, info, warning
from pathlib import Path
from re import match
import shutil
from subprocess import DEVNULL, PIPE, STDOUT
import sys

from rich.console import Console

from .command_runner import CommandRunnerProtocol, RealCommandRunner
from .filesystem import FileSystemProtocol, RealFileSystem
from .validators import (
    DiskSpaceError,
    PathTraversalError,
    ValidationError,
    check_disk_space,
    validate_env_yaml,
    validate_safe_path,
)

CODE_ROOT_DIR = Path(__file__).parent.parent.parent
RESOURCES_DIR = CODE_ROOT_DIR / "resources"
DEFS_DIR = RESOURCES_DIR / "defs"
BIN_SOURCE_DIR = RESOURCES_DIR / "bin"
ETC_SOURCE_DIR = RESOURCES_DIR / "etc"


def deploy_tier(
    target: Path,
    tier: str,
    *,
    dry_run: bool,
    offline: bool,
    mode: str | None = None,
    skip_disk_check: bool = False,
    filesystem: FileSystemProtocol | None = None,
    command_runner: CommandRunnerProtocol | None = None,
    env_yamls: list[Path] | None = None,
    mamba_path: Path | None = None,
) -> None:
    if filesystem is None:
        filesystem = RealFileSystem()
    if command_runner is None:
        command_runner = RealCommandRunner()

    mamba_binary = mamba_path if mamba_path is not None else find_mamba()

    worklist = env_yamls if env_yamls is not None else list_conda_environment_defs()
    require_disk_space(target, worklist, force=skip_disk_check)
    check_mamba(filesystem, mamba_binary)
    # Only locate production; never create it.
    prod_path = setup_tier_path(target, "production", filesystem, create=False)
    tier_path = setup_tier_path(target, tier, filesystem, create=not dry_run)
    if tier_path == prod_path:
        critical(f"Cannot modify production tier: tier={tier} resolves to {tier_path}")
        sys.exit(4)
    keep = mode == "keep"
    if (
        filesystem.exists(tier_path)
        and not keep
        and (match(r"^(dev.*|test.*|staging)$", tier) or mode == "force")
    ):
        if dry_run:
            info(f"[DRY RUN] Would remove and recreate {tier_path}")
        else:
            filesystem.rmtree(tier_path)
            filesystem.mkdir(tier_path)
    deployer = MambaDeployer(
        target,
        tier_path,
        dry_run=dry_run,
        offline=offline,
        keep=keep,
        command_runner=command_runner,
        filesystem=filesystem,
        mamba_binary=mamba_binary,
    )
    if keep and not dry_run:
        deployer.info()
    failed = deployer.deploy_conda_environments(worklist)
    if dry_run:
        return
    if failed:
        # Stop before writing meta/, which marks a tier as deployed.
        critical(f"Failed to deploy environments: {', '.join(failed)}")
        sys.exit(4)
    deployer.deploy_bin()
    deployer.deploy_etc()
    deployer.store_git_info()


def require_disk_space(target: Path, worklist: list[Path], *, force: bool) -> None:
    """Exit if there is too little space to deploy; log any lesser concern."""
    try:
        _success, message = check_disk_space(
            target, operation="deploy", env_yamls=worklist, force=force
        )
    except DiskSpaceError as e:
        critical(str(e))
        sys.exit(4)
    if message.startswith(("WARNING:", "ERROR:")):
        warning(message)
    elif message:
        info(message)


def check_mamba(filesystem: FileSystemProtocol, mamba_binary: Path | None) -> None:
    info(f"{mamba_binary=}")
    if mamba_binary is None:
        critical("Required binary not found: mamba not in PATH")
        sys.exit(2)
    if not filesystem.is_file(mamba_binary):
        critical(f"Required binary not found: mamba at {mamba_binary}")
        sys.exit(2)


def find_mamba() -> Path | None:
    """
    Locate mamba, preferring the engine this interpreter belongs to.

    The deploy wrapper runs the engine with a minimal PATH, so PATH is only
    a fallback for development and tests.
    """
    engine_dir = Path(sys.executable).parent.parent
    for candidate in (engine_dir / "bin/mamba", engine_dir / "condabin/mamba"):
        if candidate.is_file():
            return candidate
    on_path = shutil.which("mamba")
    return Path(on_path) if on_path else None


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


def setup_tier_path(
    target: Path, tier: str, filesystem: FileSystemProtocol, *, create: bool = True
) -> Path:
    """
    Setup tier path with validation and directory creation.

    Args:
        target: Target directory path
        tier: Tier name
        filesystem: Filesystem abstraction for I/O operations
        create: Create the tier directory if it does not exist

    Returns:
        Resolved tier path
    """
    info(f"{target=}")
    info(f"{tier=}")

    # Validate target is absolute
    if not target.is_absolute():
        critical(f"Target directory must be an absolute path: {target}")
        sys.exit(3)

    # Validate tier name pattern
    if not match(r"^(blue|green|staging|production|dev.*|test.*)$", tier):
        critical(
            f"Invalid tier name: {tier}. Must match pattern: blue|green|staging|production|dev.*|test.*"
        )
        sys.exit(3)

    if not filesystem.is_dir(target):
        critical(f"Target directory does not exist or is not a directory: {target}")
        sys.exit(3)
    tier_path = validate_tier_path(target, tier)

    # Validate that tier path is safely within target directory
    try:
        validate_safe_path(tier_path, target)
    except PathTraversalError as e:
        critical(f"Path traversal detected: {e}")
        sys.exit(3)

    info(f"{tier_path=}")
    if create and not filesystem.is_dir(tier_path):
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
        *,
        dry_run: bool,
        offline: bool,
        keep: bool = False,
        command_runner: CommandRunnerProtocol | None = None,
        filesystem: FileSystemProtocol | None = None,
        mamba_binary: Path | None = None,
    ):
        self.dry_run = dry_run
        self.offline = offline
        self.keep = keep
        self.command_runner = (
            command_runner if command_runner is not None else RealCommandRunner()
        )
        self.filesystem = filesystem if filesystem is not None else RealFileSystem()
        self.mamba = mamba_binary if mamba_binary is not None else find_mamba()
        self.tier_name = tier_path.name
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
        # Outside the tier, so logs survive the tier being replaced.
        self.log_dir = target / "logs"
        self.console = Console()
        debug(f"vars(deployer)={vars(self)}")

    def info(self) -> None:
        self.command_runner.run([self.mamba, "info"], env=self.env)

    def deploy_conda_environments(self, worklist: list[Path]) -> list[str]:
        """Attempt every environment; return the names of those that failed."""
        failed = []
        for env_yaml in worklist:
            info(f"{env_yaml=}")
            returncode = self.deploy_env(env_yaml)
            if returncode:
                error(
                    f"Failed to deploy environment {env_yaml.name} (exit code {returncode})"
                )
                failed.append(env_yaml.stem)
        return failed

    def deploy_env(self, env_yaml: Path) -> int:
        # Validate YAML file exists and is valid
        yaml_full_path = DEFS_DIR / env_yaml if not env_yaml.is_absolute() else env_yaml
        if not yaml_full_path.exists():
            error(f"Environment definition file does not exist: {yaml_full_path}")
            return 1

        # Validate YAML content
        try:
            validate_env_yaml(yaml_full_path)
        except ValidationError as e:
            error(f"Invalid environment definition: {e}")
            return 1

        env_name = env_yaml.stem
        options = []
        if self.keep:
            env_dir = self.envs_dir / env_name
            if self.filesystem.is_dir(env_dir):
                info(f"using existing environment: {env_dir!s}")
                return 0
        if self.offline:
            options.append("--offline")
        mamba_command = [self.mamba, "env", "create", "-y", *options]
        mamba_command += ["-n", env_name, "-f", DEFS_DIR / env_yaml]
        if self.dry_run:
            command_text = " ".join(str(arg) for arg in mamba_command)
            info(f"[DRY RUN] Would run: {command_text}")
            return 0
        info(f"{mamba_command=}")
        timestamp = dt.now().strftime("%Y%m%d-%H%M%S")
        log_name = f"{timestamp}-{self.tier_name}-{env_name}.log"
        log_path = self.log_dir / log_name
        info(f"{log_path=}")
        self.filesystem.mkdir(self.log_dir, parents=True, exist_ok=True)
        with (
            log_path.open("wb") as fout,
            self.console.status(f"Installing {env_yaml}..."),
        ):
            result = self.command_runner.run(
                mamba_command, env=self.env, stderr=STDOUT, stdout=fout
            )
        return result.returncode

    def deploy_bin(self) -> None:
        self.copy_resource_dir(BIN_SOURCE_DIR, self.bin_dir)

    def deploy_etc(self) -> None:
        self.copy_resource_dir(ETC_SOURCE_DIR, self.etc_dir)

    def copy_resource_dir(self, src_dir: Path, dst_dir: Path) -> None:
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
        self.write_meta("commit", ["rev-parse", "HEAD"])
        self.write_meta("tree_hash", ["rev-parse", "HEAD:"])
        (
            self.write_meta("description", ["describe", "--dirty"])
            or self.write_meta("description", ["describe", "--dirty", "--tags"])
            or self.write_meta("description", ["describe", "--dirty", "--all"])
        )

    def write_meta(self, dest_name: str, subcommand: list[str]) -> bool:
        command_prefix = ["git", "-C", str(CODE_ROOT_DIR)]
        command = command_prefix + subcommand
        result = self.command_runner.run(command, stdout=PIPE, stderr=DEVNULL)
        dest_path = self.meta_dir / dest_name
        self.filesystem.write_bytes(dest_path, result.stdout or b"ERROR\n")
        return result.returncode == 0
