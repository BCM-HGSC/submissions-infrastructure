"""Decide which target directory (IAC_PARENT) a command applies to."""

from collections.abc import Mapping
import os
from pathlib import Path
import tomllib

from .common import IacError
from .exit_codes import INVALID_INPUT, USAGE

CONFIG_KEY = "iac_parent"
ENV_VAR = "IAC_PARENT"

NO_TARGET_MESSAGE = f"""\
No target directory. Give one in any of these ways (later ones win):
  - {CONFIG_KEY} = "/path" in iac_config.toml beside the scripts directory
  - {CONFIG_KEY} = "/path" in ~/.config/iac/config.toml
  - {CONFIG_KEY} = "/path" in ./iac_config.toml
  - the {ENV_VAR} environment variable (set by a tier's profile.sh)
  - the --target option"""


def resolve_target(
    cli_value: str | None,
    *,
    environ: Mapping[str, str],
    repo_root: Path,
    home: Path,
    cwd: Path,
) -> tuple[Path, str]:
    """
    Return the target directory and a description of where it came from.

    Precedence, highest first: --target, IAC_PARENT, then the config files
    in the reverse of the order config_files() lists them.
    """
    if cli_value:
        return absolute(cli_value, cwd), "--target"
    if environ.get(ENV_VAR):
        return absolute(environ[ENV_VAR], cwd), f"${ENV_VAR}"
    for config_file in reversed(config_files(repo_root, home, cwd)):
        value = read_config_value(config_file)
        if value:
            return absolute(value, config_file.parent), str(config_file)
    raise IacError(USAGE, NO_TARGET_MESSAGE)


def config_files(repo_root: Path, home: Path, cwd: Path) -> list[Path]:
    """Config files from lowest to highest precedence."""
    return [
        repo_root / "iac_config.toml",
        home / ".config/iac/config.toml",
        cwd / "iac_config.toml",
    ]


def read_config_value(config_file: Path) -> str | None:
    if not config_file.is_file():
        return None
    try:
        with config_file.open("rb") as fin:
            data = tomllib.load(fin)
    except (OSError, tomllib.TOMLDecodeError) as e:
        raise IacError(INVALID_INPUT, f"Cannot read {config_file}: {e}") from e
    value = data.get(CONFIG_KEY)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise IacError(
            INVALID_INPUT, f"{CONFIG_KEY} in {config_file} must be a non-empty string"
        )
    return value


def absolute(value: str, relative_to: Path) -> Path:
    """Expand ~, anchor a relative path, and drop "..", keeping symlinks."""
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = relative_to / path
    return Path(os.path.normpath(path))
