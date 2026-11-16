# Repair and CLI Plan

Written 2026-11-16 from a read of all scripts, the engine, and the 16 open
issues. It replaces the test-infrastructure plan, which is in git history;
its unfinished items are carried into sections 6 and 8.

Each numbered section is one unit of work: tests and `ruff check` pass, then
commit. Findings marked **(ran)** were reproduced; **(read)** come from
reading the code and need a failing test first.

## Decisions

Decided 2026-11-16: the recommendation was accepted for all four.

- [x] **D1. Language of the top-level `iac` command.** Recommended: a
  stdlib-only `uv run --script` Python file, which makes uv a prerequisite
  for operators. Alternative: bash, which keeps the "bash, posix and curl"
  promise but makes the TOML config lookup of issue #19 awkward.
- [x] **D2. What `bootstrap --force` does.** Today it removes all of
  `infrastructure/`, production included. Recommended: make bootstrap
  idempotent (create what is missing, never delete) and drop the flag.
  Alternative: keep the wipe under an explicit name such as `--wipe`.
- [x] **D3. Fate of the old entry points.** Recommended: keep
  `scripts/bootstrap`, `bootstrap-engine`, `deploy`, `promote_staging` as
  thin shims that call `iac` for one release, then remove. Alternative:
  remove them in the same change.
- [x] **D4. Should `deploy` stop at the first failed environment?**
  Recommended: attempt all, then exit non-zero and list the failures.

## 1. Make the project runnable (prerequisite)

- [x] `uv run pytest` fails **(ran)**: `pyproject.toml` declares a hatchling
  build with nothing to package. Remove `[build-system]` and mark the
  project as not a package.
- [x] Move dev tools to a `dev` dependency group and add `rich` and `pyyaml`,
  which the unit tests import through the engine.
- [x] Commit `uv.lock`; add `.venv/` to `.gitignore`.
- [x] Reconcile `requires-python`, ruff `target-version`, and the engine's
  `python~=3.13`. (Already consistent: all three say 3.13.)
- [x] Run the full unit suite and `ruff check`; record the baseline here.
  Baseline 2026-11-16: 195 unit tests pass. The locked ruff (0.17.5) was
  newer than the pre-commit pin (0.8.4) and reported 7 findings plus
  formatting drift in 4 test files; the pin is now 0.17.5 and both are
  clean. Integration and E2E suites not run.

## 2. Data-loss and wrong-status bugs in `deploy`

Done 2026-11-16. Each fix has a test in `tests/unit/test_deploy_safety.py`
or `test_engine_cli.py`; the first six tests failed before the fix. Also
run through the real `scripts/deploy` wrapper against a stand-in engine
with a fake mamba. Integration and E2E suites were edited to match but not
run.

- [x] `--dry-run` removed the tier and wrote log files (confirmed by
  test). Dry run now creates, removes, and runs nothing.
- [x] A failed `mamba env create` was logged and ignored (confirmed by
  test). All environments are attempted; any failure exits 4 before
  `bin/`, `etc/`, and `meta/` are written. This applies the D4
  recommendation; reverse it if D4 goes the other way.
- [x] mamba was located with `shutil.which` under `PATH=/usr/bin:/bin`.
  `find_mamba()` now looks in the engine first, then `PATH`.
- [x] `setup_tier_path(target, "production")` created a real `production`
  directory when the symlink was missing (confirmed by test).
- [x] Logs moved from `TIER/logs` to `TARGET/logs`, named
  `<timestamp>-<tier>-<environment>.log`.
- [x] `--keep` and `--force` are an argparse exclusive group.
- [x] `dir_path` raises `ArgumentTypeError`.
- [x] `main()` logs the environment at DEBUG.
- [x] `parse_command_line()` uses the arguments it is given.
- [x] `write_meta` writes through the filesystem abstraction;
  `expect_fail` removed.
- [x] Removed the deprecated `run_function` parameter.

## 3. One CLI: `scripts/iac` (issues #19, #24)

Target form, from #19:

```
iac [--target IAC_PARENT] [-v] [-n] SUBCOMMAND [options]
```

Done 2026-11-16. `scripts/iac` is a stdlib-only uv script; the code is in
`scripts/iac_cli/`. The bootstrap and engine logic was ported from bash to
Python so the old scripts could become shims. Covered by
`tests/unit/test_iac_*.py`, including subprocess tests of the real entry
points, and tried by hand against a stand-in engine with a fake mamba.

**Not verified:** a real `iac bootstrap` or `iac engine`, which downloads
micromamba and builds the engine. Run one on a scratch target before
relying on it, and run the integration and E2E suites.

- [x] Subcommands: `bootstrap`, `engine` (rotate), `deploy [--tier staging]`,
  `promote`, `status`.
- [x] Target resolution, last wins: `REPO/iac_config.toml`,
  `~/.config/iac/config.toml`, `$PWD/iac_config.toml`, `IAC_PARENT`,
  `--target`. Error clearly when none is set.
- [x] `--tier` defaults to `staging`.
- [x] `--help` works for every subcommand with no target and no engine.
- [x] One meaning per flag: `--overwrite` and `--skip-disk-check` replace
  `--force`, in `iac` and in the engine. Bootstrap never deletes (D2).
- [x] `-v/--verbose` works everywhere and reaches the engine as `VERBOSE=1`.
- [x] `-n/--dry-run` works before or after the subcommand.
- [x] `--no-color` is gone with the old usage text.
- [x] One exit-code table in `scripts/iac_cli/exit_codes.py`, shown by
  `iac --help`. Usage errors exit 1, not argparse's 2. The engine still
  uses literal 2, 3, 4 with the same meanings.
- [x] `iac status`.
- [x] D3: `bootstrap`, `bootstrap-engine`, `deploy` are shims.
  `promote_staging` is not yet one; `iac promote` runs it under the
  engine's Python with `IAC_TIER_DIR` supplied. Section 4 finishes this.
- [ ] Remove the shims after one release.

## 4. Promotion (issue #24)

- [ ] `promote_staging --help` crashes with
  `ModuleNotFoundError: No module named 'yaml'` **(ran)**: it runs under
  the caller's `python3` and imports the engine validators. Promotion needs
  only the standard library; split the symlink validators from the YAML
  ones.
- [ ] Take the target from `iac` (section 3) instead of requiring
  `IAC_TIER_DIR`. This is the fix proposed in the #24 comment. Partly
  done: `iac promote` works without `IAC_TIER_DIR`, but only by delegating
  to `promote_staging`, so it needs an engine. Move the logic into
  `iac_cli` and make `promote_staging` a shim.
- [ ] Swap symlinks atomically (temp link plus rename). Today production is
  unlinked first, leaving a window, and a crash, with no production.
- [ ] Refuse to promote a tier that was never deployed (no `meta/commit` or
  `etc/profile.sh`). After a fresh bootstrap an empty staging can be
  promoted.
- [ ] A dangling `production` symlink skips validation and then fails with a
  `FileExistsError` traceback **(read)**.
- [ ] Remove the `infrastructure_path=` debug print.
- [ ] Document rollback: promoting again swaps back, valid only until the
  next deploy to staging.

## 5. Bootstrap and engine

- [x] `bootstrap` rotated the engine before checking that `infrastructure`
  existed. Gone with the port: `iac bootstrap` never rotates an existing
  engine.
- [x] Relative `TARGET_DIR` handling. Gone with the port: the target is
  made absolute when it is resolved.
- [ ] `fetch-micromamba` matches `Linux arm64`; Linux reports `aarch64`.
- [ ] `fetch-micromamba` is `#!/bin/sh` but uses `set -o pipefail`.
- [ ] Pin the micromamba version and verify a checksum instead of
  downloading `latest`.
- [x] Engine symlink update is atomic (temporary link, then rename).
- [ ] `sanitize-command` expands `$LOGNAME`, `$USER`, `$SHELL` unquoted and
  exists in two identical copies (`scripts/`, `resources/bin/`). Keep one.
- [ ] Put git in the engine and use it for `meta/` (issue #41).
- [x] `usage()` in `bootstrap`: gone with the port.

## 6. Tests

- [ ] Add a failing test for each **(read)** item above before fixing it.
- [ ] Subprocess tests for the real CLI with a fake `mamba` on a fixture
  target: help, dry run, failure exit status, mamba discovery. This is old
  item 7.1 and closes the gap that hid the section 2 bugs. Partly done:
  `tests/unit/test_iac_scripts.py` covers help, no-target, dry run, and
  the shims. Still missing: a fixture engine so `iac deploy` runs end to
  end with a fake mamba (done by hand only).
- [ ] The integration and E2E suites still drive `scripts/bootstrap-engine`
  and call `deploy_tier()` directly. Point them at `scripts/iac`.
- [ ] Integration tests call `pytest.skip` when bootstrap fails
  (`tests/integration/test_bootstrap.py`), which hides real failures. Fail
  instead.
- [ ] The git fixture in `tests/e2e/test_real_workflow.py` runs
  `git config user.name "E2E Test"` and at some point wrote it into this
  repo's own `.git/config`; two commits on main carry that author. The
  override was removed 2026-11-16. Find how the fixture reached the real
  repo and make it impossible (for example `GIT_CONFIG_GLOBAL` and
  per-command `-c` instead of `git config`).
- [ ] Unit tests for the `env_yamls` parameter (issue #49). Note the issue
  names `tests/unit/test_deploy.py`; the file is `test_deploy_tier.py`.
- [ ] Remove or implement the two permanently skipped tests (offline,
  force).
- [ ] Offline-mode E2E (old 6.3) and E2E timeouts (old AI.0).
- [ ] GitHub Actions: unit tests and ruff on every push (old AI.6).

## 7. Tier contents

- [ ] Remove ranger: delete `resources/etc/profile.d/ranger.sh` and the
  `ranger-fm` line in `resources/defs/universal/python.yaml` together
  (issue #51).
- [ ] `compdef: command not found` on `clinical-cpa1` (issue #27).
  `profile.sh` has an untested `compinit` fallback marked TODO; guard each
  `compdef` call in `bookmarks.sh`, `ca.sh`, `dynamic_cd.sh`,
  `functions.sh`, and test under a bare `zsh -f`.
- [ ] Central pip cache: set `PIP_CACHE_DIR` in `profile.sh` beside the
  conda cache (issue #26).
- [ ] Homebrew hidden on macOS (issue #39): `profile.sh` resets `PATH` to a
  fixed list without `/opt/homebrew/bin`. Decide whether to add it or
  re-append `IAC_ORIGINAL_PATH`.
- [ ] `mac/bioconda.yaml` is never deployed, though `profile.sh` adds a
  `bioconda` environment to `PATH`. `experimental.yaml` lives in
  `universal/` while CLAUDE.md describes an `experimental/` directory.
  Deploy or delete, and fix the description.
- [ ] `va()` in `functions.sh` is marked "TODO fix".

## 8. Docs

- [x] README, `docs/`, and CLAUDE.md rewritten around `iac`; new
  `docs/iac.md` includes the exit codes.
- [ ] Rewrite `docs/promote_staging.md` with section 4.
- [ ] Document the environment-definition format.

## 9. Backlog (after the above)

Small additions, each its own change:

- [ ] `gh` in the tier (#32); AWS CLI by default (#28); `ascp` (#29)
- [ ] `sd`, `lsp`, `lsd`, `dsd` bookmark scripts (#25)
- [ ] `chrome` alias on macOS (#35)
- [ ] Auto-add selected user environments to `PATH` (#34, needs a spec)
- [ ] Auto-symlink `sbatch`, `samtools`, etc. when present (#8, needs a
  spec; `msub` is likely obsolete)
- [ ] Post-deploy disk usage log (#45)
- [ ] Rollback and deploy-state tracking (old AI.3)

## Order

1 → 2 → 6 (first two items) → 3 → 4 → 5 → 7 → 8 → 9. Sections 1 and 2 do
not depend on any decision and can start now. Section 7 is independent of
everything else.
