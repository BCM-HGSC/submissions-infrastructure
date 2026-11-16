# bootstrap and bootstrap-engine (deprecated)

`scripts/bootstrap` and `scripts/bootstrap-engine` are shims. Each prints a
deprecation warning, translates its arguments, and runs `scripts/iac`. They
will be removed. See [iac.md](iac.md).

| Old | Runs |
|---|---|
| `bootstrap [OPTIONS] TARGET_DIR` | `iac bootstrap --target TARGET_DIR [OPTIONS]` |
| `bootstrap-engine [OPTIONS] TARGET_DIR` | `iac engine --target TARGET_DIR [OPTIONS]` |

Differences from the old scripts:

- `bootstrap --force` is refused. It used to erase
  `TARGET_DIR/infrastructure`, production included. `iac bootstrap` only
  creates what is missing, so re-running it needs no flag.
- `bootstrap` on an existing deployment no longer rotates the engine. Use
  `iac engine` for that.
- `bootstrap-engine --force` only ever skipped the disk-space check; it
  becomes `--skip-disk-check`.
- `bootstrap-engine -y` is accepted and ignored. The install never prompts.
- `TARGET_DIR` may be omitted when `IAC_PARENT` or a config file names the
  target.
