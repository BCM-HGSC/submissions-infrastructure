"""Subcommands that act on tiers: deploy, promote, status."""

from pathlib import Path

from .bootstrap import link_color, other_color
from .common import Context, IacError, log, replace_symlink, sanitized_env
from .exit_codes import INVALID_STATE, MISSING_DEPENDENCY, SUCCESS


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
    command = [str(python), "-m", "engine", str(ctx.target), tier, *options]
    extra = {"PYTHONPATH": str(ctx.scripts_dir)}
    if ctx.verbose:
        extra["VERBOSE"] = "1"
    env = sanitized_env(ctx.engine_home, **extra)
    # The engine's own --dry-run changes nothing, so always run it.
    return ctx.run(command, cwd=ctx.target, env=env)


def promote(ctx: Context) -> int:
    """
    Make the staging tier production and point staging at the other color.

    Each link is replaced atomically, production first, so production always
    names a tier. An interruption between the two leaves both links on the
    same color, which `iac bootstrap` repairs.
    """
    staging = ctx.infrastructure / "staging"
    production = ctx.infrastructure / "production"
    color = link_color(staging)
    require_deployed(staging)
    if production.is_symlink() or production.exists():
        if link_color(production) == color:
            raise IacError(
                INVALID_STATE,
                f"staging and production both point to {color}; "
                "`iac bootstrap` moves staging to the other color",
            )
    else:
        log.info("No production link yet; creating it")
    replace_symlink(ctx, production, color)
    replace_symlink(ctx, staging, other_color(color))
    return SUCCESS


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


def require_deployed(tier: Path) -> None:
    """Refuse a tier that no deploy has completed in."""
    if not is_deployed(tier):
        raise IacError(
            INVALID_STATE,
            f"{tier} has not been deployed (no meta/commit or etc/profile.sh); "
            "run `iac deploy` first",
        )


def is_deployed(tier: Path) -> bool:
    """
    Whether a deploy ran to completion in this tier.

    The engine removes meta/ before it starts and writes meta/commit last.
    """
    return (tier / "meta/commit").is_file() and (tier / "etc/profile.sh").is_file()


def describe_tier(link: Path) -> str:
    """Where a tier link points and what was deployed there."""
    description = describe_link(link)
    if not link.is_symlink() or not link.exists():
        return description
    if not is_deployed(link):
        return f"{description}, not deployed"
    commit = read_meta(link / "meta/commit")
    version = read_meta(link / "meta/description")
    return f"{description}, commit {commit[:12]} ({version})"


def describe_link(link: Path) -> str:
    if link.is_symlink():
        suffix = "" if link.exists() else " (dangling)"
        return f"-> {link.readlink()}{suffix}"
    return "not a symlink" if link.exists() else "missing"


def read_meta(path: Path) -> str:
    """The content of a meta file, or "unknown" if absent or empty."""
    text = path.read_text().strip() if path.is_file() else ""
    return text or "unknown"
