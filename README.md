# submissions-infrastructure

Code to generate on-prem code infrastructure for the Submissions team at BCM-HGSC using mamba (a faster implementation of conda)

## Operation

### Outline

1. Clone or download the software.
2. Run commands in the scripts directory to create and update infrastructure.

## Documentation

Comprehensive documentation for all core scripts is available in the `docs/` directory. See [docs/README.md](docs/README.md) for:
- Detailed script documentation (bootstrap, deploy, promote_staging)
- Quick start guides and decision trees
- Common workflow examples

## Layout

After running these commands:

```bash
scripts/bootstrap TARGET_DIR
scripts/deploy TARGET_DIR staging
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
│   ├── Library
│   │   └── Caches
│   └── micromamba
└── infrastructure
    ├── blue
    │   ├── bin
    │   ├── conda
    │   ├── etc
    │   ├── logs
    │   └── meta
    ├── green
    ├── production -> green
    └── staging -> blue
```

This command will switch the production and staging symlinks:

```bash
# Requires that IAC_TIER_DIR be in the environment
scripts/promote_staging
```

## Commands

- `scripts/bootstrap`: create a new fresh start infrastructure.
- `scripts/deploy`: create a "tier" - a complete collection of software. Requires that bootstrap has been run on the target location.
- `scripts/bootstrap-engine`: update the "engine" - the system used to create tiers. Used by bootstrap.
- `scripts/fetch-micromamba`: download a copy of micromamba to the specified location. Used by bootstrap-engine.
- `scripts/promote_staging`: switches the symlinks between production and staging. Requires `IAC_TIER_DIR` environment variable to be set.

## Environment Variables

When users source the tier's profile script (`$IAC_TIER_DIR/etc/profile.sh`), the following environment variables are initialized:

- **IAC_TIER_DIR**: Absolute path to the active tier directory (e.g., `/path/to/target/infrastructure/blue`)
- **IAC_TIER_NAME**: Name of the tier symlink being used (e.g., `production`, `staging`)
- **IAC_DIR**: Path to the infrastructure directory (e.g., `/path/to/target/infrastructure`)
- **IAC_PARENT**: Path to the TARGET_DIR (e.g., `/path/to/target`)
- **IAC_ORIGINAL_PATH**: Original PATH before modifications by the infrastructure
- **CONDARC**: Path to the tier's conda configuration file (e.g., `$IAC_TIER_DIR/etc/condarc`)

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
