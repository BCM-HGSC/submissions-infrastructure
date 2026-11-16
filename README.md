# submissions-infrastructure

Code to generate on-prem code infrastructure for the Submissions team at BCM-HGSC using mamba (a faster implementation of conda)

## Operation

### Outline

1. Clone or download the software. The one prerequisite is
   [uv](https://docs.astral.sh/uv/).
2. Run `scripts/iac` to create and update infrastructure.

### Bootstrap

The target is the **parent** of the `infrastructure/` directory. For
example, if the deployment lives at `/hgsc_software/submissions/infrastructure/`:

```bash
cd /hgsc_software/submissions
submissions-infrastructure-git/scripts/iac bootstrap --target .
```

This creates `./conda_package_cache`, `./engine_home`, and
`./infrastructure/` under the target. Passing `infrastructure/` itself as
the target is a common mistake — it would nest a new
`infrastructure/infrastructure/` inside the existing one.

Bootstrap only creates what is missing and never removes anything, so it is
safe to run again on an existing deployment.

## Documentation

See [docs/README.md](docs/README.md), and [docs/iac.md](docs/iac.md) for the
full command reference.

## Layout

After running these commands:

```bash
scripts/iac bootstrap --target TARGET_DIR
scripts/iac deploy --target TARGET_DIR
```

The layout would be:

```
TARGET_DIR
├── conda_package_cache
├── engine_home
│   ├── engine -> engine_a
│   ├── engine_a
│   │   ├── bin
│   │   ├── conda-meta
│   │   ├── condabin
│   │   ├── etc
│   │   ├── include
│   │   ├── lib
│   │   ├── libexec
│   │   ├── man
│   │   ├── sbin
│   │   ├── share
│   │   ├── shell
│   │   └── ssl
│   └── micromamba
└── infrastructure
    ├── blue
    │   ├── bin
    │   ├── conda
    │   ├── etc
    │   └── meta
    ├── green
    ├── production -> green
    └── staging -> blue
```

Deploying also writes one log per environment to `TARGET_DIR/logs`,
outside the tiers so the logs survive a tier being replaced.

This command will switch the production and staging symlinks:

```bash
scripts/iac promote --target TARGET_DIR
```

## Commands

`scripts/iac [--target TARGET_DIR] SUBCOMMAND`. The target can also come
from `IAC_PARENT` or a config file; see [docs/iac.md](docs/iac.md).

- `iac bootstrap`: create whatever a deployment is missing. Never removes anything.
- `iac engine`: replace the "engine" - the system used to create tiers.
- `iac deploy`: create a "tier" - a complete collection of software. Deploys to staging unless `--tier` says otherwise.
- `iac promote`: switch the symlinks between production and staging. Run it again to roll back.
- `iac status`: show the engine, the tier links, and what is deployed.

`iac` is the only entry point. Its own code is `scripts/iac_cli`; the
deployer it starts under the engine's Python is `scripts/engine`.

## Environment Variables

When users source the tier's profile script (`$IAC_TIER_DIR/etc/profile.sh`), the following environment variables are initialized:

- **IAC_TIER_DIR**: Absolute path to the active tier directory (e.g., `/path/to/target/infrastructure/blue`)
- **IAC_TIER_NAME**: Name of the tier symlink being used (e.g., `production`, `staging`)
- **IAC_DIR**: Path to the infrastructure directory (e.g., `/path/to/target/infrastructure`)
- **IAC_PARENT**: Path to the TARGET_DIR (e.g., `/path/to/target`)
- **IAC_ORIGINAL_PATH**: Original PATH before modifications by the infrastructure
- **CONDARC**: Path to the tier's conda configuration file (e.g., `$IAC_TIER_DIR/etc/condarc`)
- **PIP_CACHE_DIR**: `$IAC_PARENT/users/$USER/pip_cache`, unless already set

To view these variables in an interactive shell, use the `iac_dump_vars` function:

```bash
# After sourcing the profile script
source /path/to/target/infrastructure/production/etc/profile.sh
iac_dump_vars
```

To switch between tiers:

```bash
iac_load staging   # Switch to staging tier
iac_load production  # Switch back to production tier
```
