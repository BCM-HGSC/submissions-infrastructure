# Handoff

Written 2026-11-16, end of day. `plan.md` is the source of truth for what
is done and what is left; its "Next" section is the to-do list. This file
adds the state of things that the plan does not carry.

## State

- **PR #53 `iac-cli` is merged.** `scripts/iac` is the only entry point;
  the old scripts are deleted.
- **PR #54 `keep-original-path` is open**, CI green, not merged. It fixes
  issue #39. The merge message is in `local/merge.txt`.
- The working tree is on `keep-original-path`, clean and pushed. The
  `claude` branch is behind it; after the merge, switch to
  `claude` and fast-forward it to `main`.
- `uv run pytest tests/unit` passes (249). `ruff check` and
  `ruff format --check` are clean. CI runs both on Linux and macOS.

## Deployments

| Target | Production | Staging (rollback) |
|---|---|---|
| Mac, `~/team_infrastructure` | 6f36302 (PR #54, has the `PATH` fix) | 19c9487 |
| Analysis, `analysis2:/hgsc_software/submissions` | 19c9487 | ee3fd6d |
| Clinical, `clinical1:/hgsc_software/submissions` | 19c9487 | 4d7fd9d (2023) |

`scripts/iac status --target TARGET` shows this. `iac promote` swaps back
on any of them until the next deploy there.

The Mac's production tier was deployed from the PR branch before the merge.
The commit will be in `main` after a merge commit; a squash would orphan it.

## Updating a cluster

Do not start without agreeing the timing: jobs may be running. A deploy
rebuilds the staging tier, which on both clusters is the tier that was
production until 2026-11-16.

uv is not on `PATH` for `ssh host command`, so start `iac` with the
engine's Python. Both checkouts are detached at `origin/iac-cli`, a branch
that no longer exists on GitHub.

```bash
ssh analysis2      # or clinical1; needs VPN
umask 0002
cd /hgsc_software/submissions/submissions-infrastructure-git
git fetch --prune origin
git switch --detach origin/main
PY=/hgsc_software/submissions/engine_home/engine/bin/python3
$PY scripts/iac status --target /hgsc_software/submissions
$PY scripts/iac deploy --target /hgsc_software/submissions
# check: source infrastructure/staging/etc/profile.sh in a bare shell
$PY scripts/iac promote --target /hgsc_software/submissions
```

A deploy takes ten minutes or more; run it under tmux or in the background.
`iac engine` is needed only when `resources/defs/special/engine.yaml` or the
micromamba pin changes.

`production1` refused the SSH key on 2026-11-16, so the third cluster was
not looked at.

## Things a fresh session would not guess

- **Two packages under `scripts/`.** `iac_cli/` is standard library only,
  because it runs before any engine exists. `engine/` runs under the
  engine's own Python.
- **"Deployed" means `meta/commit` and `etc/profile.sh` exist.** The engine
  removes `meta/` first and writes `meta/commit` last. `iac promote`
  refuses a tier without it.
- **micromamba is pinned** in `scripts/iac_cli/micromamba.py` with one
  SHA-256 per platform. Changing the version means replacing all five.
- **Tests must never run `git init` or `git config`.** Under a git hook
  `GIT_DIR` points at this repository. Use `run_iac()` from
  `tests/conftest.py`, which strips the `GIT_*` variables.
- **Commit messages go through a file** (`git commit -F`), and
  `.pre-commit-config.yaml` must be staged or committed before any other
  commit when it has changed.
- **`PIP_CACHE_DIR`** is set by the tier and overrides a personal pip
  config file. One user had pointed pip at
  `/hgsc_software/submissions/pip_cache` that way.

## Open questions for Walker

- When can the clusters take the next deploy?
- Delete the remote branches `updates` and `fixes`? This work supersedes
  both.
- What is wrong with `va()` in `functions.sh`? It says only "TODO fix".
