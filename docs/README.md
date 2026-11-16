# Documentation Index

- **[iac.md](iac.md)**: the `scripts/iac` command. Start here. Covers
  choosing the target, every subcommand, exit codes, and the mapping from
  the old scripts.
- **[promote_staging.md](promote_staging.md)**: how promotion swaps the
  staging and production links.
- **[bootstrap.md](bootstrap.md)**, **[deploy.md](deploy.md)**: the
  deprecated `bootstrap`, `bootstrap-engine`, and `deploy` scripts.
- **[../CLAUDE.md](../CLAUDE.md)**: architecture, testing, and development
  workflow.

## Which command?

| Situation | Command |
|---|---|
| New deployment | `scripts/iac bootstrap --target TARGET`, then `scripts/iac deploy --target TARGET` |
| Update the software | `scripts/iac deploy`, test in staging, then `scripts/iac promote` |
| Update the engine itself | `scripts/iac engine`, then `scripts/iac deploy` |
| See what is deployed | `scripts/iac status` |

`--target` can be left out once `IAC_PARENT` is in the environment or a
config file names the target; see [iac.md](iac.md).

## Full cycle

```bash
# 1. Bootstrap (first time only)
scripts/iac bootstrap --target /path/to/target

# 2. Deploy to staging
scripts/iac deploy --target /path/to/target

# 3. Test in staging
source /path/to/target/infrastructure/staging/etc/profile.sh
# ... run tests ...

# 4. Promote to production
scripts/iac promote --target /path/to/target
```

## Getting help

- `scripts/iac --help` and `scripts/iac SUBCOMMAND --help`
- `--dry-run` shows what a command would do without changing anything
- `--verbose` logs debugging detail
