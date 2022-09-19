"""
Python package that is the engine for maintaining a collection of installed software,
primarily using conda.
"""

from logging import info
from os import execve
from pathlib import Path
from sys import argv, executable
from typing import NoReturn

from .logging import config_logging




def exec() -> NoReturn:
    """
    Replace the current Python process with the python interpreter in the engine.
    Run run_engine.py, passing in the sub-command, target, and any other arguments.
    Use the stem of sys.argv[0] for the sub-command.
    """
    config_logging()
    info(f"{executable=}")
    info(f"{argv=}")
    script, *args = argv
    script_stem = Path(script).stem
    command = script_stem if script_stem != "run" else args.pop(0)
    target_path = Path(args.pop(0)).resolve()
    info("===")
    script_dir = Path(__file__).resolve().parent.parent
    engine_home_path = target_path / "engine_home"
    engine_python = engine_home_path / "engine/bin/python3"
    env = dict(
        CONDARC=target_path / "infrastructure/staging/condarc",
        HOME=engine_home_path,
        PYTHONPATH=script_dir,
    )
    args[:0] = [str(x) for x in (engine_python, "-m", "engine", command, target_path)]
    info(f"{command=}")
    info(f"{script_dir=}")
    info(f"{target_path=}")
    info(f"{engine_python=}")
    info(f"{args=}")
    info(f"{env=}")
    # execve("/usr/bin/env", ["/usr/bin/env"], env)
    execve(engine_python, args, env)
