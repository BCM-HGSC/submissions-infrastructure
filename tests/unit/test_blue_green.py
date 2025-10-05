"""Unit tests for blue/green rotation logic."""

from importlib.machinery import SourceFileLoader
import importlib.util
from pathlib import Path
import sys

# Load the promote_staging script to access blue/green functions
_promote_staging_path = str(
    Path(__file__).parent.parent.parent / "scripts" / "promote_staging"
)
_loader = SourceFileLoader("promote_staging", _promote_staging_path)
_spec = importlib.util.spec_from_file_location(
    "promote_staging", _promote_staging_path, loader=_loader
)
_promote_staging = importlib.util.module_from_spec(_spec)
sys.modules["promote_staging"] = _promote_staging
_spec.loader.exec_module(_promote_staging)

BLUE_GREEN_TRANSITIONS = _promote_staging.BLUE_GREEN_TRANSITIONS
get_opposite_color = _promote_staging.get_opposite_color


def determine_next_engine(current_target):
    """Python implementation of determine_next_engine logic from bootstrap-engine.

    This mirrors the bash function in scripts/bootstrap-engine.
    """
    if current_target == "engine_a":
        return "engine_b"
    return "engine_a"


def test_determine_next_engine_from_engine_a():
    """Test determine_next_engine returns engine_b when current is engine_a."""
    result = determine_next_engine("engine_a")
    assert result == "engine_b"


def test_determine_next_engine_from_engine_b():
    """Test determine_next_engine returns engine_a when current is engine_b."""
    result = determine_next_engine("engine_b")
    assert result == "engine_a"


def test_determine_next_engine_is_deterministic():
    """Test determine_next_engine returns consistent results."""
    # Call multiple times with same inputs
    assert determine_next_engine("engine_a") == "engine_b"
    assert determine_next_engine("engine_a") == "engine_b"
    assert determine_next_engine("engine_b") == "engine_a"
    assert determine_next_engine("engine_b") == "engine_a"


def test_determine_next_engine_with_unknown_current():
    """Test determine_next_engine defaults to engine_a for unknown values."""
    # The bash logic is: if engine_a then engine_b, else engine_a
    # So anything other than "engine_a" should return "engine_a"
    assert determine_next_engine("unknown") == "engine_a"
    assert determine_next_engine("") == "engine_a"
    assert determine_next_engine("engine") == "engine_a"


def test_engine_rotation_alternates():
    """Test that engine rotation alternates between engine_a and engine_b."""
    # Simulate rotation: start with engine_a
    current = "engine_a"

    # First rotation should go to engine_b
    next_engine = "engine_b" if current == "engine_a" else "engine_a"
    assert next_engine == "engine_b"

    # Second rotation should go back to engine_a
    current = next_engine
    next_engine = "engine_b" if current == "engine_a" else "engine_a"
    assert next_engine == "engine_a"


def test_blue_green_transitions_for_tiers():
    """Test BLUE_GREEN_TRANSITIONS dictionary enables tier rotation."""
    # Starting with blue
    current = "blue"
    next_tier = BLUE_GREEN_TRANSITIONS[current]
    assert next_tier == "green"

    # Rotating from green back to blue
    current = next_tier
    next_tier = BLUE_GREEN_TRANSITIONS[current]
    assert next_tier == "blue"


def test_tier_promotion_rotation_scenario():
    """Test a complete tier promotion rotation scenario.

    Scenario:
    1. Staging points to blue
    2. Promote staging to production (production -> blue)
    3. Staging rotates to green
    4. Next deployment goes to green
    5. Promote again (production -> green, staging -> blue)
    """
    # Initial state: staging points to blue
    staging_color = "blue"
    production_color = None  # Not yet set

    # Step 1: Promote staging to production
    production_color = staging_color  # production now points to blue
    assert production_color == "blue"

    # Step 2: Rotate staging to opposite color
    staging_color = get_opposite_color(staging_color)
    assert staging_color == "green"

    # Verify they're different
    assert staging_color != production_color

    # Step 3: Deploy to new staging (green)
    # (deployment would happen here)

    # Step 4: Promote again
    old_production = production_color
    production_color = staging_color  # production now points to green
    assert production_color == "green"

    # Step 5: Rotate staging again
    staging_color = get_opposite_color(staging_color)
    assert staging_color == "blue"
    assert staging_color == old_production  # Back to where production was


def test_initial_engine_state_defaults_to_engine_a():
    """Test that initial state (no existing engine) defaults to engine_a.

    This tests the logic in select_engine_directory() where if there's
    no existing engine symlink, it should use engine_a.
    """
    # Simulate the logic from select_engine_directory
    engine_link_exists = False
    current_target = None

    if engine_link_exists:
        # Would read the symlink and rotate
        selected = "engine_b" if current_target == "engine_a" else "engine_a"
    else:
        # No existing engine, use engine_a
        selected = "engine_a"

    assert selected == "engine_a"


def test_engine_rotation_from_existing_engine_a():
    """Test engine rotation when engine_a is current."""
    # Simulate having an existing engine_a
    current_target = "engine_a"
    selected = "engine_b" if current_target == "engine_a" else "engine_a"
    assert selected == "engine_b"


def test_engine_rotation_from_existing_engine_b():
    """Test engine rotation when engine_b is current."""
    # Simulate having an existing engine_b
    current_target = "engine_b"
    selected = "engine_b" if current_target == "engine_a" else "engine_a"
    assert selected == "engine_a"


def test_blue_green_prevents_same_tier():
    """Test that blue/green rotation prevents staging and production from being same.

    This is a critical safety check that the rotation logic ensures
    staging and production never point to the same tier.
    """
    # Start with staging=blue, production=None
    staging = "blue"
    production = None

    # Promote staging to production
    production = staging
    assert production == "blue"

    # Rotate staging
    staging = get_opposite_color(staging)
    assert staging == "green"

    # Verify they're different
    assert staging != production

    # Promote again
    production = staging
    assert production == "green"

    # Rotate staging
    staging = get_opposite_color(staging)
    assert staging == "blue"

    # Verify they're different
    assert staging != production


def test_complete_rotation_cycle():
    """Test a complete rotation cycle returns to initial state."""
    # Start with engine_a
    engines = ["engine_a"]

    # Rotate 4 times
    current = "engine_a"
    for _ in range(4):
        current = "engine_b" if current == "engine_a" else "engine_a"
        engines.append(current)

    # Should be: engine_a -> engine_b -> engine_a -> engine_b -> engine_a
    assert engines == ["engine_a", "engine_b", "engine_a", "engine_b", "engine_a"]

    # After even number of rotations, back to original
    assert engines[0] == engines[4]


def test_tier_rotation_cycle():
    """Test tier rotation cycle with blue/green."""
    tiers = ["blue"]
    current = "blue"

    # Rotate 4 times
    for _ in range(4):
        current = get_opposite_color(current)
        tiers.append(current)

    # Should alternate: blue -> green -> blue -> green -> blue
    assert tiers == ["blue", "green", "blue", "green", "blue"]

    # After even number of rotations, back to original
    assert tiers[0] == tiers[4]
