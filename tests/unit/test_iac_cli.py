"""Tests for iac argument parsing, dispatch, and the tier subcommands."""

from pathlib import Path

import pytest

from scripts.iac_cli import cli
from scripts.iac_cli.cli import build_parser, main
from scripts.iac_cli.common import Context, IacError
from scripts.iac_cli.exit_codes import (
    INVALID_STATE,
    MISSING_DEPENDENCY,
    SUCCESS,
    USAGE,
)
from scripts.iac_cli.tiers import deploy, promote, status_lines

SUBCOMMANDS = ["bootstrap", "engine", "deploy", "promote", "status"]


class RecordingRunner:
    def __init__(self, returncode: int = 0):
        self.returncode = returncode
        self.calls: list[dict] = []

    def __call__(self, argv, *, cwd=None, env=None, **_kwargs) -> int:
        self.calls.append({"argv": argv, "cwd": cwd, "env": env})
        return self.returncode


@pytest.fixture
def target(tmp_path: Path) -> Path:
    """A bootstrapped-looking target with a stand-in engine python."""
    target = tmp_path / "deployment"
    (target / "engine_home/engine_a/bin").mkdir(parents=True)
    (target / "engine_home/engine_a/bin/python3").write_text("")
    (target / "engine_home/engine").symlink_to("engine_a")
    (target / "infrastructure/blue").mkdir(parents=True)
    (target / "infrastructure/green").mkdir()
    (target / "infrastructure/staging").symlink_to("blue")
    (target / "infrastructure/production").symlink_to("green")
    return target


def make_context(target: Path, runner=None, **kwargs) -> Context:
    return Context(
        target=target,
        target_source="test",
        scripts_dir=Path("/repo/scripts"),
        run=runner or RecordingRunner(),
        **kwargs,
    )


# Parsing


@pytest.mark.parametrize(
    "argv",
    [
        ["--target", "/t", "-v", "-n", "deploy"],
        ["deploy", "--target", "/t", "-v", "-n"],
        ["-n", "deploy", "--target", "/t", "--verbose"],
    ],
)
def test_common_options_work_before_and_after_subcommand(argv):
    args = build_parser().parse_args(argv)

    assert args.target == "/t"
    assert args.verbose is True
    assert args.dry_run is True


def test_common_options_default_off():
    args = build_parser().parse_args(["status"])

    assert args.target is None
    assert args.verbose is False
    assert args.dry_run is False


def test_deploy_defaults_to_staging():
    args = build_parser().parse_args(["deploy"])

    assert args.tier == "staging"
    assert (args.keep, args.overwrite, args.skip_disk_check) == (False, False, False)


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["no-such-subcommand"],
        ["deploy", "--keep", "--overwrite"],
        ["deploy", "--force"],
        ["bootstrap", "--force"],
    ],
)
def test_usage_errors_exit_with_usage_code(argv, capsys):
    with pytest.raises(SystemExit) as exc_info:
        build_parser().parse_args(argv)

    assert exc_info.value.code == USAGE
    assert "usage: iac" in capsys.readouterr().err


@pytest.mark.parametrize(
    "argv", [["--help"], *([name, "--help"] for name in SUBCOMMANDS)]
)
def test_help_needs_no_target(argv, capsys, no_configured_target):
    with pytest.raises(SystemExit) as exc_info:
        main(argv)

    assert exc_info.value.code == SUCCESS
    assert "usage: iac" in capsys.readouterr().out


def test_top_level_help_documents_exit_codes(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])

    assert "exit codes:" in capsys.readouterr().out


# Dispatch


@pytest.fixture
def no_configured_target(tmp_path, monkeypatch):
    """Hide every source of a default target."""
    monkeypatch.delenv("IAC_PARENT", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "SCRIPTS_DIR", tmp_path / "repo/scripts")


def test_main_without_a_target_is_a_usage_error(no_configured_target, caplog):
    assert main(["status"]) == USAGE
    assert "No target directory" in caplog.text


def test_main_uses_environment_target(
    no_configured_target, monkeypatch, target, capsys
):
    monkeypatch.setenv("IAC_PARENT", str(target))

    assert main(["status"]) == SUCCESS
    assert f"target:      {target}  (from $IAC_PARENT)" in capsys.readouterr().out


def test_main_deploy_without_engine_is_missing_dependency(tmp_path, caplog):
    assert main(["deploy", "--target", str(tmp_path)]) == MISSING_DEPENDENCY
    assert "iac bootstrap" in caplog.text


# deploy


def test_deploy_runs_the_engine_sanitized(target, monkeypatch):
    monkeypatch.setenv("CONDA_PREFIX", "/somewhere/conda")
    monkeypatch.setenv("https_proxy", "http://proxy.example:3128")
    runner = RecordingRunner()
    ctx = make_context(target, runner)

    result = deploy(
        ctx,
        tier="staging",
        offline=False,
        keep=False,
        overwrite=False,
        skip_disk_check=False,
    )

    assert result == 0
    call = runner.calls[0]
    assert call["cwd"] == target
    assert call["argv"] == [
        str(target / "engine_home/engine/bin/python3"),
        "-m",
        "engine",
        str(target),
        "staging",
    ]
    assert call["env"]["PYTHONPATH"] == "/repo/scripts"
    assert call["env"]["HOME"] == str(target / "engine_home")
    assert call["env"]["PATH"] == "/usr/bin:/bin"
    assert call["env"]["https_proxy"] == "http://proxy.example:3128"
    assert "CONDA_PREFIX" not in call["env"]
    assert "VERBOSE" not in call["env"]


def test_deploy_passes_every_option(target):
    runner = RecordingRunner()
    ctx = make_context(target, runner, dry_run=True, verbose=True)

    deploy(
        ctx,
        tier="green",
        offline=True,
        keep=False,
        overwrite=True,
        skip_disk_check=True,
    )

    assert runner.calls[0]["env"]["VERBOSE"] == "1"
    assert runner.calls[0]["argv"][-5:] == [
        "green",
        "--dry-run",
        "--offline",
        "--overwrite",
        "--skip-disk-check",
    ]


def test_deploy_returns_the_engine_exit_status(target):
    ctx = make_context(target, RecordingRunner(returncode=4))

    result = deploy(
        ctx,
        tier="staging",
        offline=False,
        keep=True,
        overwrite=False,
        skip_disk_check=False,
    )

    assert result == 4


def test_deploy_without_engine_raises(tmp_path):
    with pytest.raises(IacError) as exc_info:
        deploy(
            make_context(tmp_path),
            tier="staging",
            offline=False,
            keep=False,
            overwrite=False,
            skip_disk_check=False,
        )

    assert exc_info.value.code == MISSING_DEPENDENCY


# promote


@pytest.fixture
def deployed_staging(target: Path) -> Path:
    """Make the staging tier (blue) look deployed."""
    blue = target / "infrastructure/blue"
    (blue / "meta").mkdir()
    (blue / "meta/commit").write_text("0123456789abcdef0123456789abcdef01234567\n")
    (blue / "etc").mkdir()
    (blue / "etc/profile.sh").write_text("")
    return target


def links(target: Path) -> dict[str, str]:
    infrastructure = target / "infrastructure"
    return {
        path.name: str(path.readlink())
        for path in sorted(infrastructure.iterdir())
        if path.is_symlink()
    }


def test_promote_swaps_the_links(deployed_staging):
    runner = RecordingRunner()

    assert promote(make_context(deployed_staging, runner)) == SUCCESS

    assert links(deployed_staging) == {"production": "blue", "staging": "green"}
    assert runner.calls == []  # needs no engine and runs nothing


def test_promote_twice_rolls_back(deployed_staging):
    green = deployed_staging / "infrastructure/green"
    (green / "meta").mkdir()
    (green / "meta/commit").write_text("fedcba9876543210fedcba9876543210fedcba98\n")
    (green / "etc").mkdir()
    (green / "etc/profile.sh").write_text("")
    ctx = make_context(deployed_staging)

    promote(ctx)
    promote(ctx)

    assert links(deployed_staging) == {"production": "green", "staging": "blue"}


def test_promote_works_without_an_engine(deployed_staging):
    (deployed_staging / "engine_home/engine").unlink()

    assert promote(make_context(deployed_staging)) == SUCCESS


def test_promote_dry_run_changes_nothing(deployed_staging):
    promote(make_context(deployed_staging, dry_run=True))

    assert links(deployed_staging) == {"production": "green", "staging": "blue"}


def test_promote_creates_a_missing_production_link(deployed_staging):
    (deployed_staging / "infrastructure/production").unlink()

    promote(make_context(deployed_staging))

    assert links(deployed_staging) == {"production": "blue", "staging": "green"}


def test_promote_replaces_a_dangling_production_link(deployed_staging):
    (deployed_staging / "infrastructure/green").rmdir()

    promote(make_context(deployed_staging))

    assert links(deployed_staging) == {"production": "blue", "staging": "green"}


def test_promote_refuses_a_tier_that_was_never_deployed(target):
    with pytest.raises(IacError) as exc_info:
        promote(make_context(target))

    assert exc_info.value.code == INVALID_STATE
    assert "has not been deployed" in str(exc_info.value)
    assert links(target) == {"production": "green", "staging": "blue"}


def test_promote_refuses_a_tier_whose_deploy_did_not_finish(deployed_staging):
    """The engine removes meta/ first and writes meta/commit last."""
    (deployed_staging / "infrastructure/blue/meta/commit").unlink()

    with pytest.raises(IacError) as exc_info:
        promote(make_context(deployed_staging))

    assert exc_info.value.code == INVALID_STATE


def test_promote_refuses_links_on_the_same_color(deployed_staging):
    production = deployed_staging / "infrastructure/production"
    production.unlink()
    production.symlink_to("blue")

    with pytest.raises(IacError) as exc_info:
        promote(make_context(deployed_staging))

    assert exc_info.value.code == INVALID_STATE
    assert "iac bootstrap" in str(exc_info.value)


@pytest.mark.parametrize("name", ["staging", "production"])
def test_promote_refuses_a_link_to_another_name(deployed_staging, name):
    link = deployed_staging / "infrastructure" / name
    link.unlink()
    link.symlink_to("purple")

    with pytest.raises(IacError) as exc_info:
        promote(make_context(deployed_staging))

    assert exc_info.value.code == INVALID_STATE
    assert "expected blue or green" in str(exc_info.value)


@pytest.mark.parametrize("name", ["staging", "production"])
def test_promote_refuses_a_link_that_is_a_directory(deployed_staging, name):
    link = deployed_staging / "infrastructure" / name
    link.unlink()
    link.mkdir()

    with pytest.raises(IacError) as exc_info:
        promote(make_context(deployed_staging))

    assert exc_info.value.code == INVALID_STATE
    assert "Not a symlink" in str(exc_info.value)


def test_promote_refuses_a_missing_staging_link(deployed_staging):
    (deployed_staging / "infrastructure/staging").unlink()

    with pytest.raises(IacError) as exc_info:
        promote(make_context(deployed_staging))

    assert exc_info.value.code == INVALID_STATE


# status


def test_status_of_an_empty_directory(tmp_path):
    lines = status_lines(make_context(tmp_path))

    assert lines == [
        f"target:      {tmp_path}  (from test)",
        "engine:      missing",
        "micromamba:  missing",
        "staging:     missing",
        "production:  missing",
    ]


def test_status_reports_what_is_deployed(target):
    green = target / "infrastructure/green"
    (green / "meta").mkdir()
    (green / "meta/commit").write_text("0123456789abcdef0123456789abcdef01234567\n")
    (green / "meta/description").write_text("v1.2-3-g0123456\n")
    (green / "etc").mkdir()
    (green / "etc/profile.sh").write_text("")
    (target / "engine_home/micromamba").write_text("")

    lines = status_lines(make_context(target))

    assert lines[1:] == [
        "engine:      -> engine_a",
        "micromamba:  present",
        "staging:     -> blue, not deployed",
        "production:  -> green, commit 0123456789ab (v1.2-3-g0123456)",
    ]


def test_status_flags_broken_links(target):
    (target / "infrastructure/staging").unlink()
    (target / "infrastructure/staging").mkdir()
    (target / "infrastructure/production").unlink()
    (target / "infrastructure/production").symlink_to("purple")

    lines = status_lines(make_context(target))

    assert lines[3:] == [
        "staging:     not a symlink",
        "production:  -> purple (dangling)",
    ]


def test_status_shows_unknown_when_git_could_not_tell(deployed_staging):
    meta = deployed_staging / "infrastructure/blue/meta"
    (meta / "commit").write_text("unknown\n")

    line = status_lines(make_context(deployed_staging))[3]

    assert line == "staging:     -> blue, commit unknown (unknown)"
