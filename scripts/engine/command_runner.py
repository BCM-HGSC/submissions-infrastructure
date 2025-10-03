"""Command execution abstraction for testability."""

from pathlib import Path
from subprocess import CompletedProcess
from subprocess import run as subprocess_run
from typing import Any, Protocol


class CommandRunnerProtocol(Protocol):
    """Protocol defining command execution interface."""

    def run(
        self,
        args: list[str | Path],
        *,
        env: dict[str, str] | None = None,
        stdout: Any = None,
        stderr: Any = None,
    ) -> CompletedProcess:
        """Execute a command and return the result."""
        ...


class RealCommandRunner:
    """Real command execution implementation."""

    def run(
        self,
        args: list[str | Path],
        *,
        env: dict[str, str] | None = None,
        stdout: Any = None,
        stderr: Any = None,
    ) -> CompletedProcess:
        """Execute a command using subprocess.run."""
        # Convert Path objects to strings for subprocess
        str_args = [str(arg) for arg in args]
        return subprocess_run(
            str_args, env=env, stdout=stdout, stderr=stderr, check=False
        )


class MockCommandRunner:
    """Mock command runner for testing."""

    def __init__(self):
        """Initialize mock command runner with tracking."""
        self.calls: list[dict[str, Any]] = []
        self.return_value: CompletedProcess = CompletedProcess(
            args=[], returncode=0, stdout=b"", stderr=b""
        )

    def run(
        self,
        args: list[str | Path],
        *,
        env: dict[str, str] | None = None,
        stdout: Any = None,
        stderr: Any = None,
    ) -> CompletedProcess:
        """Mock command execution."""
        # Record the call
        self.calls.append(
            {
                "args": [str(arg) for arg in args],
                "env": env,
                "stdout": stdout,
                "stderr": stderr,
            }
        )
        return self.return_value

    def set_return_value(
        self,
        returncode: int = 0,
        stdout: bytes | None = None,
        stderr: bytes | None = None,
    ) -> None:
        """Set the return value for subsequent run() calls."""
        self.return_value = CompletedProcess(
            args=[],
            returncode=returncode,
            stdout=stdout or b"",
            stderr=stderr or b"",
        )

    def assert_called_with(
        self,
        args: list[str],
        *,
        env: dict[str, str] | None = None,
    ) -> bool:
        """Check if a command was called with specific arguments."""
        for call in self.calls:
            if call["args"] == args and (env is None or call["env"] == env):
                return True
        return False

    def get_call_count(self) -> int:
        """Get the number of times run() was called."""
        return len(self.calls)

    def reset(self) -> None:
        """Reset call history."""
        self.calls = []
