# Repair and CLI Plan

Written 2026-11-16 from a read of all scripts, the engine, and the 16 open
issues. It replaces the test-infrastructure plan, which is in git history;
its unfinished items are carried into sections 6 and 8.

Each numbered section is one unit of work: tests and `ruff check` pass, then
commit. Findings marked **(ran)** were reproduced; **(read)** come from
reading the code and need a failing test first.

## Decisions

Decided 2026-11-16: the recommendation was accepted for all four. Later the
same day D3 was reversed: the installed base is three or four stale
deployments and at most two other users, so the old entry points were
removed outright, and nothing has to stay compatible with the old CLI.

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

Verified 2026-11-16 on a scratch target on macOS arm64: `iac bootstrap`
built the engine and created the links; a second bootstrap changed nothing;
`iac engine` rotated to `engine_b`; `iac deploy --dry-run` logged a
`mamba_binary` inside `engine_home/engine/`; and a full `iac deploy`
installed every environment. See "Verification" at the end.

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
- [x] D3 reversed: `bootstrap`, `bootstrap-engine`, `deploy`, and
  `promote_staging` are deleted. `iac` is the only entry point.

## 4. Promotion (issue #24)

Done 2026-11-16. Promotion is `promote()` in `scripts/iac_cli/tiers.py`,
standard library only, covered by `tests/unit/test_iac_cli.py`.

- [x] `promote_staging --help` crashed for lack of PyYAML. The script is
  gone; `iac promote` needs no engine.
- [x] The target comes from `iac`, not `IAC_TIER_DIR`.
- [x] Each link is swapped atomically, production first. An interruption
  leaves both links on one color, which `iac bootstrap` repairs.
- [x] A tier that was never deployed is refused. "Deployed" means
  `meta/commit` and `etc/profile.sh` exist; the engine now removes `meta/`
  before it changes a tier, so a failed `--keep` deploy no longer leaves a
  stale marker.
- [x] A dangling `production` link is replaced; a link to anything but
  `blue` or `green` is refused with a message, not a traceback.
- [x] The `infrastructure_path=` debug print went with the script.
- [x] Rollback is documented in `docs/promote.md`.

## 5. Bootstrap and engine

Done 2026-11-16.

- [x] `bootstrap` rotated the engine before checking that `infrastructure`
  existed. Gone with the port: `iac bootstrap` never rotates an existing
  engine.
- [x] Relative `TARGET_DIR` handling. Gone with the port: the target is
  made absolute when it is resolved.
- [x] `fetch-micromamba` matched `Linux arm64` but Linux reports `aarch64`,
  and it was `#!/bin/sh` using `pipefail`. The script is replaced by
  `scripts/iac_cli/micromamba.py`, which accepts both spellings.
- [x] micromamba is pinned (2.10.0-0) and each download is checked against a
  recorded SHA-256. A micromamba from another release is replaced.
- [x] Engine symlink update is atomic (temporary link, then rename).
- [x] `sanitize-command`: `iac` builds the sanitized environment itself
  (`sanitized_env()` in `common.py`), so `scripts/sanitize-command` is
  gone. The copy users get, `resources/bin/sanitize-command`, now quotes
  its expansions. Proxy variables pass through the sanitized environment.
- [x] git is in the engine and writes `meta/` (issue #41), with
  `safe.directory` set for a checkout owned by someone else. When git
  cannot tell, `meta/` says `unknown` rather than `ERROR`.
- [x] `usage()` in `bootstrap`: gone with the port.
- [x] Unused validators removed from the engine: the binary checks and the
  symlink validator, which only `promote_staging` used.

## 6. Tests

- [x] Subprocess tests for the real CLI: `tests/unit/test_iac_scripts.py`
  (help, no target, dry run) and `tests/integration/test_iac_real.py`
  (a real engine: layout, dry-run deploy, mamba discovery, rotation).
- [x] The integration and E2E suites drive `scripts/iac` only. They were
  rewritten, not ported: `tests/integration/test_iac_real.py` and one
  workflow in `tests/e2e/test_real_workflow.py`.
- [x] A failed bootstrap fails the integration tests instead of skipping.
- [x] The E2E git identity leak. Cause: a git hook exports `GIT_DIR`, so
  the fixture's `git init` and `git config user.name` acted on this
  repository whenever the suite ran under a hook. The fixture is deleted
  (it served no purpose: the engine reads this checkout, not the target),
  and `run_iac()` in `tests/conftest.py` strips every `GIT_*` variable.
  Two commits on `main` keep the wrong author.
- [x] Unit tests for the `env_yamls` parameter (issue #49) already exist in
  `tests/unit/test_deploy_tier.py`; the issue can be closed.
- [x] The two permanently skipped tests are removed.
- [x] GitHub Actions: ruff and unit tests on every push, Linux and macOS
  (`.github/workflows/ci.yml`).
- [x] `tests/unit/test_profile.py` sources `profile.sh` in a bare bash and
  a bare `zsh -f`.
- [ ] Run `--run-integration` on Linux and `--run-e2e` anywhere. The real
  cluster refreshes covered the same paths by hand.
- [ ] Offline-mode E2E: needs a populated package cache to be meaningful.

## 7. Tier contents

- [x] ranger removed: `ranger.sh` and the `ranger-fm` dependency (issue
  #51).
- [x] `compdef: command not found` (issue #27). `profile.sh` runs
  `compinit -i` when compdef is missing; verified under `zsh -f` by
  `test_profile.py`. The per-file guards turned out not to be needed.
- [x] `PIP_CACHE_DIR` defaults to `$IAC_PARENT/users/$USER/pip_cache`
  (issue #26). Per user, because pip disables a cache directory it does
  not own.
- [x] Homebrew hidden on macOS (issue #39). Decided 2026-11-16: `profile.sh`
  appends the entries of `IAC_ORIGINAL_PATH` after the tier's directories.
  Not yet deployed anywhere.
- [x] `mac/bioconda.yaml` was never deployed; deleted, with the `bioconda`
  entry in `profile.sh`. CLAUDE.md no longer describes an `experimental/`
  directory.
- [ ] `va()` in `functions.sh` is marked "TODO fix" with no statement of
  what is wrong.

## 8. Docs

- [x] README, `docs/`, and CLAUDE.md rewritten around `iac`; new
  `docs/iac.md` includes the exit codes.
- [x] `docs/promote_staging.md` rewritten as `docs/promote.md`.
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

## Verification

Real runs on a scratch target, macOS arm64, 2026-11-16:

- `iac bootstrap`: engine built, `engine -> engine_a`, `staging -> blue`,
  `production -> green`. The micromamba the old fetch script downloaded has
  the SHA-256 now pinned for `osx-arm64`.
- `iac bootstrap` again: "Engine already installed", nothing changed.
- `iac engine`: built `engine_b` with git in it and switched the link.
- `iac deploy --dry-run`: `mamba_binary` is
  `engine_home/engine/bin/mamba`; nothing created.

- `pytest tests/integration --run-integration`: 8 passed.

Deployments refreshed 2026-11-16 from 19c9487 on branch `iac-cli`, each by
`iac engine`, `iac deploy`, a check that `staging/etc/profile.sh` sources
cleanly in a bare bash and a bare `zsh -f`, then `iac promote`:

- the Mac target `~/team_infrastructure`
- the analysis cluster (`analysis2`, RHEL 8.8, x86_64)
- the clinical cluster (`clinical1`), last deployed in 2023

On the clusters `iac` was started with a Python from the deployment itself,
because uv is not on `PATH` for `ssh host command`. The previous production
tier is staging on each, so `iac promote` rolls back until the next deploy.

Not yet run anywhere: the E2E suite, and the integration suite on Linux.
