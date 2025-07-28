# submissions-infrastructure

Code to generate on-prem code infrastructure for the Submissions team at BCM-HGSC using mamba (a faster implementation of conda)

## Operation

### Outline

1. Clone or download the software.
2. Run commands in the scripts directory to create and update infrastructure.

## Layout

After running these commands:

```bash
scripts/bootstrap TARGET_DIR
scripts/iac staging TARGET_DIR
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
- `scripts/iac`: create a "tier" - a complete collection of software, Requires that bootstrap has been run on the target location.
- `scripts/bootstrap-engine`: update the "engine" - the system used to create tiers. Used by bootstrap.
- `scripts/fetch-micromamba`: download a copy of micromamba to the specified location. Used by bootstrap-engine.
- `scripts/promote_staging`: switches the symlinks between production and staging.
