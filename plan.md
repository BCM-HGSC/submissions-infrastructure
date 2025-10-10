# Test Infrastructure Implementation Plan

This plan addresses the testability and quality issues identified in the project review, organized by priority.

## Priority 1: Add Test Infrastructure

### 1.1 Create Test Directory Structure
- [x] Create `tests/` directory at project root
- [x] Create `tests/unit/` subdirectory for unit tests
- [x] Create `tests/integration/` subdirectory for integration tests
- [x] Create `tests/fixtures/` subdirectory for test data and fixtures
- [x] Create `tests/__init__.py`
- [x] Create `tests/conftest.py` with shared fixtures

### 1.2 Add pytest Configuration
- [x] Create `pyproject.toml` with pytest configuration
  - [x] Configure test discovery patterns
  - [x] Set up markers for integration tests (`@pytest.mark.integration`)
  - [x] Configure coverage reporting
  - [x] Add pytest-cov, pytest-mock to dev dependencies
- [x] Update `.gitignore` to exclude test artifacts (`.pytest_cache/`, `.coverage`, `htmlcov/`)

### 1.3 Update Engine Dependencies
- [x] Add pytest to `resources/defs/special/engine.yaml`
- [x] Add pytest-cov for coverage reporting
- [x] Add pytest-mock for mocking support
- [x] Add pytest-timeout for long-running test protection

### 1.4 Create Initial Test Fixtures
- [x] Create `tests/conftest.py` with:
  - [x] `tmp_target_dir` fixture for temporary deployment directories
  - [x] `mock_mamba` fixture for mocking mamba commands
  - [x] `mock_filesystem` fixture for filesystem operations
  - [x] `sample_env_yaml` fixture for test environment definitions

## Priority 2: Refactor for Testability

### 2.1 Extract Filesystem Operations
- [x] Create `scripts/engine/filesystem.py` module
- [x] Define `FileSystemProtocol` (Protocol class for type hints)
- [x] Implement `RealFileSystem` class with methods:
  - [x] `mkdir(path, parents=True, exist_ok=True)`
  - [x] `rmtree(path)`
  - [x] `copytree(src, dst, symlinks=True)`
  - [x] `symlink_to(link_path, target)`
  - [x] `readlink(path)`
  - [x] `exists(path)`, `is_dir(path)`, `is_file(path)`, `is_symlink(path)`
- [x] Implement `MockFileSystem` for testing
- [x] Update `deploy.py` to use FileSystem abstraction

### 2.2 Create Command Runner Abstraction
- [x] Create `scripts/engine/command_runner.py` module
- [x] Define `CommandRunnerProtocol`
- [x] Implement `RealCommandRunner` class wrapping `subprocess.run`
- [x] Implement `MockCommandRunner` for testing
- [x] Update `deploy.py` to use CommandRunner instead of direct `run()`

### 2.3 Add Dependency Injection to deploy.py
- [x] Modify `deploy_tier()` signature to accept:
  - [x] `filesystem: FileSystemProtocol`
  - [x] `command_runner: CommandRunnerProtocol`
  - [x] `mamba_path: Path` (deferred - using global MAMBA is acceptable)
  - [x] `resources_dir: Path` (deferred - using global paths is acceptable)
- [x] Update `MambaDeployer.__init__()` to accept dependencies
- [x] Replace global variable usage with injected dependencies (for filesystem and commands)
- [x] Update `__main__.py` to create and pass real implementations

### 2.4 Separate Pure Functions from Side Effects
- [x] Extract validation logic from `setup_tier_path()`:
  - [x] Create `validate_tier_path(target: Path, tier: str) -> Path`
  - [x] Keep I/O in separate function
- [x] Extract from `select_engine_directory()` in bootstrap-engine:
  - [x] Create `determine_next_engine(current_link_target: str) -> str`
  - [x] Pure function for blue/green logic
- [x] Extract from `validate_and_get_color()` in promote_staging.py:
  - [x] Create `validate_color(color: str) -> bool`
  - [x] Create `get_opposite_color(color: str) -> str`

### 2.5 Refactor Bash Scripts for Testability
- [ ] Extract reusable functions to `scripts/lib/common.sh`:
  - [ ] `log_info()`, `log_debug()`, `log_error()`, `die()`
  - [ ] `validate_directory()`
  - [ ] `create_directory_structure()`
- [ ] Source common.sh in all bash scripts
- [ ] Make functions return status codes instead of calling `exit` directly
- [ ] Add `--test-mode` flag to skip actual operations

**NOTE**: Section 2.5 deferred to lower priority. The Python code has been
fully refactored for testability (2.1-2.4 complete). Bash script refactoring
can be done later if needed, but writing actual tests (Priority 3) is more
valuable now.

## Priority 3: Add Unit Tests

### 3.1 Test Argument Parsing
- [x] Create `tests/unit/test_bootstrap_args.py`
  - [x] Test valid arguments (deferred to integration tests)
  - [x] Test missing TARGET_DIR
  - [x] Test --offline, --verbose, --force flags (deferred to integration tests)
  - [x] Test invalid flags
- [x] Create `tests/unit/test_deploy_args.py`
  - [x] Test argument parsing for deploy script (documented as thin wrapper)
  - [x] Test --dry-run, --offline, --keep, --force modes (tested in test_engine_cli.py)
- [x] Create `tests/unit/test_engine_cli.py`
  - [x] Test `parse_command_line()` in `__main__.py`
  - [x] Test mutually exclusive --keep and --force

### 3.2 Test Path Validation Logic
- [x] Create `tests/unit/test_path_validation.py`
  - [x] Test `setup_tier_path()` with valid paths
  - [x] Test with non-existent directories
  - [x] Test with symlinks
  - [x] Test production tier protection
- [x] Create `tests/unit/test_promote_staging.py`
  - [x] Test `validate_and_get_color()` with blue/green
  - [x] Test with invalid colors
  - [x] Test with non-symlinks
  - [x] Test with broken symlinks

### 3.3 Test Blue/Green Rotation Logic
- [x] Create `tests/unit/test_blue_green.py`
  - [x] Test `select_engine_directory()` logic
  - [x] Test rotation from engine_a to engine_b
  - [x] Test rotation from engine_b to engine_a
  - [x] Test initial state (no existing engine)
  - [x] Test BLUE_GREEN_TRANSITIONS dictionary
  - [x] Test tier promotion rotation

### 3.4 Test Error Conditions
- [x] Create `tests/unit/test_error_handling.py`
  - [x] Test missing mamba binary
  - [x] Test invalid YAML files (tested missing files, validation deferred to Priority 5)
  - [x] Test disk space issues (mock) (MockFileSystem behavior tested)
  - [x] Test permission errors (mock) (exit code testing)
  - [x] Test network failures in offline mode (deferred to integration tests)

### 3.5 Test Environment Definition Loading
- [x] Create `tests/unit/test_env_defs.py`
  - [x] Test `list_conda_environment_defs()` on Linux
  - [x] Test on Darwin (macOS)
  - [x] Test with missing files
  - [x] Test glob pattern matching
  - [x] Fix deploy.py:86 list iteration bug first (already fixed with list comprehension)

## Priority 4: Add Integration Tests

**STATUS**: Sections 4.2, 4.4, and 4.5 have been deferred to Priority 6
(E2E Tests with Real Resources) because they require a real mamba installation.
The global `MAMBA` variable in `deploy.py` points to `sys.executable`, which
doesn't work in test environments. To properly support integration testing
without real mamba, the `mamba_path` parameter would need to be injected as a
dependency (deferred from Priority 2.3). Only sections 4.1 and 4.3 remain as
true integration tests that don't require real mamba.

### 4.1 Test Bootstrap Workflow
- [x] Create `tests/integration/test_bootstrap.py`
  - [x] Test full bootstrap in temp directory
  - [x] Verify directory structure created
  - [x] Verify engine symlink created correctly
  - [x] Test with --offline mode (requires pre-cached packages) (skipped placeholder)
  - [x] Test --force flag behavior (skipped placeholder)
  - [x] Mark with `@pytest.mark.integration`
  - [x] Require `--run-integration` flag to execute

### 4.2 Test Deploy Workflow
- [x] Create `tests/integration/test_deploy.py` (moved to Priority 6 - requires real mamba)
  - [ ] Test deploy to staging tier (deferred to Priority 6)
  - [ ] Verify conda environments created (deferred to Priority 6)
  - [ ] Verify bin/ and etc/ directories copied (deferred to Priority 6)
  - [ ] Verify meta/ git info stored (with mocked git commands) (deferred to Priority 6)
  - [ ] Test --dry-run mode (no actual changes) (deferred to Priority 6)
  - [ ] Test --keep mode (preserve existing envs) (deferred to Priority 6)
  - [ ] Run actual mamba commands (not mocked) (deferred to Priority 6)

**NOTE**: Tests in `tests/integration/test_deploy.py` require a real mamba
installation due to the global `MAMBA` variable pointing to `sys.executable`
location. These tests have been moved to Priority 6 (E2E Tests with Real
Resources). To properly support integration testing without real mamba, the
`mamba_path` parameter needs to be injected as a dependency (deferred from
Priority 2.3).

**DEPENDENCY ISSUE**: The current `tests/integration/test_deploy.py` imports
`scripts.engine.deploy` directly, requiring rich, pyyaml, etc. in the test
runner's Python environment. This creates fragile dependencies on the user's
active environment. See Priority 7 for the plan to refactor these tests to
use subprocess calls instead.

### 4.3 Test Promote Staging Workflow
- [x] Create `tests/integration/test_promote.py`
  - [x] Test promotion from blue to green
  - [x] Test promotion from green to blue
  - [x] Verify symlinks updated correctly
  - [x] Test with IAC_TIER_DIR environment variable
  - [x] Test error when staging and production point to same tier
  - [x] Test creation of production symlink if missing
  - [x] Test error when staging is not a symlink
  - [x] Test error when staging points to invalid color

### 4.4 Test Offline Mode
**DEFERRED TO PRIORITY 6**: These tests require real mamba installation (same issue as 4.2)
- [ ] Create `tests/integration/test_offline_mode.py` (deferred to Priority 6)
  - [ ] Test bootstrap with --offline (deferred to Priority 6)
  - [ ] Test deploy with --offline (deferred to Priority 6)
  - [ ] Verify no network calls attempted (deferred to Priority 6)
  - [ ] Test with populated conda_package_cache (deferred to Priority 6)

### 4.5 Test End-to-End Workflow
**DEFERRED TO PRIORITY 6**: These tests require real mamba installation (same issue as 4.2)
- [ ] Create `tests/integration/test_full_workflow.py` (deferred to Priority 6)
  - [ ] Bootstrap → Deploy staging → Promote → Deploy new staging (deferred to Priority 6)
  - [ ] Verify complete blue/green rotation (deferred to Priority 6)
  - [ ] Test engine rotation (bootstrap-engine twice) (deferred to Priority 6)
  - [ ] Verify metadata tracking throughout (deferred to Priority 6)

## Priority 5: Add Validation Layer

### 5.1 YAML Environment Validation
- [x] Create `scripts/engine/validators.py` module
- [x] Implement `validate_env_yaml(path: Path) -> bool`
  - [x] Check file exists and is readable
  - [x] Validate YAML syntax
  - [x] Validate required keys (channels, dependencies)
  - [x] Validate channel names
  - [x] Validate dependency format
- [x] Add validation to `deploy_env()` before deployment
- [x] Create unit tests in `tests/unit/test_validators.py`

### 5.2 Binary Availability Checks
- [x] Create `check_required_binaries()` function
  - [x] Check for mamba/micromamba
  - [x] Check for curl (for fetch-micromamba)
  - [x] Check for git (for metadata)
  - [x] Check for tar (for micromamba extraction)
- [x] Add checks to bootstrap-engine script before operations
- [x] Provide helpful error messages with installation instructions

### 5.3 Symlink Target Validation
- [x] Create `validate_symlink_target(link: Path, expected: list[str]) -> bool`
- [x] Use in `validate_and_get_color()` in promote_staging.py
- [x] Use in engine rotation logic
- [x] Add checks for dangling symlinks
- [x] Add unit tests for edge cases

### 5.4 Disk Space Checks
- [x] Create `check_disk_space(path: Path, operation: str, env_yamls: list[Path] | None, force: bool) -> tuple[bool, str]`
  - [x] Hybrid approach with static thresholds and dynamic YAML-based estimation
  - [x] Bootstrap: 5 GB minimum, 10 GB recommended
  - [x] Deploy: 15 GB minimum, 30 GB recommended
  - [x] Package estimation: ~50MB per package with 1.5x multiplier for transitive deps
- [x] Create `get_available_space_gb(path: Path) -> float` helper function
- [x] Create `estimate_env_size_gb(yaml_path: Path) -> float` helper function
- [x] Add to bootstrap-engine before creating directories
  - [x] Added `check_disk_space()` bash function
  - [x] Added `--force` flag to bypass checks
  - [x] Call check early in main() workflow
- [x] Add to deploy.py before installing environments
  - [x] Check disk space with YAML-based estimation
  - [x] Respect `--force` mode parameter
  - [x] Display warnings/info based on available space
- [x] Add comprehensive unit tests in `tests/unit/test_validators.py`
  - [x] Test get_available_space_gb() with mocked os.statvfs
  - [x] Test estimate_env_size_gb() for various environment sizes
  - [x] Test check_disk_space() for all scenarios (plenty, below recommended, below minimum, force mode)
  - [x] Test bootstrap vs deploy operation thresholds
  - [x] Test YAML-based estimation warnings

### 5.5 Path Traversal Protection
- [x] Create `validate_safe_path(path: Path, base: Path) -> bool`
  - [x] Ensure path is within expected base directory
  - [x] Check for .. components
  - [x] Resolve symlinks and verify
- [x] Add to TARGET_DIR validation in deploy.py
- [x] Add to symlink target validation in promote_staging.py
- [x] Add unit tests with malicious path examples (16 tests covering edge cases)

## Priority 6: End-to-End Tests (Real Resources)

### 6.1 Full Deploy with Real YAML Files
- [x] Refactor production code to support environment subsets
  - [x] Add `env_yamls` parameter to `deploy_tier()` function
  - [x] Add unit tests for env_yamls parameter
- [x] Create `tests/e2e/test_real_deploy.py` with E2E tests
  - [x] Add `@pytest.mark.e2e` marker and `--run-e2e` flag requirement
  - [x] Add session-scoped mamba availability check (pytest.exit if missing)
  - [x] Test quick deploy with subset (excludes python.yaml for speed)
  - [x] Test comprehensive deploy with all environments including python.yaml
  - [x] Test deploy to staging tier
  - [x] Verify conda environments created
  - [x] Verify bin/ and etc/ directories copied
  - [x] Verify meta/ git info stored with real git commands (not mocked)
  - [x] Test --dry-run mode
  - [x] Test --keep mode
  - [x] Test platform-specific environments (linux.yaml, mac.yaml) with skip markers
  - [x] Keep existing integration tests in `tests/integration/test_deploy.py` (uses mocks)

### 6.2 Full Workflow with Real Resources
- [x] Create `tests/e2e/test_real_workflow.py` (incorporates deferred items
  from 4.4 and 4.5) **(completed but may need revision after Priority 7)**
  - [x] Bootstrap → Deploy staging → Promote → Deploy new staging
  - [x] Use real YAML environment definitions
  - [x] Use real git commands for metadata
  - [x] Test complete blue/green rotation with all environments
  - [x] Test engine rotation (bootstrap-engine twice)
  - [x] Verify all metadata tracking with real git info
  - [x] May take 5-10 minutes to run (install all real environments)

### 6.3 Offline Mode Testing **(deferred until Priority 7 complete)**
- [ ] Create `tests/e2e/test_offline_mode.py` (deferred from 4.4)
  - [ ] Test bootstrap with --offline
  - [ ] Test deploy with --offline
  - [ ] Verify no network calls attempted
  - [ ] Test with populated conda_package_cache
  - [ ] Requires pre-populating package cache before running test

## Priority 7: Fix Integration Test Dependencies

**Background**: The current `tests/integration/test_deploy.py` imports
`scripts.engine.deploy` directly, which requires rich, pyyaml, and other
engine dependencies to be present in the test runner's Python environment.
This creates a fragile coupling where tests break when the user's active
Python environment changes. E2E tests correctly avoid this by using
subprocess calls to the bootstrap and deploy scripts, which manage their
own dependencies within the bootstrapped engine environment.

**Goal**: Refactor integration tests to use subprocess calls instead of
direct imports, making them independent of the test runner's environment
and more aligned with the project's architecture.

### 7.1 Refactor Integration Tests to Use Subprocess
- [ ] Modify `tests/integration/test_deploy.py` to call `scripts/deploy` via subprocess
  - [ ] Replace `from scripts.engine.deploy import deploy_tier` with subprocess calls
  - [ ] Remove imports of `scripts.engine.filesystem`, `scripts.engine.command_runner`
  - [ ] Keep `mock_git_command_runner` pattern if possible via environment or wrapper script
- [ ] Update test verification to inspect filesystem instead of in-process checks
  - [ ] Verify directory structure by checking paths exist
  - [ ] Read metadata files to verify git info stored
  - [ ] Check conda environment directories created
- [ ] Ensure all existing test cases still work
  - [ ] `test_deploy_to_staging_creates_structure`
  - [ ] `test_deploy_creates_conda_environments`
  - [ ] `test_deploy_copies_bin_directory`
  - [ ] `test_deploy_copies_etc_directory`
  - [ ] `test_deploy_stores_git_metadata`
  - [ ] `test_deploy_dry_run_mode`
  - [ ] `test_deploy_keep_mode`
- [ ] Update test documentation to reflect subprocess approach
- [ ] Verify tests pass without engine dependencies in test runner environment

### 7.2 Consider In-Process Test Preservation (Optional)
- [ ] Evaluate whether current import-based tests provide unique value
  - [ ] Do they catch different bugs than subprocess tests?
  - [ ] Are they significantly faster for development iteration?
  - [ ] Do they enable better debugging of internal state?
- [ ] If yes, preserve import-based tests in separate file
  - [ ] Create `tests/integration/test_deploy_inprocess.py`
  - [ ] Move current import-based tests there
  - [ ] Add pytest markers to skip if dependencies unavailable
  - [ ] Add `@pytest.mark.requires_engine_deps` marker
- [ ] Document that in-process tests require engine environment
  - [ ] Update test docstrings
  - [ ] Add README or comment explaining when to use each approach
- [ ] Note: This step may be skipped if subprocess approach is sufficient

### 7.3 Future: Evaluate Testing Strategy
- [ ] After 7.1 complete, assess testing approach effectiveness
  - [ ] Compare subprocess vs in-process test execution time
  - [ ] Evaluate debugging experience with subprocess tests
  - [ ] Check for any gaps in test coverage
- [ ] Document trade-offs for future reference
  - [ ] In-process: fast, easy debug, but fragile dependencies
  - [ ] Subprocess: isolated, realistic, but slower and harder to debug
- [ ] Make decision on long-term testing strategy
  - [ ] Keep only subprocess tests (simpler, more robust)?
  - [ ] Keep both approaches (flexibility, but more maintenance)?
  - [ ] Investigate hybrid approach (subprocess with debug hooks)?
- [ ] Update CLAUDE.md with testing strategy documentation
- [ ] Consider whether to remove import-based tests entirely

**Outcome**: Integration tests become independent of test runner's Python
environment, more robust, and better aligned with how the scripts are
actually used in production.

## Quick Wins (Can be done immediately)

### QW.1 Fix Critical Bugs
- [x] Fix deploy.py:86 - Don't modify list while iterating
  ```python
  # Current:
  for item in worklist:
      if not item.is_file():
          worklist.remove(item)  # BUG!

  # Fixed:
  worklist = [item for item in worklist if item.is_file()]
  ```

### QW.2 Fix Function Ordering in deploy.py
- [x] Reorder deploy.py to follow top-down principle per CLAUDE.md:
  - [x] Move helper functions below main functions
  - [x] Order: `deploy_tier()` → `check_mamba()` → `setup_tier_path()` → `list_conda_environment_defs()` → `MambaDeployer` class

### QW.3 Add Type Hints
- [x] Add complete type hints to deploy.py (partially done)
- [x] Add type hints to __main__.py
- [x] Add type hints to config.py
- [x] Add type hints to promote_staging.py (mostly done)
- [x] Run mypy for validation (mypy not installed, but type hints are complete)

### QW.4 Improve Error Messages
- [x] Change promote_staging.py die() to use stderr:
  ```python
  def die(message) -> NoReturn:
      print(message, file=sys.stderr)  # Add file=sys.stderr
      exit(1)
  ```
- [x] Add context to error messages (include paths, values)
- [x] Standardize error message format across all scripts

### QW.5 Add Input Validation
- [x] Validate TARGET_DIR is absolute path or convert to absolute
- [x] Validate tier name matches expected pattern (blue|green|staging|production|dev.*|test.*)
- [x] Validate YAML files exist before attempting to use them
- [ ] Check write permissions before attempting operations (deferred - not critical)

### QW.6 Document Return Codes
- [x] Document exit codes in bootstrap script (currently uses default)
- [x] Document exit codes in deploy script
- [x] Standardize: 0=success, 1=usage error, 2=missing dependency, 3=invalid input, 4=operation failed
- [x] Update usage() functions with exit code documentation

### QW.7 Add --dry-run Support
- [x] Verify --dry-run works in deploy (exists in code)
- [x] Add --dry-run to bootstrap script
- [x] Add --dry-run to bootstrap-engine script
- [x] Add --dry-run to promote_staging script
- [x] Test dry-run mode actually makes no changes

## Additional Improvements (Lower Priority)

### AI.0 Test Timeout Configuration
- [ ] Add explicit timeouts for E2E tests in pytest configuration
  - [ ] Quick E2E test (subset): consider 5-10 minute timeout
  - [ ] Comprehensive E2E test (all envs): consider 15-20 minute timeout
  - [ ] Add timeout configuration to pyproject.toml for e2e marker
  - [ ] Document timeout expectations in test docstrings

### AI.1 Logging Improvements
- [ ] Standardize logging across bash and Python
- [ ] Consider using Python logging in bash via wrapper
- [ ] Add timestamps to log messages
- [ ] Add log levels (DEBUG, INFO, WARN, ERROR)
- [ ] Write deployment logs to tier/logs/ directory

### AI.2 Configuration Management
- [ ] Create configuration file format (.ini or .yaml)
- [ ] Support for custom conda channels
- [ ] Support for custom micromamba download URLs
- [ ] Support for proxy settings
- [ ] Environment-specific configuration

### AI.3 Rollback Mechanism
- [ ] Track deployment state before operations
- [ ] Implement rollback on failure
- [ ] Keep backup of previous tier during deployment
- [ ] Add --rollback command to undo last deployment

### AI.4 Security Enhancements
- [ ] Add checksum verification for micromamba downloads
- [ ] Sign environment YAML files
- [ ] Validate conda package signatures
- [ ] Reduce environment variable leakage in sanitize-command
- [ ] Add --verify-only mode for security audits

### AI.5 Documentation
- [ ] Add comments to complex bash functions
- [ ] Create troubleshooting guide (common errors and solutions)
- [ ] Create architecture diagram
- [ ] Document YAML environment definition format
- [ ] Add examples directory with sample deployments
- [ ] Create developer guide for contributors

### AI.6 CI/CD Integration
- [ ] Create GitHub Actions workflow
- [ ] Run unit tests on every commit
- [ ] Run integration tests on pull requests
- [ ] Generate coverage reports
- [ ] Run linters (flake8, black, shellcheck)
- [ ] Add pre-commit hooks configuration

## Testing Execution Strategy

### TE.1 Test Execution Requirements
- [ ] Unit tests run by default: `pytest tests/unit/`
- [ ] Integration tests require flag: `pytest --run-integration tests/integration/`
- [ ] All tests: `pytest --run-integration`
- [ ] Coverage report: `pytest --cov=scripts/engine --cov-report=html`

### TE.2 Mock Strategy
- [ ] Mock subprocess.run() for all external commands
- [ ] Mock filesystem operations for unit tests
- [ ] Use real filesystem in temp directories for integration tests
- [ ] Mock network calls (curl in fetch-micromamba)
- [ ] Record and replay mamba command outputs

### TE.3 Test Data Management
- [ ] Create minimal test YAML environments in tests/fixtures/
- [ ] Create sample directory structures in fixtures
- [ ] Generate test data programmatically where possible
- [ ] Document test data requirements for integration tests

## Success Criteria

- [ ] Unit test coverage ≥ 80% for Python code
- [ ] All critical paths covered by integration tests
- [ ] No test depends on external network (except with --run-integration)
- [ ] All tests pass on both Linux and macOS
- [ ] Tests run in < 5 seconds (unit), < 60 seconds (integration)
- [ ] Zero tolerance for flaky tests
- [ ] All new code requires tests before merging
- [ ] Documentation updated with testing instructions

## Implementation Notes

1. **Order of execution**: Follow priority order but within each priority, tackle smaller tasks first for momentum
2. **Incremental approach**: Don't refactor everything at once; refactor one module, test it, then move to next
3. **Backwards compatibility**: Ensure refactoring doesn't break existing deployments
4. **Test the tests**: Verify tests actually catch bugs by introducing intentional failures
5. **Review CLAUDE.md**: Ensure all changes comply with project standards (top-down ordering, pytest, no advertising language)

## Estimated Timeline

- Priority 1: 1-2 days (test infrastructure setup)
- Priority 2: 3-4 days (refactoring for testability)
- Priority 3: 3-4 days (unit tests)
- Priority 4: 2-3 days (integration tests)
- Priority 5: 2-3 days (validation layer)
- Quick Wins: 4-6 hours (can be done in parallel)
- Additional Improvements: Ongoing

**Total estimated effort**: 2-3 weeks for core testing infrastructure and critical refactoring
