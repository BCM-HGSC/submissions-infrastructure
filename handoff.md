# Handoff: repair and `iac` CLI work

Written 2026-11-16. Read `plan.md` first; it is the source of truth and its
checkboxes are current. This file adds what the plan does not say: where
things stand right now and what to do next.

## State

- Branch `claude`, local only, seven commits ahead of `main`, working tree
  clean. Nothing pushed, no PR. The newest commit adds this file; the six
  before it are:

  ```
  e975357 Add the iac command (#19)
  2f532a5 Plan: track the E2E git identity leak
  cad72c4 Fix data loss and false success in deploy
  b81676c Replace plan with repair and CLI plan
  087fdcb Fix findings from ruff 0.17.5
  4349981 Make the project runnable under uv
  ```

- Plan sections 1, 2, and 3 are done. Decisions D1 to D4 are all settled
  (recommendations accepted).
- `uv run pytest tests/unit` passes (279). `uv run ruff check .` and
  `uv run ruff format --check .` are clean.
- This repo's `.git/config` used to set the author to
  `E2E Test <e2e@test.local>`, leaked from the fixture in
  `tests/e2e/test_real_workflow.py`. That override was removed; commits now
  use the global identity. Two older commits on `main` still carry the
  wrong author. The root cause is an open item in plan section 6.

## Not verified

1. **A real `iac bootstrap` / `iac engine`.** The bash logic was ported to
   Python (`scripts/iac_cli/bootstrap.py`) and tested only with a fake
   runner. A real run was started and interrupted partway:

   ```bash
   scripts/iac bootstrap --verbose --target SOME_SCRATCH_DIR
   ```

   What the interrupted run did get through: it created
   `conda_package_cache/`, `engine_home/`, `infrastructure/blue` and
   `green`; `fetch-micromamba` downloaded micromamba; `micromamba --version`
   passed; micromamba downloaded repodata and had started
   `env create`. It was stopped before `engine_a` existed, so there is no
   `engine` link and no `staging`/`production` links. So the fetch and
   launch path works; the build, the atomic link switch, and the tier
   links are still unproven.

2. **Integration and E2E suites** (`--run-integration`, `--run-e2e`). They
   were edited to match new behaviour and they collect, but only two
   offline integration tests were run. They still drive
   `scripts/bootstrap-engine` (now a shim) and call `deploy_tier()`
   directly.

3. **`find_mamba()` against a real engine.** It looks for `bin/mamba` then
   `condabin/mamba` beside the engine's Python. Confirmed with a stand-in
   engine and a fake mamba, not a real conda environment.

## Next steps, in order

1. Finish the real verification on a fresh scratch target (uses the
   network; allow about ten minutes for the engine build):

   ```bash
   scripts/iac bootstrap --target SCRATCH
   scripts/iac status --target SCRATCH
   scripts/iac bootstrap --target SCRATCH      # must change nothing
   scripts/iac engine --target SCRATCH         # engine -> engine_b
   scripts/iac deploy --target SCRATCH --dry-run
   ```

   Check that the last command logs a `mamba_binary=` inside
   `SCRATCH/engine_home/engine/`. Record the result in plan section 3,
   under "Not verified".

2. Plan section 4, promotion. `iac promote` currently delegates to
   `scripts/promote_staging` under the engine's Python. Move the logic into
   `scripts/iac_cli`, make the swap atomic (`replace_symlink()` in
   `common.py` already does this), refuse to promote a tier with no
   `meta/commit`, handle a dangling `production` link, and turn
   `promote_staging` into a shim. Existing tests to keep in view:
   `tests/unit/test_promote_staging.py`, `tests/unit/test_blue_green.py`
   (loads `promote_staging` by path), `tests/integration/test_promote.py`.

3. Then sections 5 to 9 as the plan lists them. Section 7 (tier contents:
   ranger #51, `compdef` #27, pip cache #26, Homebrew #39) is independent
   of everything else and can go at any time.

## Things a fresh session would not guess

- **Two packages under `scripts/`.** `iac_cli/` is standard library only
  because it runs under uv before any engine exists; never import `rich`
  or `yaml` there. `engine/` runs under the engine's own Python.
- **Tests inject a fake runner.** Subcommand functions take a `Context`
  whose `run` callable replaces subprocess execution. See `FakeRunner` in
  `tests/unit/test_iac_bootstrap.py`.
- **`--force` no longer exists** in `iac` or the engine. It is
  `--overwrite` and `--skip-disk-check`. The `deploy` and
  `bootstrap-engine` shims translate it; the `bootstrap` shim refuses it.
  Inside the engine the mode value is still the string `"force"`.
- **Deploy logs moved** from `TIER/logs` to `TARGET/logs`.
- **A failed environment makes deploy exit 4** before `bin/`, `etc/`, and
  `meta/` are written, so `meta/commit` marks a fully deployed tier.
  Section 4's "was staging ever deployed" check can rely on that.
- **ruff is 0.17.5** in both `uv.lock` and `.pre-commit-config.yaml`. Keep
  the two in step.
- **Commit messages go through a file** (`git commit -F`): the body limit
  is 72 columns and the pre-commit hook stashes unstaged changes, so stage
  `.pre-commit-config.yaml` whenever it changes.
- **Commit identity.** If `git config user.name` in this repo ever reads
  `E2E Test` again, the E2E fixture has leaked again; do not commit until
  it is unset.

## Open questions for Walker

- Push `claude` as a named feature branch and open a PR now, or after
  section 4?
- When should the three shims be removed? The plan says "after one
  release" without defining it.
- Issue #39: add `/opt/homebrew/bin` to the fixed `PATH` in `profile.sh`,
  or re-append `IAC_ORIGINAL_PATH`?
