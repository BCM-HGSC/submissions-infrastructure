"""
Top-level execution point for deploying infrastructure.
"""

from argparse import ArgumentParser
from logging import debug, info
from os import environ
from os.path import isdir
from pathlib import Path
from sys import argv, executable

from .config import config_logging
from .deploy import deploy_tier


def main(cli_args: list[str]):
    config_logging()
    info(f"running {__file__}:main")
    info(f"{environ=}")
    info(f"{executable=}")
    debug(f"{cli_args=}")
    args = parse_command_line(cli_args)
    info(f"{args=}")
    deploy_tier(args.target, args.tier, args.dry_run, args.offline, args.mode)


def parse_command_line(cli_args):
    """
    `python3 -m engine TIER TARGET_DIR`
    """
    parser = ArgumentParser(description="Deploy infrastructure")
    parser.add_argument("target", type=dir_path)
    parser.add_argument("tier")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("-n", "--dry-run", action="store_true")
    parser.add_argument(
        "--keep",
        action="store_const",
        const="keep",
        dest="mode",
        help="keep existing conda environments",
    )
    parser.add_argument(
        "--force",
        action="store_const",
        const="force",
        dest="mode",
        help="overwrite existing conda environments",
    )
    args = parser.parse_args()
    return args


def dir_path(string):
    if isdir(string):
        return Path(string)
    raise NotADirectoryError(string)


if __name__ == "__main__":
    exit(main(argv))
