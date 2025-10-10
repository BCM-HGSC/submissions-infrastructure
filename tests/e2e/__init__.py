"""End-to-end tests requiring real mamba installation.

These tests deploy actual conda environments using real YAML definitions
and are marked with @pytest.mark.e2e. They require:
- Real mamba/micromamba installation in PATH
- The --run-e2e flag to execute
- Longer execution time (5-10+ minutes for comprehensive tests)

Run with: pytest --run-e2e tests/e2e/
"""
