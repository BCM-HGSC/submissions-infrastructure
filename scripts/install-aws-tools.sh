#!/bin/bash

# Version 1.0.0

# Install script for /hgsccl_software/prod/aws/venv

# TODO: Replay history option
# TODO: Option to move and replace prior installation
# TODO: Make TARGET_PREFIX an option (-p)

set -Eeuo pipefail

DEFAULT_TARGET_PREFIX="/hgsccl_software/prod"

THIS_SCRIPT="$(readlink -f ${BASH_SOURCE[0]})"
MY_PARENT="$(dirname ${THIS_SCRIPT})"
MY_RESOURCES_DIR="$MY_PARENT"/install-aws-tools-resources

usage() {
    echo "USAGE: $0 [TARGET_PREFIX]"
    echo
    echo "TARGET_PREFIX: directory to be created (if necessary) and populated"
    echo "default value: $DEFAULT_TARGET_PREFIX"
    echo "value of AWS_TARGET environment variable: (${AWS_TARGET:-''})"
} >&2

main() {
    if [ $# -gt 1 ]; then
        usage
        exit 1
    fi

    if [[ -n "$1" ]]; then
        TARGET_PREFIX="$1"
    elif [[ -n "$AWS_TARGET" ]]; then
        TARGET_PREFIX="$AWS_TARGET"
    elif [[ -d "$DEFAULT_TARGET_PREFIX" ]]; then
        TARGET_PREFIX=$DEFAULT_TARGET_PREFIX
    else
        echo "No value or defaults for TARGET_PREFIX"
        exit 2
    fi
    TARGET_PREFIX="$(readlink -f $TARGET_PREFIX)"

    INSTALLER=$(command which mamba conda 2>/dev/null | head -n1)

    export PATH=/usr/bin:/bin

    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    export AWS_ROOT="$TARGET_PREFIX"/aws
    export HOME="$AWS_ROOT"/users/$USER  # Avoid any weirdness from home directory.
    HISTORY_DIR="$AWS_ROOT"/history/$TIMESTAMP
    LOG_FILE="$HISTORY_DIR"/install.log
    VENV_BIN_DIR="$AWS_ROOT"/venv/bin
    AWS_PYTHON_DIR="$TARGET_PREFIX"/aws-python
    AWS_CLI_DIR="$TARGET_PREFIX"/aws-cli
    PREFIX_DIRS="$AWS_PYTHON_DIR/bin:$AWS_CLI_DIR"

    f mkdir -p "$HISTORY_DIR"

    # Dump output to log
    {
        ts starting install-aws-tools

        ts "AWS_ROOT: $AWS_ROOT"
        ts "LOG_FILE: $LOG_FILE"

        f mkdir -p "$HOME" "$VENV_BIN_DIR"

        cd "$TARGET_PREFIX"/aws

        [[ -d "$AWS_PYTHON_DIR" ]] || f install_aws_python
        f report_aws_python

        [[ -d "$AWS_CLI_DIR" ]] || f install_aws_cli
        f report_aws_cli

        f install_activate_script "$PREFIX_DIRS"

        f test_deployment

        ts finished install-aws-tools
    } 2>&1 | tee -a "$LOG_FILE"
} >&2

install_aws_python() {
    # Keep a copy of the sources for reference.
    ENV_YAML_PATH="$MY_RESOURCES_DIR"/install-aws-tools.env.yaml
    export CONDARC="$MY_RESOURCES_DIR"/install-aws-tools.condarc.yaml
    ts "CONDARC: $CONDARC"
    f cp -p "$THIS_SCRIPT" "$CONDARC" "$ENV_YAML_PATH" "$HISTORY_DIR"/

    ts "$INSTALLER"
    "$INSTALLER" info

    rm -rf "$AWS_PYTHON_DIR"
    f "$INSTALLER" env create -p "$AWS_PYTHON_DIR" -f "$ENV_YAML_PATH"
}

report_aws_python() {
    ts "$INSTALLER" env export -p "$AWS_PYTHON_DIR"
    ts '>' "$HISTORY_DIR/install-aws-tools.env.pinned.yaml"
    "$INSTALLER" env export -p "$AWS_PYTHON_DIR" \
        | sed -e '/^name:/d;/^prefix:/d' \
        > "$HISTORY_DIR/install-aws-tools.env.pinned.yaml"
}

install_aws_cli() {
    local platform=$(uname)
    if [[ $platform == "Linux" ]]; then
        f install_aws_cli_linux 
    elif [[ $platform == "Darwin" ]]; then
        f "$MY_RESOURCES_DIR"/install-aws-cli-mac.sh \
            "$HISTORY_DIR" "$TARGET_PREFIX"
    else
        echo "unsupported platform: $platform"
        return 10
    fi
}

install_aws_cli_linux() {
    # Download the AWS CLI installation bundle
    ts "Downloading AWS CLI..."
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"

    # Unzip the installation bundle
    ts "Unzipping AWS CLI..."
    unzip awscliv2.zip
    mv awscliv2.zip "$HISTORY_DIR"/

    # Run the AWS CLI installation script
    ts "Installing AWS CLI..."
    ./aws/install -i "$AWS_CLI_DIR" -b "$AWS_CLI_DIR"

    # Clean up temporary files
    ts "Cleaning up..."
    f rm -rf aws
}

report_aws_cli() {
    "$AWS_CLI_DIR"/aws --version > "$HISTORY_DIR/install-aws-tools.cli.txt"
}

install_activate_script() {
    local script="$MY_RESOURCES_DIR"/aws-tools-activate-template.sh
    m4 -D PREFIX_DIRS="$1" "$script" > "$VENV_BIN_DIR"/activate
}

test_deployment() {
    PS1="dummy"
    source "$VENV_BIN_DIR"/activate
    which python
    which w2sc_builder
    python --version
    python <<EOD
from boto3 import __version__ as bv
from w2sc_builder.version import __version__ as wv
print(f"boto3: {bv}")
print(f"w2sc_builder: {wv}")
EOD
    w2sc_builder --help >/dev/null
    which aws
    aws --version
    alias deactivate
    __aws_tools_deactivate
    ! alias deactivate 2>/dev/null
}

f() {
    ts "$@"
    "$@"
}

ts() {
    echo
    echo $(date +%FT%T) $*
}

main "$@"
