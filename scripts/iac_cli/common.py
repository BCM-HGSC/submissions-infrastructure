"""Shared pieces: the run context, the error type, and command execution."""

from collections.abc import Callable
from dataclasses import dataclass
import logging
from pathlib import Path
import subprocess

log = logging.getLogger("iac")

Runner = Callable[..., int]


class IacError(Exception):
    """A failure to report to the user, carrying the exit code to use."""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Context:
    """Everything a subcommand needs to know about this invocation."""

    target: Path
    target_source: str
    scripts_dir: Path
    dry_run: bool = False
    verbose: bool = False
    run: Runner | None = None  # tests inject a fake; defaults to run_command

    def __post_init__(self) -> None:
        if self.run is None:
            object.__setattr__(self, "run", run_command)

    @property
    def repo_root(self) -> Path:
        return self.scripts_dir.parent

    @property
    def engine_home(self) -> Path:
        return self.target / "engine_home"

    @property
    def infrastructure(self) -> Path:
        return self.target / "infrastructure"


def run_step(ctx: Context, argv: list[str], **kwargs) -> int:
    """Run a command that changes something, or describe it in a dry run."""
    if ctx.dry_run:
        log.info("[DRY RUN] Would run: %s", " ".join(argv))
        return 0
    log.debug("Running: %s", " ".join(argv))
    return ctx.run(argv, **kwargs)


def make_dir(ctx: Context, path: Path) -> None:
    if path.is_dir():
        return
    if ctx.dry_run:
        log.info("[DRY RUN] Would create directory: %s", path)
        return
    log.debug("Creating directory: %s", path)
    path.mkdir(parents=True, exist_ok=True)


def replace_symlink(ctx: Context, link: Path, target_name: str) -> None:
    """Point link at target_name atomically, whether or not link exists."""
    if ctx.dry_run:
        log.info("[DRY RUN] Would link: %s -> %s", link, target_name)
        return
    log.info("Linking: %s -> %s", link, target_name)
    temporary = link.with_name(link.name + ".new")
    if temporary.is_symlink():
        temporary.unlink()
    temporary.symlink_to(target_name)
    temporary.replace(link)


def run_command(
    argv: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    quiet: bool = False,
) -> int:
    """Run a command and return its exit status."""
    stdout = subprocess.DEVNULL if quiet else None
    return subprocess.run(argv, cwd=cwd, env=env, stdout=stdout, check=False).returncode
