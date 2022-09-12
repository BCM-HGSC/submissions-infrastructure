from os import environ
from pathlib import Path
from shutil import rmtree
from subprocess import run
from sys import argv, executable, exit


def main():
    print()
    executable_path = Path(executable)
    conda_opts = argv[1:]
    print(f"{conda_opts=}")
    # for k in sorted(environ):
    #     if "conda" in k.lower():
    #         print(k, "=", environ[k])
    home = Path().resolve()
    env = dict(
        HOME=home,
        CONDARC=env_path("CONDARC"),
    )
    conda = env_path("CONDA")
    print(home)
    print()
    run("/usr/bin/env", env=env)
    print()
    result = run([conda, "info"], env=env)
    engine_path = rotate_engine_directories(home, executable_path, conda)
    print(engine_path)
    return


    symlink = home / "engine"
    engine_path = home / "engine_a"
    print(symlink.exists())
    conda_command = [conda, "create"] + conda_opts
    conda_command +=  f"-y -p {engine_path} conda pip".split()
    result = run(conda_command)
    if result.returncode:
        return result.returncode
    if symlink.is_symlink():
        symlink.unlink()
    symlink.symlink_to("engine_a")


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
