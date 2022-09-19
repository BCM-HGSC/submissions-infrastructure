"""
Top-level execution point for deploying infrastructure.
"""

from argparse import ArgumentParser
from logging import debug, info
from os import environ
from os.path import isdir
from pathlib import Path
from sys import argv, executable

from .logging import config_logging


def main(cli_args: list[str]):
    config_logging()
    info(f"running {__file__}:main")
    info(f"{environ=}")
    info(f"{executable=}")
    debug(f"{cli_args=}")
    args = parse_command_line(cli_args)
    info(f"{args=}")
    return "TODO"


def parse_command_line(cli_args):
    """
    `python3 -m engine TIER TARGET_DIR`
    """
    parser = ArgumentParser(description="Deploy infrastructure")
    parser.add_argument("tier")
    parser.add_argument("target", type=dir_path)
    args = parser.parse_args()
    return args


def dir_path(string):
    if isdir(string):
        return Path(string)
    else:
        raise NotADirectoryError(string)


if __name__ == "__main__":
    exit(main(argv))
