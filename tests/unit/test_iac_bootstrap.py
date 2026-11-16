"""Tests for `iac bootstrap` and `iac engine` with a fake micromamba."""

from collections import namedtuple
from pathlib import Path

import pytest

from scripts.iac_cli import bootstrap as bootstrap_module
from scripts.iac_cli.bootstrap import bootstrap, install_engine, next_engine_name
from scripts.iac_cli.common import Context, IacError
from scripts.iac_cli.exit_codes import (
    INVALID_INPUT,
    MISSING_DEPENDENCY,
    OPERATION_FAILED,
)

SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
DiskUsage = namedtuple("DiskUsage", "total used free")


class FakeRunner:
    """Stands in for fetch-micromamba and micromamba."""

    def __init__(self, target: Path):
        self.target = target
        self.calls: list[list[str]] = []
        self.fail_create = False
        self.fail_version = False

    def __call__(self, argv, **_kwargs) -> int:
        self.calls.append(argv)
        if argv[0].endswith("fetch-micromamba"):
            micromamba = self.target / "engine_home/micromamba"
            micromamba.write_text("#!/bin/sh\n")
            micromamba.chmod(0o755)
        elif argv[-1] == "--version":
            return 1 if self.fail_version else 0
        elif "create" in argv:
            if self.fail_create:
                return 1
            prefix = Path(argv[argv.index("--prefix") + 1])
            (prefix / "bin").mkdir(parents=True)
        return 0

    @property
    def creates(self) -> list[list[str]]:
        return [argv for argv in self.calls if "create" in argv]


@pytest.fixture
def target(tmp_path: Path) -> Path:
    return tmp_path / "deployment"  # deliberately not created


@pytest.fixture
def runner(target: Path) -> FakeRunner:
    return FakeRunner(target)


@pytest.fixture(autouse=True)
def no_fetch_requirements(monkeypatch):
    monkeypatch.setattr(bootstrap_module, "FETCH_REQUIREMENTS", ())


def make_context(target: Path, runner: FakeRunner, *, dry_run=False) -> Context:
    return Context(
        target=target,
        target_source="test",
        scripts_dir=SCRIPTS_DIR,
        dry_run=dry_run,
        run=runner,
    )


def test_bootstrap_creates_the_layout(target, runner):
    bootstrap(make_context(target, runner), offline=False, skip_disk_check=True)

    assert (target / "conda_package_cache").is_dir()
    assert (target / "infrastructure/blue").is_dir()
    assert (target / "infrastructure/green").is_dir()
    assert (target / "infrastructure/staging").readlink() == Path("blue")
    assert (target / "infrastructure/production").readlink() == Path("green")
    assert (target / "engine_home/engine").readlink() == Path("engine_a")
    assert (target / "engine_home/engine_a/bin").is_dir()


def test_bootstrap_twice_changes_nothing(target, runner):
    ctx = make_context(target, runner)
    bootstrap(ctx, offline=False, skip_disk_check=True)
    before = snapshot(target)

    bootstrap(ctx, offline=False, skip_disk_check=True)

    assert snapshot(target) == before
    assert len(runner.creates) == 1  # the engine was not rotated


def test_bootstrap_never_removes_existing_tiers(target, runner):
    infrastructure = target / "infrastructure"
    (infrastructure / "blue").mkdir(parents=True)
    (infrastructure / "green").mkdir()
    (infrastructure / "blue/marker").write_text("production data\n")
    (infrastructure / "production").symlink_to("blue")
    (infrastructure / "staging").symlink_to("green")

    bootstrap(make_context(target, runner), offline=False, skip_disk_check=True)

    assert (infrastructure / "blue/marker").read_text() == "production data\n"
    assert (infrastructure / "production").readlink() == Path("blue")
    assert (infrastructure / "staging").readlink() == Path("green")


def test_bootstrap_restores_staging_opposite_production(target, runner):
    infrastructure = target / "infrastructure"
    (infrastructure / "blue").mkdir(parents=True)
    (infrastructure / "production").symlink_to("blue")

    bootstrap(make_context(target, runner), offline=False, skip_disk_check=True)

    assert (infrastructure / "staging").readlink() == Path("green")


def test_bootstrap_dry_run_creates_nothing(target, runner):
    ctx = make_context(target, runner, dry_run=True)

    bootstrap(ctx, offline=False, skip_disk_check=True)

    assert not target.exists()
    assert runner.calls == []


def test_engine_rotates_between_slots(target, runner):
    ctx = make_context(target, runner)
    link = target / "engine_home/engine"

    install_engine(ctx, offline=False, skip_disk_check=True)
    assert link.readlink() == Path("engine_a")
    install_engine(ctx, offline=False, skip_disk_check=True)
    assert link.readlink() == Path("engine_b")
    (target / "engine_home/engine_a/stale").write_text("old\n")
    install_engine(ctx, offline=False, skip_disk_check=True)

    assert link.readlink() == Path("engine_a")
    assert not (target / "engine_home/engine_a/stale").exists()
    assert (target / "engine_home/engine_b").is_dir()  # previous engine kept


def test_engine_passes_offline(target, runner):
    install_engine(make_context(target, runner), offline=True, skip_disk_check=True)

    assert runner.creates[0][-1] == "--offline"


def test_failed_engine_install_keeps_the_active_engine(target, runner):
    ctx = make_context(target, runner)
    install_engine(ctx, offline=False, skip_disk_check=True)
    runner.fail_create = True

    with pytest.raises(IacError) as exc_info:
        install_engine(ctx, offline=False, skip_disk_check=True)

    assert exc_info.value.code == OPERATION_FAILED
    assert (target / "engine_home/engine").readlink() == Path("engine_a")


def test_engine_link_that_is_a_directory_is_refused(target, runner):
    (target / "engine_home/engine").mkdir(parents=True)

    with pytest.raises(IacError) as exc_info:
        install_engine(
            make_context(target, runner), offline=False, skip_disk_check=True
        )

    assert exc_info.value.code == INVALID_INPUT
    assert runner.creates == []


def test_micromamba_that_does_not_run_is_a_missing_dependency(target, runner):
    runner.fail_version = True

    with pytest.raises(IacError) as exc_info:
        install_engine(
            make_context(target, runner), offline=False, skip_disk_check=True
        )

    assert exc_info.value.code == MISSING_DEPENDENCY
    assert runner.creates == []


def test_low_disk_space_stops_bootstrap(target, runner, monkeypatch):
    low = DiskUsage(total=10**12, used=10**12, free=1024**3)
    monkeypatch.setattr(bootstrap_module.shutil, "disk_usage", lambda _path: low)
    ctx = make_context(target, runner)

    with pytest.raises(IacError) as exc_info:
        bootstrap(ctx, offline=False, skip_disk_check=False)

    assert exc_info.value.code == OPERATION_FAILED
    assert not target.exists()

    bootstrap(ctx, offline=False, skip_disk_check=True)
    assert (target / "engine_home/engine").is_symlink()


@pytest.mark.parametrize(
    ("current", "expected"),
    [(None, "engine_a"), ("engine_a", "engine_b"), ("engine_b", "engine_a")],
)
def test_next_engine_name(current, expected):
    assert next_engine_name(current) == expected


def snapshot(root: Path) -> dict[str, str]:
    result = {}
    for path in sorted(root.rglob("*")):
        key = str(path.relative_to(root))
        if path.is_symlink():
            result[key] = f"link:{path.readlink()}"
        elif path.is_dir():
            result[key] = "dir"
        else:
            result[key] = f"file:{path.read_text()}"
    return result
