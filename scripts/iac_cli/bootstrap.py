"""Create the target layout and install or rotate the engine."""

import os
from pathlib import Path
import shutil

from .common import (
    Context,
    IacError,
    log,
    make_dir,
    replace_symlink,
    run_step,
)
from .exit_codes import INVALID_INPUT, MISSING_DEPENDENCY, OPERATION_FAILED

MINIMUM_FREE_GB = 5
ENGINE_NAMES = ("engine_a", "engine_b")
TIER_COLORS = ("blue", "green")
FETCH_REQUIREMENTS = (Path("/usr/bin/curl"), Path("/usr/bin/tar"))


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
        raise IacError(INVALID_INPUT, f"Engine definition not found: {engine_yaml}")
    link = ctx.engine_home / "engine"
    if link.exists() and not link.is_symlink():
        raise IacError(INVALID_INPUT, f"Not a symlink: {link}")
    package_cache = ctx.target / "conda_package_cache"
    make_dir(ctx, ctx.engine_home)
    make_dir(ctx, package_cache)
    micromamba = ensure_micromamba(ctx)

    engine_name = next_engine_name(current_engine_name(link))
    engine_path = ctx.engine_home / engine_name
    remove_old_engine(ctx, engine_path)
    command = [
        str(ctx.scripts_dir / "sanitize-command"),
        f"HOME={ctx.engine_home}",
        f"CONDA_PKGS_DIRS={package_cache}",
        str(micromamba),
        "env",
        "create",
        "--yes",
        "--prefix",
        str(engine_path),
        "--file",
        str(engine_yaml),
    ]
    if offline:
        command.append("--offline")
    log.info("Creating engine environment: %s", engine_path)
    if run_step(ctx, command, cwd=existing_ancestor(ctx.target)):
        raise IacError(
            OPERATION_FAILED,
            f"Failed to create {engine_path}; the active engine is unchanged",
        )
    replace_symlink(ctx, link, engine_name)


def ensure_tier_links(ctx: Context) -> None:
    """Create the staging and production links if they are missing."""
    staging = ctx.infrastructure / "staging"
    production = ctx.infrastructure / "production"
    has_staging = staging.is_symlink() or staging.exists()
    has_production = production.is_symlink() or production.exists()
    if has_staging and has_production:
        return
    if not has_staging and not has_production:
        replace_symlink(ctx, staging, "blue")
        replace_symlink(ctx, production, "green")
    elif has_staging:
        log.warning("No production link at %s; `iac promote` creates it", production)
    else:
        production_color = production.readlink().name if production.is_symlink() else ""
        if production_color not in TIER_COLORS:
            raise IacError(
                INVALID_INPUT, f"{production} is not a link to blue or green"
            )
        other = TIER_COLORS[1 - TIER_COLORS.index(production_color)]
        replace_symlink(ctx, staging, other)


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


def ensure_micromamba(ctx: Context) -> Path:
    """Fetch micromamba into engine_home if needed and check that it runs."""
    micromamba = ctx.engine_home / "micromamba"
    if not os.access(micromamba, os.X_OK):
        missing = [str(path) for path in FETCH_REQUIREMENTS if not path.is_file()]
        if missing:
            raise IacError(
                MISSING_DEPENDENCY,
                f"Fetching micromamba needs {' and '.join(missing)}",
            )
        log.info("Fetching micromamba into %s", ctx.engine_home)
        fetch = [str(ctx.scripts_dir / "fetch-micromamba"), str(ctx.engine_home)]
        if run_step(ctx, fetch) or not (ctx.dry_run or os.access(micromamba, os.X_OK)):
            raise IacError(MISSING_DEPENDENCY, f"Failed to fetch {micromamba}")
    if not ctx.dry_run and ctx.run([str(micromamba), "--version"], quiet=True):
        raise IacError(MISSING_DEPENDENCY, f"{micromamba} does not run")
    return micromamba


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
