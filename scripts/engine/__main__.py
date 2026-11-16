"""
Top-level execution point for deploying infrastructure.
"""

from argparse import ArgumentParser, ArgumentTypeError, Namespace
from logging import debug, info
from os import environ
from pathlib import Path
import sys

from .command_runner import RealCommandRunner
from .config import config_logging
from .deploy import deploy_tier
from .filesystem import RealFileSystem


def main(cli_args: list[str]) -> None:
    config_logging()
    info(f"running {__file__}:main")
    debug(f"{environ=}")
    info(f"{sys.executable=}")
    debug(f"{cli_args=}")
    args = parse_command_line(cli_args[1:])
    info(f"{args=}")

    # Create real implementations for production use
    filesystem = RealFileSystem()
    command_runner = RealCommandRunner()

    deploy_tier(
        args.target,
        args.tier,
        dry_run=args.dry_run,
        offline=args.offline,
        mode=args.mode,
        filesystem=filesystem,
        command_runner=command_runner,
    )


def parse_command_line(argv: list[str] | None = None) -> Namespace:
    """
    `python3 -m engine TARGET_DIR TIER`

    Parses argv, or sys.argv[1:] when argv is None.
    """
    parser = ArgumentParser(prog="deploy", description="Deploy infrastructure")
    parser.add_argument("target", type=dir_path)
    parser.add_argument("tier")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("-n", "--dry-run", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--keep",
        action="store_const",
        const="keep",
        dest="mode",
        help="keep existing conda environments",
    )
    mode.add_argument(
        "--force",
        action="store_const",
        const="force",
        dest="mode",
        help="overwrite existing conda environments",
    )
    return parser.parse_args(argv)


def dir_path(string: str) -> Path:
    path = Path(string)
    if path.is_dir():
        return path
    raise ArgumentTypeError(f"not a directory: {string}")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
