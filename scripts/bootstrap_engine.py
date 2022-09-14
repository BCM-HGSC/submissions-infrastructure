"""
Python script to bootstrap or rotate the infrastructure maintenance angine.

This script takes no command-line parameters.

Required environment variables:
CONDA: location of the conda executable
CONDARC: location of the condarc configuration file

Note that this variable is set from the current working directory:
HOME: directory used by conda as the "home directory" for configuration

Optional environment variables:
OFFLINE: if set run conda create with the --offline option
VERBOSE: if set, logging level is DEBUG, otherwise INFO
"""

from logging import DEBUG, INFO, StreamHandler, basicConfig, error, critical, info, debug
from os import environ
from pathlib import Path
from shutil import rmtree
from subprocess import run
from sys import argv, executable, exit, stderr

try:
    from rich.logging import RichHandler
    ROOT_HANDLER = RichHandler(show_time=False)
    ROOT_FORMAT = "%(message)s"
except:
    ROOT_HANDLER = StreamHandler()
    ROOT_FORMAT = "%(levelname)s: %(message)s"


def main(run_function=run):
    config_logging()
    info(f"starting {__file__}")
    if len(argv) > 1:
        critical(f"unknown command-line parameters: {argv[1:]}")
        return 2
    home = Path().resolve()
    executable_path = Path(executable)
    conda = env_path("CONDA")
    engine_yaml = Path(__file__).parent.parent / "resources/engine.yaml"
    info(f"{engine_yaml=}")
    assert engine_yaml.is_file()
    engine_path = rotate_engine_directories(home, executable_path, conda)
    symlink = home / "engine"
    conda_opts = ["--offline"] if environ["OFFLINE"] else []
    debug(f"{conda_opts=}")
    conda_command = [conda, "env", "create"] + conda_opts
    conda_command +=  ["-p", engine_path, "-f", engine_yaml]
    info(f"{conda_command=}")
    env = dict(
        HOME=home,
        CONDARC=env_path("CONDARC"),
    )
    info(f"{env=}")
    run_function(conda_command, check=True, env=env)
    if symlink.is_symlink():
        symlink.unlink()
    symlink.symlink_to(engine_path)


def config_logging():
    level = DEBUG if environ["VERBOSE"] else INFO
    basicConfig(level=level, format=ROOT_FORMAT, handlers=[ROOT_HANDLER])


def env_path(key: str) -> Path:
    if key not in environ:
        raise KeyError(f"missing environment variable {key}")
    return Path(environ[key]).resolve()


def rotate_engine_directories(home: Path, executable_path: Path, conda: Path) -> Path:
    """
    Clean out unused directories and select the directory to use next.
    """
    engine_path = None
    for letter in "abc":
        possible_path = home / f"engine_{letter}"
        conflicts_executable = executable_path.is_relative_to(possible_path)
        conflicts_conda = conda.is_relative_to(possible_path)
        if not (conflicts_executable or conflicts_conda):
            rmtree(possible_path, ignore_errors=True)
            if not possible_path.exists():
                engine_path = engine_path or possible_path
    return engine_path


if __name__ == "__main__":
    exit(main())
