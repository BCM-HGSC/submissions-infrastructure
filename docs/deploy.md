# deploy

## Overview

The `scripts/deploy` executable is a bash wrapper that invokes the Python deployment engine to create or update infrastructure tiers.

## Purpose

This script is used to deploy or update infrastructure tiers (blue, green, staging, production) by invoking the engine's Python code to process environment definitions and create conda environments.

Most often the user runs `scripts/deploy /path/to/target_dir staging`.

## Arguments and Options

**Positional Arguments:**
- `TARGET_DIR` (required): Path to the target directory containing engine_home
- `TIER` (required): Name of the tier to deploy (e.g., blue, green, staging, production)

**Options:**
- `--offline`: Run in offline mode (no network access)
- `-n, --dry-run`: Show what would be done without making changes
- `--keep`: Keep existing conda environments (don't remove/recreate)
- `--force`: Overwrite existing conda environments
- `-h, --help`: Show help message

## Operation Flow

1. **Argument Parsing**:
   - Extracts TARGET_DIR from command line
   - Collects remaining arguments to pass to Python engine

2. **Path Setup**:
   - Determines script directory (project root)
   - Changes to TARGET_DIR

3. **Engine Invocation**:
   - Runs `scripts/sanitize-command` with PYTHONPATH set to scripts directory
   - Executes: `$TARGET_DIR/engine_home/engine/bin/python3 -m engine TARGET_DIR TIER [OPTIONS]`

## Python Engine Behavior

The Python engine (`scripts/engine/__main__.py`) performs the actual deployment:

1. **Configuration**: Sets up logging and parses arguments

2. **Environment Discovery**:
   - Scans `resources/defs/` for YAML environment definitions
   - Validates YAML syntax and structure
   - Filters by platform (universal, linux, mac)

3. **Tier Validation**:
   - Validates tier name and path
   - Determines tier directory (`$TARGET_DIR/infrastructure/$TIER`)

4. **Deployment**:
   - For each environment definition:
     - Creates conda environment using mamba
     - Installs packages from YAML specifications
     - Handles blue/green rotation if applicable
   - Uses shared package cache at `$TARGET_DIR/conda_package_cache`

5. **Profile Generation**:
   - Creates `$TIER/etc/profile.sh` with environment initialization
   - Sets IAC_* environment variables for tier management

## Tier Management

**Tier Symlinks:**
- `production`: Points to active production tier (blue or green)
- `staging`: Points to staging tier for testing

**Workflow:**
1. Deploy to staging: `scripts/deploy /path/to/target staging`
2. Test changes in staging environment
3. Promote staging to production: `scripts/promote_staging`

## Error Handling

The script propagates errors from the Python engine. Common failures:
- Missing or invalid environment definitions (YAML errors)
- Network errors in online mode
- Disk space issues
- Invalid tier names or paths

## Integration

**Prerequisites:**
- Engine must be bootstrapped first using `scripts/bootstrap-engine`
- TARGET_DIR must contain `engine_home/engine/` with Python environment

**Related Scripts:**
- `scripts/bootstrap-engine`: Creates the engine
- `scripts/promote_staging`: Swaps production/staging symlinks
- `scripts/sanitize-command`: Provides clean environment for execution

## Environment Variables Set

When users source a tier's profile (`$IAC_TIER_DIR/etc/profile.sh`):
- `IAC_TIER_DIR`: Absolute path to the tier directory
- `IAC_TIER_NAME`: Name of the tier symlink (production/staging)
- `IAC_DIR`: Path to infrastructure directory
- `IAC_PARENT`: Path to TARGET_DIR
- `IAC_ORIGINAL_PATH`: Original PATH before modifications
- `CONDARC`: Path to tier's conda configuration
