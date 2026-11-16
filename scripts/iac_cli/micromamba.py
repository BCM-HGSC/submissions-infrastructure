"""
Install the pinned micromamba into engine_home.

micromamba builds the engine, so it is fetched before any engine exists.
The release is pinned and each download is checked against the checksum
recorded here, so every deployment starts from the same binary.

To move to a new release, change VERSION and replace the checksums with the
ones published beside the binaries at
https://github.com/mamba-org/micromamba-releases/releases
"""

import hashlib
from pathlib import Path
import platform

from .common import Context, IacError, log
from .exit_codes import MISSING_DEPENDENCY

VERSION = "2.10.0-0"
RELEASES_URL = "https://github.com/mamba-org/micromamba-releases/releases/download"
SHA256 = {
    "linux-64": "701f39c06f8e6a670a0e186c8479b9e5c0502a2f0cda6cef65d83bdd2875e8bd",
    "linux-aarch64": "3bb56786e21b9b24024f599fe9185b4a59dc3f9f59937a42311ee583adbbb23c",
    "linux-ppc64le": "f746f14add6430daf77ff525fc3d24ef8e7d611db397dd9bad548c4fb19aa731",
    "osx-64": "8421462a1ef1df9f7acd114f9e2a24c1332ce4f4e29f44465b4acb44e2755172",
    "osx-arm64": "c547639f5caf742236641c362746abb4a3505774753ecd08fe341643670c4c01",
}
PLATFORMS = {
    ("Linux", "x86_64"): "linux-64",
    ("Linux", "aarch64"): "linux-aarch64",
    ("Linux", "arm64"): "linux-aarch64",
    ("Linux", "ppc64le"): "linux-ppc64le",
    ("Darwin", "x86_64"): "osx-64",
    ("Darwin", "arm64"): "osx-arm64",
}
CURL = Path("/usr/bin/curl")


def ensure_micromamba(ctx: Context, *, offline: bool) -> Path:
    """
    Make engine_home/micromamba the pinned release and check that it runs.

    A micromamba from another release is replaced. Offline, whatever is
    already there is used, because nothing can be fetched.
    """
    micromamba = ctx.engine_home / "micromamba"
    platform_name = current_platform()
    if file_sha256(micromamba) == SHA256[platform_name]:
        log.debug("micromamba %s already installed", VERSION)
    elif not offline:
        fetch(ctx, micromamba, platform_name)
    elif micromamba.is_file():
        log.warning("Offline: using %s, which is not release %s", micromamba, VERSION)
    else:
        raise IacError(MISSING_DEPENDENCY, f"Offline and no micromamba at {micromamba}")
    if not ctx.dry_run and ctx.run([str(micromamba), "--version"], quiet=True):
        raise IacError(MISSING_DEPENDENCY, f"{micromamba} does not run")
    return micromamba


def current_platform() -> str:
    key = (platform.system(), platform.machine())
    if key not in PLATFORMS:
        raise IacError(
            MISSING_DEPENDENCY, f"No micromamba for platform {' '.join(key)}"
        )
    return PLATFORMS[key]


def fetch(ctx: Context, micromamba: Path, platform_name: str) -> None:
    """Download to a temporary file, verify it, then move it into place."""
    url = f"{RELEASES_URL}/{VERSION}/micromamba-{platform_name}"
    if ctx.dry_run:
        log.info("[DRY RUN] Would fetch %s to %s", url, micromamba)
        return
    if not CURL.is_file():
        raise IacError(MISSING_DEPENDENCY, f"Fetching micromamba needs {CURL}")
    log.info("Fetching micromamba %s for %s", VERSION, platform_name)
    partial = micromamba.with_name("micromamba.partial")
    command = [str(CURL), "--fail", "--location", "--silent", "--show-error"]
    command += ["--output", str(partial), url]
    try:
        if ctx.run(command):
            raise IacError(MISSING_DEPENDENCY, f"Failed to fetch {url}")
        actual = file_sha256(partial)
        if actual != SHA256[platform_name]:
            raise IacError(
                MISSING_DEPENDENCY,
                f"Checksum mismatch for {url}: "
                f"expected {SHA256[platform_name]}, got {actual}",
            )
        partial.chmod(0o755)
        partial.replace(micromamba)
    finally:
        partial.unlink(missing_ok=True)


def file_sha256(path: Path) -> str | None:
    """The SHA-256 of a file, or None if there is no such file."""
    if not path.is_file():
        return None
    with path.open("rb") as fin:
        return hashlib.file_digest(fin, "sha256").hexdigest()
