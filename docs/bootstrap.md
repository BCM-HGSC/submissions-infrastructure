# bootstrap-engine

## Overview

The `scripts/bootstrap-engine` executable is a bash script responsible for creating and rotating the infrastructure maintenance engine.

## Purpose

This script creates a fresh conda environment containing deployment tools (Python, mamba, rich, PyYAML, etc.) in a blue/green rotation pattern.
Most often the user runs `scripts/bootstrap-engine /path/to/target_dir`.

## Arguments and Options

**Positional Arguments:**
- `TARGET_DIR` (required): Parent directory where engine_home will be created

**Options:**
- `--offline`: Run conda create with --offline flag
- `-v, --verbose`: Enable verbose logging
- `-y, --yes`: Pass -y flag to mamba (assume yes for prompts)
- `-n, --dry-run`: Show what would be done without making changes
- `-h, --help`: Show help message

## Operation Flow

1. **Argument Parsing**: Parses TARGET_DIR and options (--offline, --verbose, -y, --dry-run)

2. **Path Resolution**:
   - Determines project root from script location
   - Sets ENGINE_HOME to `$TARGET_DIR/engine_home`
   - Sets CONDA_PKGS_DIRS to `$TARGET_DIR/conda_package_cache`

3. **Setup Environment**:
   - Creates `$ENGINE_HOME/` directory
   - Creates `$CONDA_PKGS_DIRS/` directory

4. **Binary Verification**:
   - Checks for required binaries (curl, tar) with helpful error messages
   - Exits with code 2 if missing

5. **Micromamba Setup**:
   - Checks if `$ENGINE_HOME/micromamba` exists
   - If not, runs `scripts/fetch-micromamba "$ENGINE_HOME"` to download and install it

6. **Engine Directory Rotation**:
   - Reads current engine symlink to determine active engine
   - Selects next directory from `engine_a`, `engine_b` using blue/green rotation

7. **Environment Creation**:
   - Removes existing engine directory if present
   - Builds micromamba command: `$MAMBA env create -p <engine_path> -f resources/defs/special/engine.yaml`
   - Adds `--offline` and `-y` flags if specified
   - Runs command via `scripts/sanitize-command` with CONDA_PKGS_DIRS set

8. **Symlink Management**:
   - Removes existing `engine` symlink if present
   - Creates new symlink `$ENGINE_HOME/engine` pointing to the newly created engine directory

## Engine Directory Rotation Logic

The script maintains two potential engine directories (`engine_a`, `engine_b`) and rotates between them in a blue/green deployment model.
This allows undoing the most recent engine deployment.

## Engine Environment Contents

The engine environment is defined by `resources/defs/special/engine.yaml` and typically contains:
- Core conda/mamba tools
- Python deployment scripts
- Any other tools needed for infrastructure management

## Error Handling

**Exit Codes:**
- 0: Success
- 1: General error (usage error, missing TARGET_DIR, missing dependency)
- 2: Missing dependency (curl or tar not found)
- 3: Invalid input (missing engine.yaml, invalid path)
- 4: Operation failed (command execution failure)

The script provides helpful error messages for missing binaries with platform-specific installation instructions.

## Integration

This script is typically called during initial infrastructure setup:
- By `scripts/bootstrap` to create the complete infrastructure
- Manually to update or rotate the engine

The script uses a sanitized environment via `scripts/sanitize-command` to ensure reproducibility.
