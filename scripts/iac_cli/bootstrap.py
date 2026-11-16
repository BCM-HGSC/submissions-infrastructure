"""Create the target layout and install or rotate the engine."""

from pathlib import Path
import shutil

from .common import (
    Context,
    IacError,
    log,
    make_dir,
    replace_symlink,
    run_step,
    sanitized_env,
)
from .exit_codes import INVALID_STATE, OPERATION_FAILED
from .micromamba import ensure_micromamba

MINIMUM_FREE_GB = 5
ENGINE_NAMES = ("engine_a", "engine_b")
TIER_COLORS = ("blue", "green")


def bootstrap(ctx: Context, *, offline: bool, skip_disk_check: bool) -> None:
    """
    Create whatever is missing from the target. Never removes anything.

    An existing engine is left alone; `iac engine` rotates it.
    """
    require_disk_space(ctx.target, skip=skip_disk_check)
    make_dir(ctx, ctx.target / "conda_package_cache")
    make_dir(ctx, ctx.engine_home)
    for color in TIER_COLORS:
        make_dir(ctx, ctx.infrastructure / color)
    if (ctx.engine_home / "engine").is_symlink():
        log.info("Engine already installed; use `iac engine` to rotate it")
    else:
        install_engine(ctx, offline=offline, skip_disk_check=True)
    ensure_tier_links(ctx)


def install_engine(ctx: Context, *, offline: bool, skip_disk_check: bool) -> None:
    """Build a fresh engine in the inactive slot, then switch the link to it."""
    require_disk_space(ctx.target, skip=skip_disk_check)
    engine_yaml = ctx.repo_root / "resources/defs/special/engine.yaml"
    if not engine_yaml.is_file():
        raise IacError(INVALID_STATE, f"Engine definition not found: {engine_yaml}")
    link = ctx.engine_home / "engine"
    if link.exists() and not link.is_symlink():
        raise IacError(INVALID_STATE, f"Not a symlink: {link}")
    package_cache = ctx.target / "conda_package_cache"
    make_dir(ctx, ctx.engine_home)
    make_dir(ctx, package_cache)
    micromamba = ensure_micromamba(ctx, offline=offline)

    engine_name = next_engine_name(current_engine_name(link))
    engine_path = ctx.engine_home / engine_name
    remove_old_engine(ctx, engine_path)
    command = [str(micromamba), "env", "create", "--yes"]
    command += ["--prefix", str(engine_path), "--file", str(engine_yaml)]
    if offline:
        command.append("--offline")
    env = sanitized_env(ctx.engine_home, CONDA_PKGS_DIRS=str(package_cache))
    log.info("Creating engine environment: %s", engine_path)
    if run_step(ctx, command, cwd=existing_ancestor(ctx.target), env=env):
        raise IacError(
            OPERATION_FAILED,
            f"Failed to create {engine_path}; the active engine is unchanged",
        )
    replace_symlink(ctx, link, engine_name)


def ensure_tier_links(ctx: Context) -> None:
    """
    Create the staging and production links if they are missing.

    Also repairs the state an interrupted promotion leaves behind, where
    both links name the same color: staging moves to the other one.
    """
    staging = ctx.infrastructure / "staging"
    production = ctx.infrastructure / "production"
    for link in (staging, production):
        if link.exists() and not link.is_symlink():
            raise IacError(INVALID_STATE, f"Not a symlink: {link}")
    if not staging.is_symlink() and not production.is_symlink():
        replace_symlink(ctx, staging, TIER_COLORS[0])
        replace_symlink(ctx, production, TIER_COLORS[1])
    elif not production.is_symlink():
        log.warning("No production link at %s; `iac promote` creates it", production)
    else:
        production_color = link_color(production)
        if not staging.is_symlink():
            replace_symlink(ctx, staging, other_color(production_color))
        elif link_color(staging) == production_color:
            log.warning("staging and production both point to %s", production_color)
            replace_symlink(ctx, staging, other_color(production_color))


def link_color(link: Path) -> str:
    """The color a tier link names. Raises unless it is exactly blue or green."""
    if not link.is_symlink():
        raise IacError(INVALID_STATE, f"Not a symlink: {link}")
    color = str(link.readlink())
    if color not in TIER_COLORS:
        raise IacError(
            INVALID_STATE,
            f"{link} points to {color}; expected {' or '.join(TIER_COLORS)}",
        )
    return color


def other_color(color: str) -> str:
    return TIER_COLORS[1 - TIER_COLORS.index(color)]


def require_disk_space(target: Path, *, skip: bool) -> None:
    where = existing_ancestor(target)
    free_gb = shutil.disk_usage(where).free / 1024**3
    log.debug("%.1f GB free at %s", free_gb, where)
    if free_gb >= MINIMUM_FREE_GB:
        return
    message = f"{free_gb:.1f} GB free at {where}; {MINIMUM_FREE_GB} GB needed"
    if not skip:
        raise IacError(OPERATION_FAILED, f"{message}. Override: --skip-disk-check")
    log.warning("%s. Continuing because of --skip-disk-check", message)


def current_engine_name(link: Path) -> str | None:
    return link.readlink().name if link.is_symlink() else None


def next_engine_name(current: str | None) -> str:
    """The slot to build next: the one the engine link does not point to."""
    return ENGINE_NAMES[1] if current == ENGINE_NAMES[0] else ENGINE_NAMES[0]


def remove_old_engine(ctx: Context, engine_path: Path) -> None:
    if not engine_path.exists():
        return
    if ctx.dry_run:
        log.info("[DRY RUN] Would remove inactive engine: %s", engine_path)
        return
    log.info("Removing inactive engine: %s", engine_path)
    shutil.rmtree(engine_path)


def existing_ancestor(path: Path) -> Path:
    """The nearest directory at or above path that exists."""
    while not path.is_dir():
        path = path.parent
    return path
