"""
Module responsible for actually deploying sofwware to a tier.
(A "tier" is a top-level directory or symlink such as "staging" or "production".)
"""

from logging import info
from pathlib import Path


def deploy(target: Path, tier: str) -> None:
    info(f"{target=}")
    info(f"{tier=}")
    exit("TODO")
