"""Unit tests for engine CLI argument parsing."""

from argparse import ArgumentTypeError
import sys

import pytest

from scripts.engine.__main__ import dir_path, parse_command_line


def test_parse_valid_arguments(tmp_path, monkeypatch):
    """Test parsing valid command line arguments."""
    test_args = ["engine", str(tmp_path), "staging"]
    monkeypatch.setattr(sys, "argv", test_args)

    args = parse_command_line()

    assert args.target == tmp_path
    assert args.tier == "staging"
    assert args.offline is False
    assert args.dry_run is False
    assert args.mode is None


def test_parse_offline_flag(tmp_path, monkeypatch):
    """Test parsing --offline flag."""
    test_args = ["engine", str(tmp_path), "blue", "--offline"]
    monkeypatch.setattr(sys, "argv", test_args)

    args = parse_command_line()

    assert args.offline is True


def test_parse_dry_run_flag(tmp_path, monkeypatch):
    """Test parsing --dry-run flag."""
    test_args = ["engine", str(tmp_path), "green", "--dry-run"]
    monkeypatch.setattr(sys, "argv", test_args)

    args = parse_command_line()

    assert args.dry_run is True


def test_parse_dry_run_short_flag(tmp_path, monkeypatch):
    """Test parsing -n flag for dry-run."""
    test_args = ["engine", str(tmp_path), "staging", "-n"]
    monkeypatch.setattr(sys, "argv", test_args)

    args = parse_command_line()

    assert args.dry_run is True


def test_parse_keep_flag(tmp_path, monkeypatch):
    """Test parsing --keep flag."""
    test_args = ["engine", str(tmp_path), "staging", "--keep"]
    monkeypatch.setattr(sys, "argv", test_args)

    args = parse_command_line()

    assert args.mode == "keep"


def test_parse_overwrite_flag(tmp_path):
    """Test that --overwrite replaces the tier but keeps the disk check."""
    args = parse_command_line([str(tmp_path), "staging", "--overwrite"])

    assert args.mode == "force"
    assert args.skip_disk_check is False


def test_parse_skip_disk_check_flag(tmp_path):
    """Test that --skip-disk-check does not imply overwriting."""
    args = parse_command_line([str(tmp_path), "staging", "--skip-disk-check"])

    assert args.skip_disk_check is True
    assert args.mode is None


def test_force_flag_is_gone(tmp_path):
    """Test that the overloaded --force flag is rejected."""
    with pytest.raises(SystemExit) as exc_info:
        parse_command_line([str(tmp_path), "staging", "--force"])

    assert exc_info.value.code == 2


@pytest.mark.parametrize(
    "flags", [["--keep", "--overwrite"], ["--overwrite", "--keep"]]
)
def test_keep_and_overwrite_mutually_exclusive(tmp_path, flags):
    """Test that --keep and --overwrite cannot be combined."""
    with pytest.raises(SystemExit) as exc_info:
        parse_command_line([str(tmp_path), "staging", *flags])

    assert exc_info.value.code == 2


def test_parse_explicit_argv_ignores_sys_argv(tmp_path, monkeypatch):
    """Test that an explicit argument list is used instead of sys.argv."""
    monkeypatch.setattr(sys, "argv", ["engine", "/nonexistent", "production"])

    args = parse_command_line([str(tmp_path), "staging", "--offline"])

    assert args.target == tmp_path
    assert args.tier == "staging"
    assert args.offline is True


def test_parse_nonexistent_target_is_usage_error(tmp_path, capsys):
    """Test that a bad target is reported by argparse, not as a traceback."""
    with pytest.raises(SystemExit) as exc_info:
        parse_command_line([str(tmp_path / "nonexistent"), "staging"])

    assert exc_info.value.code == 2
    assert "not a directory" in capsys.readouterr().err


def test_parse_missing_target(monkeypatch):
    """Test that missing target argument causes error."""
    test_args = ["engine"]
    monkeypatch.setattr(sys, "argv", test_args)

    with pytest.raises(SystemExit):
        parse_command_line()


def test_parse_missing_tier(tmp_path, monkeypatch):
    """Test that missing tier argument causes error."""
    test_args = ["engine", str(tmp_path)]
    monkeypatch.setattr(sys, "argv", test_args)

    with pytest.raises(SystemExit):
        parse_command_line()


def test_dir_path_validator_valid_directory(tmp_path):
    """Test dir_path validator accepts valid directories."""
    result = dir_path(str(tmp_path))
    assert result == tmp_path


def test_dir_path_validator_nonexistent_path(tmp_path):
    """Test dir_path validator rejects nonexistent paths."""
    nonexistent = tmp_path / "nonexistent"

    with pytest.raises(ArgumentTypeError):
        dir_path(str(nonexistent))


def test_dir_path_validator_file_not_directory(tmp_path):
    """Test dir_path validator rejects files."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")

    with pytest.raises(ArgumentTypeError):
        dir_path(str(test_file))


def test_parse_combined_flags(tmp_path, monkeypatch):
    """Test parsing multiple flags together."""
    test_args = ["engine", str(tmp_path), "staging", "--offline", "--dry-run", "--keep"]
    monkeypatch.setattr(sys, "argv", test_args)

    args = parse_command_line()

    assert args.target == tmp_path
    assert args.tier == "staging"
    assert args.offline is True
    assert args.dry_run is True
    assert args.mode == "keep"
