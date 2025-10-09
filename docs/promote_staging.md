# promote_staging

## Overview

The `scripts/promote_staging` executable is a Python script that promotes the staging tier to production by swapping the production and staging symlinks.

## Purpose

This script performs a blue/green deployment rotation, making the current staging environment become production and moving staging to the opposite color. This enables zero-downtime deployments where changes are tested in staging before being promoted.

The script must be run from within an active tier environment (after sourcing a tier's profile.sh).

## Arguments and Options

**Options:**
- `-n, --dry-run`: Show what would be done without making changes
- `-h, --help`: Show help message

**No positional arguments required** - the script reads the infrastructure path from the `IAC_TIER_DIR` environment variable.

## Prerequisites

**Environment Variables:**
- `IAC_TIER_DIR` must be set (automatically set when sourcing `$TIER/etc/profile.sh`)

**Example Setup:**
```bash
# Source a tier to set IAC_TIER_DIR
source /path/to/target/infrastructure/staging/etc/profile.sh

# Now promote_staging can run
scripts/promote_staging
```

## Operation Flow

1. **Environment Validation**:
   - Checks that `IAC_TIER_DIR` is set in the environment
   - Resolves tier path and determines infrastructure directory

2. **Staging Validation**:
   - Validates that `staging` symlink exists and points to blue or green
   - Reads the staging color (e.g., "green")

3. **Production Validation**:
   - If `production` symlink exists:
     - Validates it points to blue or green
     - Ensures production and staging point to different colors
     - Removes the production symlink

4. **Symlink Rotation**:
   - Creates new `production` symlink pointing to staging's color
   - Updates `staging` symlink to point to the opposite color

## Example Workflow

**Before promotion:**
```
infrastructure/
├── blue/              (deployed tier)
├── green/             (deployed tier)
├── production -> blue
└── staging -> green
```

**After running `scripts/promote_staging`:**
```
infrastructure/
├── blue/
├── green/
├── production -> green  (was staging)
└── staging -> blue      (swapped to opposite)
```

**Effect:**
- Production now serves from green (previously staging)
- Staging now points to blue for next round of testing

## Validation and Safety

**Symlink Validation:**
- Uses `validate_symlink_target()` from `scripts/engine/validators.py`
- Ensures symlinks exist and point to valid targets (blue or green)
- Prevents promotion when staging and production point to the same color

**Error Conditions:**
- Missing `IAC_TIER_DIR` environment variable
- Invalid or missing staging symlink
- Staging and production pointing to the same color
- Symlink target is not blue or green

## Error Handling

**Exit Codes:**
- 0: Success
- 1: General error (missing IAC_TIER_DIR, validation failure, same color error)

All errors are written to stderr with descriptive messages.

## Integration

**Typical Deployment Workflow:**
1. Deploy changes to staging: `scripts/deploy /path/to/target staging`
2. Test changes in staging environment
3. Source staging profile: `source /path/to/target/infrastructure/staging/etc/profile.sh`
4. Promote to production: `scripts/promote_staging`
5. Production now serves the tested changes

**Related Scripts:**
- `scripts/deploy`: Deploy tiers before promotion
- `scripts/bootstrap`: Initial infrastructure setup

**Related Environment Variables:**
- `IAC_TIER_DIR`: Set by sourcing tier profile, required for promotion
- `IAC_DIR`: Infrastructure directory path
- `IAC_TIER_NAME`: Current tier name (production/staging)
