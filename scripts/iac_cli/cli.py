"""Argument parsing and dispatch for the `iac` command."""

from argparse import (
    SUPPRESS,
    ArgumentParser,
    Namespace,
    RawDescriptionHelpFormatter,
)
import logging
import os
from pathlib import Path
import sys
from typing import NoReturn

from . import bootstrap as bootstrap_module
from . import tiers
from .common import Context, IacError, log
from .config import resolve_target
from .exit_codes import HELP_TEXT, SUCCESS, USAGE

SCRIPTS_DIR = Path(__file__).resolve().parent.parent

DESCRIPTION = """\
Manage the conda-based infrastructure under one target directory.

The target comes from --target, the IAC_PARENT environment variable, or
iac_parent in a config file; run a subcommand with no target to see the
list. --target, --verbose and --dry-run work before or after the subcommand.
"""


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )
    try:
        return args.handler(make_context(args), args)
    except IacError as e:
        log.error("%s", e)
        return e.code


def build_parser() -> ArgumentParser:
    parser = IacArgumentParser(
        prog="iac",
        description=DESCRIPTION,
        epilog=HELP_TEXT,
        formatter_class=RawDescriptionHelpFormatter,
    )
    add_common_options(parser, at_top_level=True)
    subparsers = parser.add_subparsers(
        dest="subcommand", metavar="SUBCOMMAND", required=True
    )

    def add_subcommand(name: str, handler, summary: str) -> ArgumentParser:
        subparser = subparsers.add_parser(name, help=summary, description=summary)
        subparser.set_defaults(handler=handler)
        add_common_options(subparser, at_top_level=False)
        return subparser

    bootstrap = add_subcommand(
        "bootstrap",
        run_bootstrap,
        "Create whatever the target is missing. Never removes anything.",
    )
    add_install_options(bootstrap)

    engine = add_subcommand(
        "engine",
        run_engine,
        "Install a fresh engine in the inactive slot and switch to it.",
    )
    add_install_options(engine)

    deploy = add_subcommand(
        "deploy", run_deploy, "Install the environments and resources into a tier."
    )
    deploy.add_argument(
        "--tier", default="staging", help="tier to deploy to (default: staging)"
    )
    add_install_options(deploy)
    existing = deploy.add_mutually_exclusive_group()
    existing.add_argument(
        "--keep", action="store_true", help="keep environments that already exist"
    )
    existing.add_argument(
        "--overwrite",
        action="store_true",
        help="replace the contents of a tier that is not normally replaced",
    )

    add_subcommand(
        "promote", run_promote, "Make staging the production tier and swap the links."
    )
    add_subcommand("status", run_status, "Show the target, engine, and tier links.")
    return parser


def add_common_options(parser: ArgumentParser, *, at_top_level: bool) -> None:
    """
    Options accepted both before and after the subcommand.

    The subcommand copies use SUPPRESS so that an option given before the
    subcommand is not overwritten by the subcommand's default.
    """

    def default(value):
        return value if at_top_level else SUPPRESS

    parser.add_argument(
        "--target",
        metavar="IAC_PARENT",
        default=default(None),
        help="directory holding engine_home and infrastructure",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=default(False),
        help="log debugging detail",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        default=default(False),
        help="show what would be done; change nothing",
    )


def add_install_options(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--offline", action="store_true", help="install from the package cache only"
    )
    parser.add_argument(
        "--skip-disk-check",
        action="store_true",
        help="continue even when free disk space is below the minimum",
    )


def make_context(args: Namespace) -> Context:
    target, source = resolve_target(
        args.target,
        environ=os.environ,
        repo_root=SCRIPTS_DIR.parent,
        home=Path.home(),
        cwd=Path.cwd(),
    )
    log.debug("target=%s (from %s)", target, source)
    return Context(
        target=target,
        target_source=source,
        scripts_dir=SCRIPTS_DIR,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


def run_bootstrap(ctx: Context, args: Namespace) -> int:
    bootstrap_module.bootstrap(
        ctx, offline=args.offline, skip_disk_check=args.skip_disk_check
    )
    return SUCCESS


def run_engine(ctx: Context, args: Namespace) -> int:
    bootstrap_module.install_engine(
        ctx, offline=args.offline, skip_disk_check=args.skip_disk_check
    )
    return SUCCESS


def run_deploy(ctx: Context, args: Namespace) -> int:
    return tiers.deploy(
        ctx,
        tier=args.tier,
        offline=args.offline,
        keep=args.keep,
        overwrite=args.overwrite,
        skip_disk_check=args.skip_disk_check,
    )


def run_promote(ctx: Context, args: Namespace) -> int:  # noqa: ARG001
    return tiers.promote(ctx)


def run_status(ctx: Context, args: Namespace) -> int:  # noqa: ARG001
    return tiers.status(ctx)


class IacArgumentParser(ArgumentParser):
    """An ArgumentParser whose usage errors exit with our USAGE code."""

    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(USAGE, f"{self.prog}: error: {message}\n")
