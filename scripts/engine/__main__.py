from logging import info
from os import environ
from sys import executable, argv

from .logging import config_logging

config_logging()
info(f"hello from {__file__}")
info(f"{environ=}")
info(f"{executable=}")
info(f"{argv=}")

exit("boom")
