from logging import basicConfig, DEBUG, INFO, StreamHandler

try:
    from rich.logging import RichHandler

    ROOT_HANDLER = RichHandler(show_time=False)
    ROOT_FORMAT = "%(message)s"
except:
    ROOT_HANDLER = StreamHandler()
    ROOT_FORMAT = "%(levelname)s: %(message)s"


def config_logging(verbose: bool = False) -> None:
    level = DEBUG if verbose else INFO
    basicConfig(level=level, format=ROOT_FORMAT, handlers=[ROOT_HANDLER])
