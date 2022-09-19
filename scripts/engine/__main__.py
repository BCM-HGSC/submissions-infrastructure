from logging import info
from os import environ
from sys import argv, executable

from .logging import config_logging


def main():
    config_logging()
    info(f"running {__file__}:main")
    info(f"{environ=}")
    info(f"{executable=}")
    info(f"{argv=}")
    return "TODO"


if __name__ == "__main__":
    exit(main())
