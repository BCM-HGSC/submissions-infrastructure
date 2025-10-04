"""Unit tests for engine CLI argument parsing."""

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


def test_parse_force_flag(tmp_path, monkeypatch):
    """Test parsing --force flag."""
    test_args = ["engine", str(tmp_path), "staging", "--force"]
    monkeypatch.setattr(sys, "argv", test_args)

    args = parse_command_line()

    assert args.mode == "force"


def test_keep_and_force_mutually_exclusive(tmp_path, monkeypatch):
    """Test that --keep and --force are mutually exclusive (last one wins)."""
    # In argparse, when using store_const with same dest, last flag wins
    test_args = ["engine", str(tmp_path), "staging", "--keep", "--force"]
    monkeypatch.setattr(sys, "argv", test_args)

    args = parse_command_line()

    assert args.mode == "force"  # Last flag should win

    # Test opposite order
    test_args = ["engine", str(tmp_path), "staging", "--force", "--keep"]
    monkeypatch.setattr(sys, "argv", test_args)

    args = parse_command_line()

    assert args.mode == "keep"  # Last flag should win


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

    with pytest.raises(NotADirectoryError):
        dir_path(str(nonexistent))


def test_dir_path_validator_file_not_directory(tmp_path):
    """Test dir_path validator rejects files."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")

    with pytest.raises(NotADirectoryError):
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
