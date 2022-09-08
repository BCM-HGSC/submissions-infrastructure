# submissions-infrastructure

Code to generate on-prem code infrastructure for the Submissions team at BCM-HGSC using conda

## Layout

- some other team or application
- submissions
  - condarc -> infrastructure/current/condarc
  - conda_package_cache
  - user_envs
    - hale
    - eskinner
    - ...
  - infrastructure
    - blue
      - bin
      - etc
      - condarc (master file)
      - conda
        - defs (YAML definitions of the envs)
        - envs
          - conda_a (our copy of the conda machinery)
            - condarc -> ../../condarc
          - bio_a (any bioinformatics tools we pull from bioconda)
          - main_a (all python stuff we pull from conda-forge)
          - unix_a (any unix tools we pull from conda-forge)
          - conda -> conda_a
          - bio -> bio_a
          - main -> main_a
          - unix -> unix_a
    - green
    - staging
    - testing
    - current (symlink to blue or green)
- some other team or application

## Sources

- https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
- https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh
