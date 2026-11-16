# deploy (deprecated)

`scripts/deploy` is a shim. It prints a deprecation warning, translates its
arguments, and runs `scripts/iac deploy`. It will be removed. See
[iac.md](iac.md) for what deploying does.

| Old | Runs |
|---|---|
| `deploy TARGET_DIR TIER [OPTIONS]` | `iac deploy --target TARGET_DIR --tier TIER [OPTIONS]` |
| `deploy TARGET_DIR TIER --force` | `iac deploy ... --overwrite --skip-disk-check` |

`--force` used to mean both "replace a tier that is not normally replaced"
and "ignore low disk space". The two are now separate options.

`TARGET_DIR` and `TIER` may be omitted: the target then comes from
`IAC_PARENT` or a config file, and the tier defaults to `staging`.

## Environment variables set by a tier

When users source a tier's profile (`$IAC_TIER_DIR/etc/profile.sh`):

- `IAC_TIER_DIR`: Absolute path to the tier directory
- `IAC_TIER_NAME`: Name of the tier symlink (production/staging)
- `IAC_DIR`: Path to infrastructure directory
- `IAC_PARENT`: Path to TARGET_DIR
- `IAC_ORIGINAL_PATH`: Original PATH before modifications
- `CONDARC`: Path to tier's conda configuration
