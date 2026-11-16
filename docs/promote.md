# Promotion

`scripts/iac promote` makes the staging tier the production tier.

```
iac promote [--dry-run]
```

It needs no engine and no sourced tier: like every `iac` subcommand it finds
the target from `--target`, `IAC_PARENT`, or a config file (see
[iac.md](iac.md)).

## What it does

`staging` and `production` are symlinks in `TARGET/infrastructure`, each
pointing to `blue` or `green`. Promotion points `production` at the color
staging has, then points `staging` at the other color.

Before:

```
infrastructure/
├── blue/
├── green/
├── production -> blue
└── staging -> green
```

After:

```
infrastructure/
├── blue/
├── green/
├── production -> green
└── staging -> blue
```

Users who source `production/etc/profile.sh` get the new tier in their next
shell. A shell that is already open keeps the tier it loaded, because
`profile.sh` resolves the link when it is sourced; `iac_reload` picks up the
new one.

## What it checks first

Promotion is refused, with exit code 3 and nothing changed, when:

- `staging` is missing, is not a symlink, or points to anything other than
  `blue` or `green`;
- the staging tier has not been deployed. A tier counts as deployed when it
  has `meta/commit` and `etc/profile.sh`. `iac deploy` removes `meta/`
  before it starts and writes `meta/commit` last, so a deploy that failed or
  was interrupted leaves a tier that cannot be promoted;
- `production` exists but is not a symlink to `blue` or `green`;
- `staging` and `production` point to the same color.

A missing `production` link is created. A `production` link whose tier
directory is gone is replaced.

## Atomicity

Each link is replaced by creating a temporary link and renaming it over the
old one, so there is no moment when `production` does not exist. Production
is switched first. If the command is interrupted between the two renames,
both links name the same color; production is already correct, and
`iac bootstrap` moves staging to the other color.

## Rolling back

The tier that was production becomes staging and is left untouched, so
promoting again swaps back:

```bash
scripts/iac promote     # production is the new tier
scripts/iac promote     # production is the old tier again
```

This works only until the next `iac deploy`, which rebuilds staging and so
destroys the old production tier. Check `iac status` first: it shows the
commit deployed in each tier.
