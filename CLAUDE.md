# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains infrastructure automation code for generating on-prem conda-based infrastructure for the Submissions team at BCM-HGSC.The system creates a tiered deployment structure with blue/green rotation capabilities and engine-based management.

## Key Commands

### Bootstrap Infrastructure
```bash
# Bootstrap new infrastructure with all components
scripts/bootstrap TARGET_DIR
scripts/bootstrap TARGET_DIR --verbose --force

# Bootstrap just the engine (management tools)
scripts/bootstrap-engine TARGET_DIR
scripts/bootstrap-engine TARGET_DIR --offline --verbose -y
```

### Deploy Infrastructure Tiers
```bash
# Deploy specific tier using the engine
scripts/deploy TARGET_DIR TIER
scripts/deploy /path/to/target blue --offline
scripts/deploy /path/to/target staging --dry-run --force
# the tier is usually staging
```

### Promote Staging to Production
```bash
# Switch production and staging symlinks (requires IAC_TIER_DIR in environment)
scripts/promote_staging

# This swaps which tier is production and which is staging
# Example: if production -> blue and staging -> green, after promotion:
#          production -> green and staging -> blue
```

### AWS Tools Installation
```bash
# Install AWS CLI and tools
bash scripts/install-aws-tools.sh
```

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
- The `scripts/promote_staging` script requires `IAC_TIER_DIR` to be set in the environment (this indicates which tier is currently active and needs promotion)
- Users switch between tiers using `iac_load <tier_name>` (e.g., `iac_load staging`)

### Code Architecture

**Testability Design**:
- `scripts/engine/filesystem.py`: Filesystem abstraction with Protocol, real implementation, and mock
- `scripts/engine/command_runner.py`: Command execution abstraction for mocking subprocess calls
- `scripts/engine/validators.py`: YAML environment validation with comprehensive error messages
- Dependency injection in `deploy_tier()` and `MambaDeployer` for testing
- Pure functions separated from side effects (e.g., `validate_tier_path()`, `validate_color()`)

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
- Check engine logs in deployment process
- YAML definitions are automatically validated before deployment

## Testing

### Running Tests

```bash
# Run all unit tests
pytest tests/unit/

# Run specific test file
pytest tests/unit/test_deploy_args.py -v

# Run integration tests (requires --run-integration flag)
pytest tests/integration/ --run-integration

# Run with coverage
pytest --cov=scripts/engine --cov-report=html
```

### Test Organization

**Unit Tests** (`tests/unit/`):
- Fast, isolated tests using mocks
- No external dependencies or network calls
- Test individual functions and error conditions
- 129 tests covering argument parsing, path validation, blue/green logic, error handling, environment definitions, and YAML validation

**Integration Tests** (`tests/integration/`):
- Test complete workflows with actual script execution
- Marked with `@pytest.mark.integration`
- Require `--run-integration` flag to execute
- May require network access or take longer to run

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
