from os import environ
from pathlib import Path
from shutil import rmtree
from subprocess import run
from sys import argv, executable, exit


def main(run_function=run):
    print()
    conda_opts = argv[1:]
    print(f"{conda_opts=}")
    home = Path().resolve()
    env = dict(
        HOME=home,
        CONDARC=env_path("CONDARC"),
    )
    executable_path = Path(executable)
    conda = env_path("CONDA")
    run_function("/usr/bin/env", env=env)
    run_function([conda, "info"], env=env)
    engine_path = rotate_engine_directories(home, executable_path, conda)
    symlink = home / "engine"
    conda_command = [conda, "create"] + conda_opts
    conda_command +=  f"-y -p {engine_path} conda pip".split()
    run_function(conda_command, check=True)
    if symlink.is_symlink():
        symlink.unlink()
    symlink.symlink_to(engine_path)


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
