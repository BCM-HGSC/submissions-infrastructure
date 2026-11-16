# iac

`scripts/iac` is the single command for managing a deployment.

```
iac [--target IAC_PARENT] [-v] [-n] SUBCOMMAND [options]
```

It is a `uv run` script that uses only the Python standard library, so the
one prerequisite is [uv](https://docs.astral.sh/uv/). Fetching micromamba
also uses `/usr/bin/curl`. The code is in `scripts/iac_cli/`.

## The target

Every subcommand acts on one target directory, the parent of `engine_home/`
and `infrastructure/`. It is taken from the first of these that is set:

1. `--target PATH`
2. the `IAC_PARENT` environment variable, which a tier's `profile.sh` sets
3. `iac_parent = "PATH"` in `./iac_config.toml`
4. `iac_parent = "PATH"` in `~/.config/iac/config.toml`
5. `iac_parent = "PATH"` in `iac_config.toml` at the root of this checkout

A relative path in a config file is relative to that file. `iac status`
shows which source was used. The checkout's own `iac_config.toml` is
git-ignored.

## Options for every subcommand

These work before or after the subcommand.

| Option | Meaning |
|---|---|
| `--target PATH` | The target directory. |
| `-v`, `--verbose` | Log debugging detail, including from the engine. |
| `-n`, `--dry-run` | Show what would be done. Creates, removes, and runs nothing. |
| `-h`, `--help` | Help. Needs no target and no engine. |

## Subcommands

### bootstrap

```
iac bootstrap [--offline] [--skip-disk-check]
```

Creates whatever the target is missing: `conda_package_cache/`,
`engine_home/` with micromamba and an engine, `infrastructure/blue` and
`green`, and the `staging -> blue` and `production -> green` links. It never
removes or replaces anything, so it is safe to run again. An engine that
already exists is left alone.

If `staging` and `production` point to the same color, which is what an
interrupted `iac promote` leaves, bootstrap moves `staging` to the other
one.

### engine

```
iac engine [--offline] [--skip-disk-check]
```

Builds a fresh engine from `resources/defs/special/engine.yaml` in the
inactive slot (`engine_a` or `engine_b`) and then switches the `engine` link
to it. If the build fails, the link is not touched and the active engine
keeps working. The previous engine stays on disk until the next rotation.

The engine is built by micromamba, which `iac` installs as
`engine_home/micromamba`. The release is pinned in
`scripts/iac_cli/micromamba.py` together with the SHA-256 of each
platform's binary. A download that does not match is discarded, and a
micromamba from any other release is replaced. With `--offline` nothing is
fetched and whatever micromamba is already there is used.

The build runs in a sanitized environment: `HOME` is `engine_home`, `PATH`
is `/usr/bin:/bin`, and only `LOGNAME`, `USER`, `SHELL`, `TERM`, and the
proxy variables are passed through.

### deploy

```
iac deploy [--tier TIER] [--offline] [--keep | --overwrite] [--skip-disk-check]
```

Installs the conda environments from `resources/defs/` and copies
`resources/bin` and `resources/etc` into a tier. `--tier` defaults to
`staging`; other names are `blue`, `green`, and anything starting with `dev`
or `test`. A tier that resolves to the production tier is refused.

- `staging`, `dev*`, and `test*` tiers are emptied and rebuilt.
- `--keep` keeps environments that already exist and installs the rest.
- `--overwrite` empties and rebuilds a tier addressed as `blue` or `green`.

Every environment is attempted. If any fails, the command lists the failures
and exits 4 without copying `bin/` and `etc/` or writing `meta/`. `meta/` is
removed when a deploy starts and `meta/commit` is written last, so a tier
with `meta/commit` is one where a deploy ran to completion; `iac promote`
relies on that. The mamba output for each environment is in
`TARGET/logs/<timestamp>-<tier>-<environment>.log`.

`meta/` records the commit, tree hash, and `git describe` of this checkout,
read with the engine's own git. When git cannot tell (a downloaded copy with
no `.git`), the files say `unknown` and the deploy still succeeds.

The work is done by the engine (`scripts/engine/`), which `iac` runs with
the engine's own Python in the same sanitized environment as the engine
build.

### promote

```
iac promote
```

Makes the staging tier the production tier and points staging at the other
color. Refuses a staging tier that was never deployed. Promoting again rolls
back. See [promote.md](promote.md).

### status

```
iac status
```

Prints the target and where it came from, the engine link, and for staging
and production the color each points to and the commit deployed there.
Changes nothing.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Usage error: bad arguments, or no target configured |
| 2 | Missing dependency: no engine, no micromamba, no curl |
| 3 | Invalid input or state: bad tier name, bad config file, broken links, promoting a tier that was never deployed |
| 4 | Operation failed: an install failed, or too little disk space |

## Typical use

```bash
# First time
scripts/iac bootstrap --target /path/to/target

# Each update
scripts/iac deploy --target /path/to/target
source /path/to/target/infrastructure/staging/etc/profile.sh
# ... test; IAC_PARENT is now set, so --target is no longer needed ...
iac_load production
scripts/iac promote
```
