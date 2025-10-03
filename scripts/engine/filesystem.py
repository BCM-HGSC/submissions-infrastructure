"""Filesystem abstraction for testability."""

from pathlib import Path
from shutil import copytree as shutil_copytree
from shutil import rmtree as shutil_rmtree
from typing import Protocol


class FileSystemProtocol(Protocol):
    """Protocol defining filesystem operations interface."""

    def mkdir(
        self, path: Path, *, parents: bool = False, exist_ok: bool = False
    ) -> None:
        """Create a directory."""
        ...

    def rmtree(self, path: Path) -> None:
        """Remove a directory tree."""
        ...

    def copytree(
        self,
        src: Path,
        dst: Path,
        *,
        symlinks: bool = False,
        dirs_exist_ok: bool = False,
    ) -> None:
        """Copy a directory tree."""
        ...

    def symlink_to(self, link_path: Path, target: Path | str) -> None:
        """Create a symbolic link."""
        ...

    def readlink(self, path: Path) -> Path:
        """Read the target of a symbolic link."""
        ...

    def exists(self, path: Path) -> bool:
        """Check if a path exists."""
        ...

    def is_dir(self, path: Path) -> bool:
        """Check if a path is a directory."""
        ...

    def is_file(self, path: Path) -> bool:
        """Check if a path is a file."""
        ...

    def is_symlink(self, path: Path) -> bool:
        """Check if a path is a symbolic link."""
        ...


class RealFileSystem:
    """Real filesystem implementation."""

    def mkdir(
        self, path: Path, *, parents: bool = False, exist_ok: bool = False
    ) -> None:
        """Create a directory."""
        path.mkdir(parents=parents, exist_ok=exist_ok)

    def rmtree(self, path: Path) -> None:
        """Remove a directory tree."""
        shutil_rmtree(path)

    def copytree(
        self,
        src: Path,
        dst: Path,
        *,
        symlinks: bool = False,
        dirs_exist_ok: bool = False,
    ) -> None:
        """Copy a directory tree."""
        shutil_copytree(src, dst, symlinks=symlinks, dirs_exist_ok=dirs_exist_ok)

    def symlink_to(self, link_path: Path, target: Path | str) -> None:
        """Create a symbolic link."""
        link_path.symlink_to(target)

    def readlink(self, path: Path) -> Path:
        """Read the target of a symbolic link."""
        return path.readlink()

    def exists(self, path: Path) -> bool:
        """Check if a path exists."""
        return path.exists()

    def is_dir(self, path: Path) -> bool:
        """Check if a path is a directory."""
        return path.is_dir()

    def is_file(self, path: Path) -> bool:
        """Check if a path is a file."""
        return path.is_file()

    def is_symlink(self, path: Path) -> bool:
        """Check if a path is a symbolic link."""
        return path.is_symlink()


class MockFileSystem:
    """Mock filesystem for testing."""

    def __init__(self):
        """Initialize mock filesystem with tracking structures."""
        self.directories: set[Path] = set()
        self.files: set[Path] = set()
        self.symlinks: dict[Path, Path | str] = {}
        self.removed: list[Path] = []
        self.copied: list[tuple[Path, Path]] = []

    def mkdir(
        self, path: Path, *, parents: bool = False, exist_ok: bool = False
    ) -> None:
        """Mock directory creation."""
        if path in self.directories and not exist_ok:
            raise FileExistsError(f"Directory exists: {path}")
        if parents:
            # Create parent directories
            for parent in reversed(path.parents):
                self.directories.add(parent)
        self.directories.add(path)

    def rmtree(self, path: Path) -> None:
        """Mock directory tree removal."""
        self.removed.append(path)
        # Remove path and all children
        to_remove = {p for p in self.directories if p == path or path in p.parents}
        self.directories -= to_remove
        to_remove_files = {f for f in self.files if f == path or path in f.parents}
        self.files -= to_remove_files
        to_remove_links = {
            link for link in self.symlinks if link == path or path in link.parents
        }
        for link in to_remove_links:
            del self.symlinks[link]

    def copytree(
        self,
        src: Path,
        dst: Path,
        *,
        symlinks: bool = False,  # noqa: ARG002
        dirs_exist_ok: bool = False,  # noqa: ARG002
    ) -> None:
        """Mock directory tree copy."""
        self.copied.append((src, dst))
        self.directories.add(dst)

    def symlink_to(self, link_path: Path, target: Path | str) -> None:
        """Mock symbolic link creation."""
        self.symlinks[link_path] = target

    def readlink(self, path: Path) -> Path:
        """Mock reading symbolic link target."""
        if path not in self.symlinks:
            raise OSError(f"Not a symlink: {path}")
        target = self.symlinks[path]
        return Path(target) if isinstance(target, str) else target

    def exists(self, path: Path) -> bool:
        """Mock path existence check."""
        return path in self.directories or path in self.files or path in self.symlinks

    def is_dir(self, path: Path) -> bool:
        """Mock directory check."""
        return path in self.directories

    def is_file(self, path: Path) -> bool:
        """Mock file check."""
        return path in self.files

    def is_symlink(self, path: Path) -> bool:
        """Mock symlink check."""
        return path in self.symlinks
