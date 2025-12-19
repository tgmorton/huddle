"""Tests for the game prep bonus system."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from huddle.core.game_prep import (
    MAX_PREP_REPS,
    MAX_SCHEME_BONUS,
    MAX_EXECUTION_BONUS,
    GamePrepBonus,
    calculate_prep_level,
    create_game_prep,
    apply_prep_bonus,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def opponent_id() -> uuid4:
    """Create a sample opponent ID."""
    return uuid4()


@pytest.fixture
def basic_prep(opponent_id) -> GamePrepBonus:
    """Create a basic game prep bonus at 50%."""
    return GamePrepBonus(
        opponent_id=opponent_id,
        opponent_name="Dallas Cowboys",
        prep_level=0.5,
        week=5,
    )


@pytest.fixture
def full_prep(opponent_id) -> GamePrepBonus:
    """Create a fully prepared game prep bonus."""
    return GamePrepBonus(
        opponent_id=opponent_id,
        opponent_name="New York Giants",
        prep_level=1.0,
        week=8,
    )


# =============================================================================
# Calculate Prep Level Tests
# =============================================================================

class TestCalculatePrepLevel:
    """Test prep level calculation from reps."""

    def test_zero_reps_zero_prep(self):
        """No reps = no prep."""
        level = calculate_prep_level(0)
        assert level == 0.0

    def test_max_reps_full_prep(self):
        """Max reps = 100% prep."""
        level = calculate_prep_level(MAX_PREP_REPS)
        assert level == 1.0

    def test_half_reps_half_prep(self):
        """Half reps = 50% prep."""
        level = calculate_prep_level(MAX_PREP_REPS // 2)
        assert level == pytest.approx(0.5, rel=0.05)

    def test_exceeds_max_capped(self):
        """Reps beyond max still cap at 100%."""
        level = calculate_prep_level(MAX_PREP_REPS * 2)
        assert level == 1.0


# =============================================================================
# GamePrepBonus Tests
# =============================================================================

class TestGamePrepBonus:
    """Test GamePrepBonus dataclass."""

    def test_bonuses_calculated_on_init(self, opponent_id):
        """Bonuses are calculated from prep_level on creation."""
        bonus = GamePrepBonus(
            opponent_id=opponent_id,
            opponent_name="Test",
            prep_level=1.0,
            week=1,
        )

        assert bonus.scheme_recognition == MAX_SCHEME_BONUS
        assert bonus.execution_bonus == MAX_EXECUTION_BONUS

    def test_half_prep_half_bonus(self, basic_prep):
        """50% prep = 50% of max bonuses."""
        assert basic_prep.scheme_recognition == pytest.approx(MAX_SCHEME_BONUS * 0.5, rel=0.01)
        assert basic_prep.execution_bonus == pytest.approx(MAX_EXECUTION_BONUS * 0.5, rel=0.01)

    def test_get_total_bonus_no_prep(self, opponent_id):
        """Zero prep = 1.0 multiplier (no bonus)."""
        bonus = GamePrepBonus(
            opponent_id=opponent_id,
            opponent_name="Test",
            prep_level=0.0,
            week=1,
        )

        assert bonus.get_total_bonus() == 1.0

    def test_get_total_bonus_full_prep(self, full_prep):
        """Full prep = combined bonus."""
        total = full_prep.get_total_bonus()

        # (0.10 + 0.05) / 2 = 0.075 bonus
        expected = 1.0 + (MAX_SCHEME_BONUS + MAX_EXECUTION_BONUS) / 2
        assert total == pytest.approx(expected, rel=0.01)

    def test_get_scheme_multiplier(self, full_prep):
        """Scheme multiplier at full prep."""
        mult = full_prep.get_scheme_multiplier()
        assert mult == 1.0 + MAX_SCHEME_BONUS

    def test_get_execution_multiplier(self, full_prep):
        """Execution multiplier at full prep."""
        mult = full_prep.get_execution_multiplier()
        assert mult == 1.0 + MAX_EXECUTION_BONUS


# =============================================================================
# Add Prep Tests
# =============================================================================

class TestAddPrep:
    """Test adding more preparation."""

    def test_add_prep_increases_level(self, basic_prep):
        """Adding prep increases prep level."""
        initial = basic_prep.prep_level
        basic_prep.add_prep(0.3)

        assert basic_prep.prep_level > initial

    def test_add_prep_diminishing_returns(self, basic_prep):
        """Adding prep has diminishing returns."""
        # At 50%, adding 50% shouldn't get to 100%
        basic_prep.add_prep(0.5)

        # remaining = 0.5, gain = 0.5 * 0.5 = 0.25
        # new level = 0.5 + 0.25 = 0.75
        assert basic_prep.prep_level == pytest.approx(0.75, rel=0.01)

    def test_add_prep_capped_at_one(self, basic_prep):
        """Prep level can't exceed 1.0."""
        basic_prep.add_prep(1.0)
        basic_prep.add_prep(1.0)
        basic_prep.add_prep(1.0)

        assert basic_prep.prep_level <= 1.0

    def test_add_prep_updates_bonuses(self, basic_prep):
        """Adding prep recalculates bonuses."""
        initial_scheme = basic_prep.scheme_recognition
        basic_prep.add_prep(0.3)

        assert basic_prep.scheme_recognition > initial_scheme


# =============================================================================
# Expiration Tests
# =============================================================================

class TestExpiration:
    """Test game prep expiration."""

    def test_not_expired_same_week(self, basic_prep):
        """Prep for current week is not expired."""
        assert basic_prep.is_expired(basic_prep.week) is False

    def test_not_expired_earlier_week(self, basic_prep):
        """Prep for future week is not expired."""
        assert basic_prep.is_expired(basic_prep.week - 1) is False

    def test_expired_later_week(self, basic_prep):
        """Prep expires after game week passes."""
        assert basic_prep.is_expired(basic_prep.week + 1) is True

    def test_expired_much_later(self, basic_prep):
        """Prep definitely expired many weeks later."""
        assert basic_prep.is_expired(basic_prep.week + 10) is True


# =============================================================================
# Opponent Validation Tests
# =============================================================================

class TestOpponentValidation:
    """Test opponent matching."""

    def test_valid_for_correct_opponent(self, basic_prep, opponent_id):
        """Prep is valid for the prepped opponent."""
        assert basic_prep.is_valid_for_opponent(opponent_id) is True

    def test_invalid_for_wrong_opponent(self, basic_prep):
        """Prep is not valid for a different opponent."""
        wrong_opponent = uuid4()
        assert basic_prep.is_valid_for_opponent(wrong_opponent) is False


# =============================================================================
# Create Game Prep Tests
# =============================================================================

class TestCreateGamePrep:
    """Test create_game_prep helper."""

    def test_creates_with_correct_level(self, opponent_id):
        """Creates prep with calculated level."""
        prep = create_game_prep(
            opponent_id=opponent_id,
            opponent_name="Test Team",
            week=10,
            reps=20,  # Half of max
        )

        assert prep.opponent_id == opponent_id
        assert prep.opponent_name == "Test Team"
        assert prep.week == 10
        assert prep.prep_level == pytest.approx(0.5, rel=0.05)


# =============================================================================
# Apply Prep Bonus Tests
# =============================================================================

class TestApplyPrepBonus:
    """Test apply_prep_bonus helper."""

    def test_creates_new_if_none(self, opponent_id):
        """Creates new prep if none exists."""
        result = apply_prep_bonus(
            existing=None,
            opponent_id=opponent_id,
            opponent_name="New Opponent",
            week=5,
            reps=20,
        )

        assert result is not None
        assert result.opponent_id == opponent_id
        assert result.week == 5

    def test_adds_to_existing_same_week(self, basic_prep, opponent_id):
        """Adds to existing prep for same week."""
        initial_level = basic_prep.prep_level

        result = apply_prep_bonus(
            existing=basic_prep,
            opponent_id=opponent_id,
            opponent_name="Dallas Cowboys",
            week=basic_prep.week,  # Same week
            reps=20,
        )

        assert result.prep_level > initial_level
        assert result is basic_prep  # Same object

    def test_replaces_for_different_week(self, basic_prep, opponent_id):
        """Creates new prep for different week."""
        new_week = basic_prep.week + 1

        result = apply_prep_bonus(
            existing=basic_prep,
            opponent_id=opponent_id,
            opponent_name="New Opponent",
            week=new_week,
            reps=20,
        )

        assert result.week == new_week
        assert result is not basic_prep  # New object


# =============================================================================
# Serialization Tests
# =============================================================================

class TestSerialization:
    """Test to_dict and from_dict."""

    def test_to_dict(self, full_prep):
        """Test conversion to dictionary."""
        data = full_prep.to_dict()

        assert data["opponent_name"] == "New York Giants"
        assert data["prep_level"] == 1.0
        assert data["week"] == 8
        assert data["scheme_recognition"] == MAX_SCHEME_BONUS
        assert data["execution_bonus"] == MAX_EXECUTION_BONUS

    def test_from_dict(self, full_prep):
        """Test restoration from dictionary."""
        data = full_prep.to_dict()
        restored = GamePrepBonus.from_dict(data)

        assert restored.opponent_name == full_prep.opponent_name
        assert restored.prep_level == full_prep.prep_level
        assert restored.week == full_prep.week
        assert restored.scheme_recognition == full_prep.scheme_recognition
        assert restored.execution_bonus == full_prep.execution_bonus

    def test_round_trip(self, basic_prep):
        """Test full serialization round trip."""
        data = basic_prep.to_dict()
        restored = GamePrepBonus.from_dict(data)

        assert restored.get_total_bonus() == basic_prep.get_total_bonus()
        assert restored.is_expired(basic_prep.week) == basic_prep.is_expired(basic_prep.week)
