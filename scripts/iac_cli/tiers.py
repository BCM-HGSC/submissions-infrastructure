"""Subcommands that act on tiers: deploy, promote, status."""

import os
from pathlib import Path

from .common import Context, IacError
from .exit_codes import MISSING_DEPENDENCY, SUCCESS


def deploy(
    ctx: Context,
    *,
    tier: str,
    offline: bool,
    keep: bool,
    overwrite: bool,
    skip_disk_check: bool,
) -> int:
    """Run the engine's deployer in a sanitized environment."""
    python = require_engine_python(ctx)
    assignments = [f"PYTHONPATH={ctx.scripts_dir}"]
    if ctx.verbose:
        assignments.append("VERBOSE=1")
    options = [
        flag
        for flag, enabled in (
            ("--dry-run", ctx.dry_run),
            ("--offline", offline),
            ("--keep", keep),
            ("--overwrite", overwrite),
            ("--skip-disk-check", skip_disk_check),
        )
        if enabled
    ]
    command = [
        str(ctx.scripts_dir / "sanitize-command"),
        *assignments,
        str(python),
        "-m",
        "engine",
        str(ctx.target),
        tier,
        *options,
    ]
    # The engine's own --dry-run changes nothing, so always run it.
    return ctx.run(command, cwd=ctx.target)


def promote(ctx: Context) -> int:
    """
    Swap the production and staging links.

    Delegates to scripts/promote_staging under the engine's Python, which
    has the modules that script imports.
    """
    python = require_engine_python(ctx)
    command = [str(python), str(ctx.scripts_dir / "promote_staging")]
    if ctx.dry_run:
        command.append("--dry-run")
    env = {**os.environ, "IAC_TIER_DIR": str(ctx.infrastructure / "staging")}
    return ctx.run(command, env=env)


def status(ctx: Context) -> int:
    """Print the state of the target. Reads only."""
    for line in status_lines(ctx):
        print(line)
    return SUCCESS


def status_lines(ctx: Context) -> list[str]:
    micromamba = ctx.engine_home / "micromamba"
    return [
        f"target:      {ctx.target}  (from {ctx.target_source})",
        f"engine:      {describe_link(ctx.engine_home / 'engine')}",
        f"micromamba:  {'present' if micromamba.is_file() else 'missing'}",
        f"staging:     {describe_tier(ctx.infrastructure / 'staging')}",
        f"production:  {describe_tier(ctx.infrastructure / 'production')}",
    ]


def require_engine_python(ctx: Context) -> Path:
    python = ctx.engine_home / "engine/bin/python3"
    if not python.is_file():
        raise IacError(
            MISSING_DEPENDENCY,
            f"No engine at {python.parent.parent}; run `iac bootstrap` first",
        )
    return python


def describe_tier(link: Path) -> str:
    """Where a tier link points and what was deployed there."""
    description = describe_link(link)
    if not link.is_symlink() or not link.exists():
        return description
    commit = read_meta(link / "meta/commit")
    if commit is None:
        return f"{description}, not deployed"
    version = read_meta(link / "meta/description") or "no description"
    return f"{description}, commit {commit[:12]} ({version})"


def describe_link(link: Path) -> str:
    if link.is_symlink():
        suffix = "" if link.exists() else " (dangling)"
        return f"-> {link.readlink()}{suffix}"
    return "not a symlink" if link.exists() else "missing"


def read_meta(path: Path) -> str | None:
    """The content of a meta file, or None if absent or a recorded failure."""
    if not path.is_file():
        return None
    text = path.read_text().strip()
    return None if text in ("", "ERROR") else text
