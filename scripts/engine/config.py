from logging import DEBUG, INFO, StreamHandler, basicConfig
from os import environ

try:
    from rich.logging import RichHandler

    ROOT_HANDLER = RichHandler(show_time=False)
    ROOT_FORMAT = "%(message)s"
except Exception:
    ROOT_HANDLER = StreamHandler()
    ROOT_FORMAT = "%(levelname)s: %(message)s"


def config_logging(verbose: bool | None = None) -> None:
    if verbose is None:
        verbose = bool(environ.get("VERBOSE", ""))
    level = DEBUG if verbose else INFO
    basicConfig(level=level, format=ROOT_FORMAT, handlers=[ROOT_HANDLER])
