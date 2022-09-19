"""
Python package that is the engine for maintaining a collection of installed software,
primarily using conda.
"""

from logging import debug, info
from os import environ, execve
from pathlib import Path
from sys import argv, executable
from typing import NoReturn

from .logging import config_logging


def exec() -> NoReturn:
    """
    Replace the current Python process with the python interpreter in the engine.
    Run run_engine.py, passing in the tier, target, and any other arguments.
    Use the stem of sys.argv[0] for the tier.
    """
    config_logging()
    info(f"{executable=}")
    info(f"{argv=}")
    script, *args = argv
    debug(f"{script=}")
    tier = args.pop(0)
    target_path = Path(args.pop(0)).resolve()
    script_dir = Path(__file__).resolve().parent.parent
    engine_home_path = target_path / "engine_home"
    engine_python = engine_home_path / "engine/bin/python3"
    env = dict(
        # CONDARC=target_path / "infrastructure/staging/condarc",
        # HOME=engine_home_path,
        PYTHONPATH=script_dir,
        VERBOSE=environ.get("VERBOSE", ""),
    )
    args[:0] = [engine_python, "-m", "engine", tier, target_path]
    debug(f"{tier=}")
    debug(f"{script_dir=}")
    debug(f"{target_path=}")
    debug(f"{engine_python=}")
    info(f"{env=}")
    info(f"{args=}")
    info("execve")
    execve(engine_python, args, env)
