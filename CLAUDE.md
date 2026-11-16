# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Context: Relationship to Deployed Installations

This repository manages conda-based software deployments in multiple locations: the shared team
installation at `/hgsc_software/submissions/` on each cluster, and equivalent deployments on
employee laptops. Changes to conda environments or bootstrap logic must be made here and
propagated to staging before reaching production in any deployment.

`/hgsc_software/submissions/infrastructure/` is one deployment target managed by this repository.
Other things in `/hgsc_software/submissions/` (such as `aws-object-search/`) are not directly
managed here and have their own deployment mechanisms.

## Project Overview

This repository contains infrastructure automation code for generating on-prem conda-based infrastructure for the Submissions team at BCM-HGSC. The system creates a tiered deployment structure with blue/green rotation capabilities and engine-based management.

## Key Commands

Everything goes through one command, `scripts/iac`, a stdlib-only
`uv run` script. `--target`, `--verbose` and `--dry-run` work before or
after the subcommand. Without `--target`, the target comes from
`IAC_PARENT` or `iac_parent` in a config file (see `docs/iac.md`).

```bash
scripts/iac --help
scripts/iac SUBCOMMAND --help   # needs no target and no engine

# Create whatever a deployment is missing; never removes anything
scripts/iac bootstrap --target TARGET_DIR

# Replace the engine (management tools) in the inactive slot
scripts/iac engine --target TARGET_DIR --offline

# Deploy a tier; the tier is staging unless --tier says otherwise
scripts/iac deploy --target TARGET_DIR
scripts/iac deploy --target TARGET_DIR --dry-run     # changes nothing
scripts/iac deploy --target TARGET_DIR --tier blue --overwrite

# Swap production and staging; run it again to roll back
# Example: if production -> blue and staging -> green, after promotion:
#          production -> green and staging -> blue
scripts/iac promote --target TARGET_DIR

# Show the engine, the tier links, and what is deployed
scripts/iac status --target TARGET_DIR
```

`iac` is the only entry point. There are no other scripts to run.

### AWS Tools Installation
```bash
# Install AWS CLI and tools
bash scripts/install-aws-tools.sh
```

## Documentation

Detailed documentation is in the `docs/` directory:
- **docs/iac.md**: The `iac` command: target resolution, subcommands, exit codes
- **docs/promote.md**: What promotion checks, atomicity, and rollback

## Architecture

### Directory Structure
The system creates a hierarchical structure:
- **TARGET_DIR/**: Root deployment directory
  - **conda_package_cache/**: Shared conda package cache
  - **engine_home/**: Management engine directory
    - **engine_a/**, **engine_b/**: Blue/green engine environments
    - **engine**: Symlink to active engine
    - **micromamba**: Pinned release, checksum-verified (`scripts/iac_cli/micromamba.py`)
  - **infrastructure/**: Deployment tiers
    - **blue/**, **green/**: Environment directories
    - **production**, **staging**: Symlinks to active tiers
  - **logs/**: One mamba log per deployed environment
  - **users/**: Per-user conda environments, package caches, and pip caches

### Engine System
The engine is a self-contained conda environment containing deployment tools:
- Python 3.13 or later with conda, mamba, pip, and git
- Rich for terminal output, PyYAML for configuration
- Blue/green rotation for zero-downtime engine updates
- Defined by `resources/defs/special/engine.yaml`

### Configuration Management
Environment definitions stored in `resources/defs/`:
- **special/**: The engine. Never deployed to a tier.
- **universal/**: Deployed everywhere (conda, experimental, python, unix)
- **linux/**, **mac/**: Deployed on that platform only

A tier gets every `universal/*.yaml` plus its platform's file. Each becomes
an environment named for the file.

### Deployment Process
1. Bootstrap creates basic directory structure
2. Engine environment installed via micromamba
3. Engine deploys infrastructure tiers using YAML definitions
4. Blue/green rotation allows safe updates

A tier is "deployed" when it has `meta/commit` and `etc/profile.sh`. The
engine removes `meta/` before it changes a tier and writes `meta/commit`
last; `iac promote` refuses a tier without it.

### Environment Variables

When users source `$IAC_TIER_DIR/etc/profile.sh`, the following environment variables are initialized:

- **IAC_TIER_DIR**: Absolute path to the active tier directory (e.g., `/path/to/target/infrastructure/blue`)
- **IAC_TIER_NAME**: Name of the tier symlink being used (e.g., `production`, `staging`)
- **IAC_DIR**: Path to the infrastructure directory (e.g., `/path/to/target/infrastructure`)
- **IAC_PARENT**: Path to the TARGET_DIR (e.g., `/path/to/target`)
- **IAC_ORIGINAL_PATH**: Original PATH before modifications by the infrastructure. Its entries are appended to `PATH` after the tier's, so the tier wins and nothing the caller had is hidden
- **CONDARC**: Path to the tier's conda configuration file (e.g., `$IAC_TIER_DIR/etc/condarc`)
- **PIP_CACHE_DIR**: `$IAC_PARENT/users/$USER/pip_cache`, unless the user already set it

**Usage**:
- Interactive users can view these variables with the `iac_dump_vars` shell function
- `scripts/iac` uses `IAC_PARENT` as its default target, so `--target` is unnecessary in a shell that has sourced a tier
- Users switch between tiers using `iac_load <tier_name>` (e.g., `iac_load staging`)

### Code Architecture

**Two Python packages under `scripts/`**:
- `scripts/iac_cli/`: the `iac` command. Standard library only, because it runs under uv before any engine exists. `cli.py` (parsing, dispatch), `config.py` (target resolution), `bootstrap.py` (layout, tier links, engine install and rotation), `micromamba.py` (pinned, checksum-verified fetch), `tiers.py` (deploy, promote, status), `exit_codes.py` (the one exit-code table), `common.py` (`Context`, `IacError`, `sanitized_env`, command running). Never import `rich` or `yaml` here.
- `scripts/engine/`: the deployer. Runs under the engine's own Python (which has rich and PyYAML), started by `iac deploy` with the environment from `sanitized_env()`.

Subcommand functions take a `Context`; tests inject a fake `run` callable instead of running micromamba.

**Testability Design**:
- `scripts/engine/filesystem.py`: Filesystem abstraction with Protocol, real implementation, and mock
- `scripts/engine/command_runner.py`: Command execution abstraction for mocking subprocess calls
- `scripts/engine/validators.py`: YAML environment validation, binary availability checks, disk space checks, symlink validation, and path traversal protection with helpful error messages
- Dependency injection in `deploy_tier()` and `MambaDeployer` for testing
- Pure functions separated from side effects (e.g., `validate_tier_path()`, `validate_color()`)

**Mamba Detection**:
`find_mamba()` in `scripts/engine/deploy.py` looks in this order:
1. **Engine-relative**: `bin/mamba`, then `condabin/mamba`, in the environment that `sys.executable` belongs to. This is what `iac deploy` relies on, because it runs the engine with `PATH=/usr/bin:/bin`.
2. **PATH**: `shutil.which("mamba")`, a fallback for development.

Tests inject a location with the `mamba_path` parameter of `deploy_tier()` or by patching `find_mamba`.

`find_git()` does the same for the git that writes `meta/`: the engine's own, then `PATH`.

## Development Workflow

### Testing Changes
- Use `--dry-run` flag to preview deployments
- Test with `--offline` for air-gapped environments
- Engine rotation allows testing new versions safely

### Adding Environments
1. Create YAML definition in appropriate `resources/defs/` subdirectory
2. Test deployment with `--dry-run`
3. Deploy to staging tier first
4. Promote to production after validation

### Debugging
- Use `--verbose` flag for detailed logging
- Per-environment mamba logs are in `TARGET_DIR/logs/`
- `iac deploy` exits 4 if any environment fails to install
- YAML definitions are automatically validated before deployment
- `iac status` shows the commit deployed in each tier

## Testing

### Running Tests

```bash
# Run all unit tests
pytest tests/unit/

# Run specific test file
pytest tests/unit/test_iac_cli.py -v

# Run integration tests: builds a real engine (network, a few minutes)
pytest tests/integration/ --run-integration

# Run E2E tests: deploys every environment twice (network, 20+ minutes)
pytest tests/e2e/ --run-e2e

# Run with coverage
pytest --cov=scripts/engine --cov-report=html
```

### Test Organization

**Unit Tests** (`tests/unit/`):
- Fast, no network. Subcommands run against `tmp_path` with a fake `run`
  callable in place of curl, micromamba, and the engine.
- `test_iac_scripts.py` starts the real `scripts/iac` through uv.
- `test_profile.py` sources `resources/etc/profile.sh` in a bare bash and a
  bare `zsh -f` against a stand-in tier.

**Integration Tests** (`tests/integration/`):
- Marked with `@pytest.mark.integration`; require `--run-integration`
- Bootstrap one real target through `scripts/iac`, then check the layout,
  the pinned micromamba, a dry-run deploy, and engine rotation
- A failed bootstrap fails the tests; it does not skip them

**End-to-End Tests** (`tests/e2e/`):
- Marked with `@pytest.mark.e2e`; require `--run-e2e`
- One test: bootstrap, deploy, source the tier, promote, deploy again,
  `--keep`, roll back, all through `scripts/iac`

Both real suites start `iac` through `run_iac()` in `tests/conftest.py`,
which removes `IAC_PARENT` and every `GIT_*` variable. Tests must never run
`git config` or `git init`: under a git hook `GIT_DIR` points at this
repository, which is how a test once rewrote this repo's own author.

### Test Fixtures

Key fixtures in `tests/conftest.py`:
- `tmp_target_dir`: Creates temporary deployment directory structure
- `mock_filesystem`: MockFileSystem for testing file operations
- `mock_command_runner`: MockCommandRunner for testing subprocess calls
- `run_iac()` (a function, not a fixture): the real `scripts/iac` in a clean environment
- `sample_env_yaml`: Sample environment definition for testing

### Code Quality

**Linting and Formatting**:
```bash
# Run ruff linter
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .
```

**Pre-commit Hooks**:
- Automatically run ruff check and format on commit
- Validate YAML syntax
- Check for trailing whitespace and EOF newlines
- Install hooks: `pre-commit install`
