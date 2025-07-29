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
- Validate YAML definitions before deployment
