# AWS Tools

Operation:

```bash
/path/to/install-aws-tools.sh [TARGET_PREFIX]
```

`TARGET_PREFIX` is determined by the first available of:

- the command line
- the `AWS_TARGET` environment variable
- `/hgsccl_software/prod`

Spec for our local deployments of AWS tools.

## Technologies

- AWS CLI version 2
- python-3.11
  - aws-mfa
  - boto3
  - cfn-lint
  - dateutil
  - dynamo-json
  - json2yaml
  - pandas
  - pip
  - pyyaml
  - requests
  - s3cmd
  - s4cmd
  - taskcat
  - yq
  - **w2sc_builder (local src tarball)**
- activate script
  - aws/venv/bin/activate

## Directory Layout

- `$TARGET_PREFIX` [/hgsccl_software/prod]
  - aws
    - history
      - `$(date +%Y%m%d_%H%M)`
        - aws-tools.yaml
        - install-aws-tools.sh
        - w2sc_builder[-VER].tgz
        - install.log
        - contents.txt
        - env.yaml
      - ...
    - users (implementation details)
      - user1
        - conda
          - pkgs
      - user2 ...
    - venv -> venv_2
    - venv_2
      - bin
        - activate
  - aws-cli
    - aws
    - aws_completer
    - ... (implementation details)
  - aws-python (python-3.11)
    - bin
    - ... (implementation details)

## Example Use Case

```bash
export PATH=/usr/bin:/bin
source /hgsccl_software/prod/aws/venv/bin/activate
aws --version  # Shows AWS CLI version 2
aws-mfa --help  # No error
w2sc_builder --help  # Shows version 1.0.1
deactivate  # venv-style, just restore original PATH and PS1
command which aws 2>/dev/null || echo gone  # get "gone"
```
