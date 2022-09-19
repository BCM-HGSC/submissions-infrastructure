from logging import basicConfig, DEBUG, INFO, StreamHandler
from os import environ
from typing import Optional

try:
    from rich.logging import RichHandler

    ROOT_HANDLER = RichHandler(show_time=False)
    ROOT_FORMAT = "%(message)s"
except:
    ROOT_HANDLER = StreamHandler()
    ROOT_FORMAT = "%(levelname)s: %(message)s"


def config_logging(verbose: Optional[bool] = None) -> None:
    if verbose is None:
        verbose = bool(environ.get("VERBOSE", ""))
    level = DEBUG if verbose else INFO
    basicConfig(level=level, format=ROOT_FORMAT, handlers=[ROOT_HANDLER])
