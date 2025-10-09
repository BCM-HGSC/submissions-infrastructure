# Documentation Index

This directory contains comprehensive documentation for the submissions-infrastructure project's core scripts and workflows.

## Available Documentation

- **[bootstrap.md](bootstrap.md)** - Complete documentation for `scripts/bootstrap-engine`
  - Engine creation and rotation
  - Blue/green deployment for the management engine
  - Binary verification and micromamba setup

- **[deploy.md](deploy.md)** - Documentation for `scripts/deploy` and the Python deployment engine
  - Tier deployment and management
  - Environment discovery and validation
  - Profile generation and IAC variables

- **[promote_staging.md](promote_staging.md)** - Blue/green promotion workflow
  - Staging to production promotion
  - Symlink rotation and validation
  - Zero-downtime deployment workflow

## Quick Start Guide

### New Deployment

If you're setting up a new infrastructure deployment from scratch:

1. **Bootstrap the infrastructure** - Creates engine and directory structure
   - Read: [bootstrap.md](bootstrap.md)
   - Run: `scripts/bootstrap TARGET_DIR`

2. **Deploy a tier** - Creates conda environments for a specific tier
   - Read: [deploy.md](deploy.md)
   - Run: `scripts/deploy TARGET_DIR staging`

3. **Test and promote** - Move staging to production
   - Read: [promote_staging.md](promote_staging.md)
   - Run: `scripts/promote_staging` (after sourcing tier profile)

### Updating Existing Infrastructure

If you already have infrastructure and want to update it:

1. **Update staging tier** - Deploy changes to staging first
   - Read: [deploy.md](deploy.md)
   - Run: `scripts/deploy TARGET_DIR staging`

2. **Test changes** - Validate in staging environment
   - Source: `source TARGET_DIR/infrastructure/staging/etc/profile.sh`
   - Test your workflows

3. **Promote to production** - Make staging the new production
   - Read: [promote_staging.md](promote_staging.md)
   - Run: `scripts/promote_staging`

### Engine Updates

If you need to update the management engine itself:

1. **Update engine** - Rotate to new engine version
   - Read: [bootstrap.md](bootstrap.md)
   - Run: `scripts/bootstrap-engine TARGET_DIR`

2. **Deploy with new engine** - Use the updated engine to deploy tiers
   - Read: [deploy.md](deploy.md)
   - Run: `scripts/deploy TARGET_DIR staging`

## Decision Tree

```
Are you starting from scratch?
├─ Yes → Start with bootstrap.md
│         Run: scripts/bootstrap TARGET_DIR
│         Then: scripts/deploy TARGET_DIR staging
│
└─ No → Do you need to update the engine?
        ├─ Yes → See bootstrap.md
        │         Run: scripts/bootstrap-engine TARGET_DIR
        │
        └─ No → Do you want to update a tier?
                ├─ Yes → See deploy.md
                │         Run: scripts/deploy TARGET_DIR staging
                │         Then promote with scripts/promote_staging
                │
                └─ Just learning? → Read all three docs in order:
                                     1. bootstrap.md
                                     2. deploy.md
                                     3. promote_staging.md
```

## Additional Resources

- **[../CLAUDE.md](../CLAUDE.md)** - Project architecture, testing, and development workflow
- **[../README.md](../README.md)** - Project overview and quick reference

## Common Workflows

### Full Deployment Cycle
```bash
# 1. Bootstrap (first time only)
scripts/bootstrap /path/to/target

# 2. Deploy to staging
scripts/deploy /path/to/target staging

# 3. Test in staging
source /path/to/target/infrastructure/staging/etc/profile.sh
# ... run tests ...

# 4. Promote to production
scripts/promote_staging
```

### Update and Rotation
```bash
# Deploy changes to staging
scripts/deploy /path/to/target staging --offline

# Test thoroughly
source /path/to/target/infrastructure/staging/etc/profile.sh
# ... validate changes ...

# Promote when ready
scripts/promote_staging
```

## Getting Help

- Check script help: `scripts/<script-name> --help`
- Use dry-run mode: `scripts/<script-name> --dry-run`
- Enable verbose output: `scripts/<script-name> --verbose`
