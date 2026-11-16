# Repair and CLI Plan

Written 2026-11-16 from a read of all scripts, the engine, and the 16 open
issues. It replaces the test-infrastructure plan, which is in git history;
its unfinished items are carried into sections 6 and 8.

Each numbered section is one unit of work: tests and `ruff check` pass, then
commit. Findings marked **(ran)** were reproduced; **(read)** come from
reading the code and need a failing test first.

## Decisions needed

These change the shape of sections 2 to 4. Recommendations are listed first.

- [ ] **D1. Language of the top-level `iac` command.** Recommended: a
  stdlib-only `uv run --script` Python file, which makes uv a prerequisite
  for operators. Alternative: bash, which keeps the "bash, posix and curl"
  promise but makes the TOML config lookup of issue #19 awkward.
- [ ] **D2. What `bootstrap --force` does.** Today it removes all of
  `infrastructure/`, production included. Recommended: make bootstrap
  idempotent (create what is missing, never delete) and drop the flag.
  Alternative: keep the wipe under an explicit name such as `--wipe`.
- [ ] **D3. Fate of the old entry points.** Recommended: keep
  `scripts/bootstrap`, `bootstrap-engine`, `deploy`, `promote_staging` as
  thin shims that call `iac` for one release, then remove. Alternative:
  remove them in the same change.
- [ ] **D4. Should `deploy` stop at the first failed environment?**
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

- [ ] `--dry-run` removes the tier before the dry-run check
  (`scripts/engine/deploy.py:80-86`) and then writes log files **(read)**.
  Dry run must touch nothing.
- [ ] A failed `mamba env create` is logged and ignored; `deploy` exits 0
  **(read)**. Apply D4.
- [ ] mamba is located with `shutil.which` at import, but `scripts/deploy`
  runs the engine with `PATH=/usr/bin:/bin` **(read)**. All E2E tests pass
  `mamba_path` explicitly, so the real path is untested. Resolve mamba
  relative to the engine (`sys.executable`), keep `mamba_path` injection.
- [ ] `setup_tier_path(target, "production")` creates a real `production`
  directory when the symlink is missing **(read)**. Only resolve it.
- [ ] Deploying to `staging` deletes `staging/logs` with the tier. Move logs
  outside the tier (for example `TARGET/logs/`).
- [ ] `--keep` and `--force` are documented as exclusive but the last one
  wins **(read)**. Make them an argparse exclusive group.
- [ ] `dir_path` raises `NotADirectoryError` and produces a traceback; raise
  `ArgumentTypeError`.
- [ ] `main()` logs the whole environment at INFO. Drop it to DEBUG.
- [ ] `parse_command_line()` ignores the `cli_args` it is given; the
  docstring still shows the old `TIER TARGET_DIR` order.
- [ ] `write_meta` writes through `Path` directly, bypassing the filesystem
  abstraction; the `expect_fail` argument is always true.
- [ ] Remove the deprecated `run_function` parameter.

## 3. One CLI: `scripts/iac` (issues #19, #24)

Target form, from #19:

```
iac [--target IAC_PARENT] [-v] [-n] SUBCOMMAND [options]
```

- [ ] Subcommands: `bootstrap`, `engine` (rotate), `deploy [--tier staging]`,
  `promote`, `status`.
- [ ] Target resolution, last wins: `REPO/iac_config.toml`,
  `~/.config/iac/config.toml`, `$PWD/iac_config.toml`, `IAC_PARENT`,
  `--target`. Error clearly when none is set.
- [ ] `--tier` defaults to `staging`.
- [ ] `--help` works for every subcommand with no target and no engine.
  Today `scripts/deploy --help` and bare `scripts/deploy` fail with
  `env: engine_home/engine/bin/python3: No such file or directory`
  **(ran)**.
- [ ] One meaning per flag across subcommands. `--force` currently means
  "wipe infrastructure" (bootstrap), "skip the disk check"
  (bootstrap-engine), and "overwrite environments and skip the disk check"
  (deploy). Split into `--overwrite` and `--skip-disk-check`; apply D2.
- [ ] `-v/--verbose` works everywhere. Today `deploy` has no verbose switch:
  the engine reads `VERBOSE` from an environment the wrapper has cleared.
- [ ] `-n/--dry-run` is global and is passed through; `bootstrap --dry-run`
  currently only prints that it would call `bootstrap-engine --dry-run`.
- [ ] Remove `--no-color` from the bootstrap usage text, or implement it; it
  is documented and rejected **(ran)**.
- [ ] One exit-code table, defined once and used by every subcommand. The
  two bash usage texts currently disagree about code 1.
- [ ] `iac status`: show target, engine link, tier links, and each tier's
  `meta/` commit. Read-only.
- [ ] Apply D3 to the old scripts.

## 4. Promotion (issue #24)

- [ ] `promote_staging --help` crashes with
  `ModuleNotFoundError: No module named 'yaml'` **(ran)**: it runs under
  the caller's `python3` and imports the engine validators. Promotion needs
  only the standard library; split the symlink validators from the YAML
  ones.
- [ ] Take the target from `iac` (section 3) instead of requiring
  `IAC_TIER_DIR`. This is the fix proposed in the #24 comment.
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

- [ ] `bootstrap` rotates the engine before it checks that `infrastructure`
  exists, so a refused bootstrap still rotates the engine **(read)**.
  Validate first.
- [ ] With a relative `TARGET_DIR`, `bootstrap` does `cd "$TARGET_DIR"` and
  then tests `$TARGET_DIR/infrastructure` relative to the new directory
  **(read)**. Make the target absolute at parse time.
- [ ] `fetch-micromamba` matches `Linux arm64`; Linux reports `aarch64`.
- [ ] `fetch-micromamba` is `#!/bin/sh` but uses `set -o pipefail`.
- [ ] Pin the micromamba version and verify a checksum instead of
  downloading `latest`.
- [ ] Engine symlink update is remove-then-create; make it atomic.
- [ ] `sanitize-command` expands `$LOGNAME`, `$USER`, `$SHELL` unquoted and
  exists in two identical copies (`scripts/`, `resources/bin/`). Keep one.
- [ ] Put git in the engine and use it for `meta/` (issue #41).
- [ ] `usage()` in `bootstrap` calls `exit` itself and has a typo
  ("populated it with  a").

## 6. Tests

- [ ] Add a failing test for each **(read)** item above before fixing it.
- [ ] Subprocess tests for the real CLI with a fake `mamba` on a fixture
  target: help, dry run, failure exit status, mamba discovery. This is old
  item 7.1 and closes the gap that hid the section 2 bugs.
- [ ] Integration tests call `pytest.skip` when bootstrap fails
  (`tests/integration/test_bootstrap.py`), which hides real failures. Fail
  instead.
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

- [ ] Rewrite README, `docs/`, and CLAUDE.md around `iac` once section 3
  lands.
- [ ] Until then, correct what is wrong now: CLAUDE.md and
  `docs/README.md` tell users to pass `--verbose` to `deploy`; CLAUDE.md
  shows `staging --dry-run --force` as a safe preview.
- [ ] Document the exit codes and the environment-definition format once.

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
