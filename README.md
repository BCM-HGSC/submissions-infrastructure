# submissions-infrastructure

Code to generate on-prem code infrastructure for the Submissions team at BCM-HGSC using conda

## Layout

- some other team or application
- submissions
  - condarc -> infrastructure/production/condarc
  - conda_package_cache
  - config (any configuration for installing/updating infrastructure)
  - engine_home (non-user HOME containing machinery)
    - .conda (implementation detail)
    - .condrc (not present by default)
    - Library (implementation detail)
    - engine_a (conda environment containing conda and pip)
    - engine -> engine_a (or engine_b if we re-bootstrapped the engine)
  - user_envs
    - hale
    - eskinner
    - ...
  - infrastructure
    - blue
      - bin
      - etc (all automatically generated or installed "config" or "profile" items)
      - condarc (master file)
      - conda
        - defs (YAML definitions of the envs)
        - envs
          - conda (our copy of the conda machinery)
            - condarc -> ../../condarc
          - bio (any bioinformatics tools we pull from bioconda)
          - main (all python stuff we pull from conda-forge)
          - unix (any unix tools we pull from conda-forge)
    - green (duplicate of blue)
    - production (symlink to blue or green)
    - staging (symlink to blue or green)
    - testing
  - etc -> infrastructure/current/etc
- some other team or application

## Execution

1. Clone or download the software.
2. `bash /path/to/submissions-infrastructure/scripts/bootstrap.sh -h`

## Sources

- https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
- https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh
