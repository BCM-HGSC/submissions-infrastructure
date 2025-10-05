"""Unit tests for deploy script argument parsing.

Note: The deploy script is a thin wrapper that:
1. Parses TARGET_DIR from the first positional argument
2. Passes all arguments to the Python engine module at TARGET_DIR/engine_home/engine/

Testing this script requires a functioning engine environment, making it unsuitable
for unit tests. The actual argument parsing (--dry-run, --offline, --keep, --force)
happens in the Python engine module, which is already tested in test_engine_cli.py.

Integration tests in tests/integration/ would be appropriate for testing the full
deploy workflow with a real or mocked engine environment.
"""

# Intentionally empty - no unit tests needed for this thin wrapper script.
# The Python module it wraps (scripts.engine.__main__) is tested in test_engine_cli.py.
