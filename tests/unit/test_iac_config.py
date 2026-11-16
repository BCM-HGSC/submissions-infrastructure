"""Tests for how iac chooses the target directory."""

from pathlib import Path

import pytest

from scripts.iac_cli.common import IacError
from scripts.iac_cli.config import resolve_target
from scripts.iac_cli.exit_codes import INVALID_STATE, USAGE


@pytest.fixture
def places(tmp_path: Path) -> dict[str, Path]:
    """The three directories that can hold a config file."""
    result = {name: tmp_path / name for name in ("repo_root", "home", "cwd")}
    for path in result.values():
        path.mkdir()
    (result["home"] / ".config/iac").mkdir(parents=True)
    return result


def resolve(places, cli_value=None, environ=None) -> tuple[Path, str]:
    return resolve_target(cli_value, environ=environ or {}, **places)


def write_config(path: Path, value: str) -> None:
    path.write_text(f'iac_parent = "{value}"\n')


def write_all_configs(places) -> None:
    write_config(places["repo_root"] / "iac_config.toml", "/from/repo")
    write_config(places["home"] / ".config/iac/config.toml", "/from/home")
    write_config(places["cwd"] / "iac_config.toml", "/from/cwd")


def test_option_beats_everything(places):
    write_all_configs(places)

    target, source = resolve(places, "/from/cli", {"IAC_PARENT": "/from/env"})

    assert target == Path("/from/cli")
    assert source == "--target"


def test_environment_beats_config_files(places):
    write_all_configs(places)

    target, source = resolve(places, environ={"IAC_PARENT": "/from/env"})

    assert target == Path("/from/env")
    assert source == "$IAC_PARENT"


def test_config_file_precedence(places):
    write_all_configs(places)
    cwd_config = places["cwd"] / "iac_config.toml"
    home_config = places["home"] / ".config/iac/config.toml"

    assert resolve(places) == (Path("/from/cwd"), str(cwd_config))
    cwd_config.unlink()
    assert resolve(places) == (Path("/from/home"), str(home_config))
    home_config.unlink()
    assert resolve(places)[0] == Path("/from/repo")


def test_no_target_is_a_usage_error(places):
    with pytest.raises(IacError) as exc_info:
        resolve(places)

    assert exc_info.value.code == USAGE
    assert "--target" in str(exc_info.value)
    assert "IAC_PARENT" in str(exc_info.value)


def test_empty_environment_variable_is_ignored(places):
    with pytest.raises(IacError):
        resolve(places, environ={"IAC_PARENT": ""})


def test_relative_option_is_anchored_to_cwd(places):
    target, _source = resolve(places, "sub/../deployment")

    assert target == places["cwd"] / "deployment"


def test_relative_config_value_is_anchored_to_its_file(places):
    write_config(places["repo_root"] / "iac_config.toml", "../deployment")

    target, _source = resolve(places)

    assert target == places["repo_root"].parent / "deployment"


def test_config_without_the_key_is_skipped(places):
    (places["cwd"] / "iac_config.toml").write_text('other = "value"\n')
    write_config(places["repo_root"] / "iac_config.toml", "/from/repo")

    assert resolve(places)[0] == Path("/from/repo")


@pytest.mark.parametrize("content", ["iac_parent = [", "iac_parent = 3\n"])
def test_bad_config_is_invalid_input(places, content):
    (places["cwd"] / "iac_config.toml").write_text(content)

    with pytest.raises(IacError) as exc_info:
        resolve(places)

    assert exc_info.value.code == INVALID_STATE
