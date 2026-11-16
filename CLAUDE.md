# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains infrastructure automation code for generating on-prem conda-based infrastructure for the Submissions team at BCM-HGSC.The system creates a tiered deployment structure with blue/green rotation capabilities and engine-based management.

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

# Swap production and staging
# Example: if production -> blue and staging -> green, after promotion:
#          production -> green and staging -> blue
scripts/iac promote --target TARGET_DIR

# Show the engine, the tier links, and what is deployed
scripts/iac status --target TARGET_DIR
```

`scripts/bootstrap`, `scripts/bootstrap-engine`, and `scripts/deploy` are
deprecated shims that translate their arguments and call `iac`.

### AWS Tools Installation
```bash
# Install AWS CLI and tools
bash scripts/install-aws-tools.sh
```

## Documentation

Detailed documentation is in the `docs/` directory:
- **docs/iac.md**: The `iac` command: target resolution, subcommands, exit codes
- **docs/promote_staging.md**: Blue/green promotion workflow documentation
- **docs/bootstrap.md**, **docs/deploy.md**: The deprecated shims and how their arguments map to `iac`

## Architecture

### Directory Structure
The system creates a hierarchical structure:
- **TARGET_DIR/**: Root deployment directory
  - **conda_package_cache/**: Shared conda package cache
  - **engine_home/**: Management engine directory
    - **engine_a/**, **engine_b/**: Blue/green engine environments
    - **engine**: Symlink to active engine
    - **micromamba**: Conda package installer
  - **infrastructure/**: Deployment tiers
    - **blue/**, **green/**: Environment directories
    - **production**, **staging**: Symlinks to active tiers
  - **user_envs/**: Individual user environments

### Engine System
The engine is a self-contained conda environment containing deployment tools:
- Python 3.13 with conda, mamba, pip
- Rich for terminal output, PyYAML for configuration
- Blue/green rotation for zero-downtime engine updates
- Defined by `resources/defs/special/engine.yaml`

### Configuration Management
Environment definitions stored in `resources/defs/`:
- **special/**: Engine and special-purpose environments
- **universal/**: Cross-platform environments (conda, python, unix)
- **linux/**, **mac/**: Platform-specific environments
- **experimental/**: Testing environments

### Deployment Process
1. Bootstrap creates basic directory structure
2. Engine environment installed via micromamba
3. Engine deploys infrastructure tiers using YAML definitions
4. Blue/green rotation allows safe updates

### Environment Variables

When users source `$IAC_TIER_DIR/etc/profile.sh`, the following environment variables are initialized:

- **IAC_TIER_DIR**: Absolute path to the active tier directory (e.g., `/path/to/target/infrastructure/blue`)
- **IAC_TIER_NAME**: Name of the tier symlink being used (e.g., `production`, `staging`)
- **IAC_DIR**: Path to the infrastructure directory (e.g., `/path/to/target/infrastructure`)
- **IAC_PARENT**: Path to the TARGET_DIR (e.g., `/path/to/target`)
- **IAC_ORIGINAL_PATH**: Original PATH before modifications by the infrastructure
- **CONDARC**: Path to the tier's conda configuration file (e.g., `$IAC_TIER_DIR/etc/condarc`)

**Usage**:
- Interactive users can view these variables with the `iac_dump_vars` shell function
- `scripts/iac` uses `IAC_PARENT` as its default target, so `--target` is unnecessary in a shell that has sourced a tier
- `scripts/promote_staging`, when run directly, requires `IAC_TIER_DIR`; `scripts/iac promote` supplies it
- Users switch between tiers using `iac_load <tier_name>` (e.g., `iac_load staging`)

### Code Architecture

**Two Python packages under `scripts/`**:
- `scripts/iac_cli/`: the `iac` command. Standard library only, because it runs under uv before any engine exists. `cli.py` (parsing, dispatch), `config.py` (target resolution), `bootstrap.py` (layout, engine install and rotation), `tiers.py` (deploy, promote, status), `exit_codes.py` (the one exit-code table), `common.py` (`Context`, `IacError`, command running). Never import `rich` or `yaml` here.
- `scripts/engine/`: the deployer. Runs under the engine's own Python (which has rich and PyYAML), started by `iac deploy` through `scripts/sanitize-command`.

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
- Required binaries (curl, tar, git) are checked before bootstrap with helpful error messages

## Testing

### Running Tests

```bash
# Run all unit tests
pytest tests/unit/

# Run specific test file
pytest tests/unit/test_iac_cli.py -v

# Run integration tests (requires --run-integration flag)
pytest tests/integration/ --run-integration

# Run E2E tests (requires real mamba and --run-e2e flag)
pytest tests/e2e/ --run-e2e

# Run with coverage
pytest --cov=scripts/engine --cov-report=html
```

### Test Organization

**Unit Tests** (`tests/unit/`):
- Fast, isolated tests using mocks
- No external dependencies or network calls
- Test individual functions and error conditions
- Comprehensive test coverage including argument parsing, path validation, blue/green logic, error handling, environment definitions, YAML validation, binary availability checks, disk space checks, symlink validation, and path traversal protection

**Integration Tests** (`tests/integration/`):
- Test complete workflows with actual script execution
- Marked with `@pytest.mark.integration`
- Require `--run-integration` flag to execute
- May require network access or take longer to run

**End-to-End Tests** (`tests/e2e/`):
- Test complete deployment workflows using real mamba installations and YAML environment definitions
- Marked with `@pytest.mark.e2e`
- Require `--run-e2e` flag to execute
- Require real mamba/micromamba in PATH
- May take 5-10+ minutes for comprehensive tests
- Validate complete bootstrap → deploy → promote workflows with real resources

### Test Fixtures

Key fixtures in `tests/conftest.py`:
- `tmp_target_dir`: Creates temporary deployment directory structure
- `mock_filesystem`: MockFileSystem for testing file operations
- `mock_command_runner`: MockCommandRunner for testing subprocess calls
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
