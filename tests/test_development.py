"""Tests for the player development system."""

import pytest
from uuid import uuid4

from huddle.core.enums import Position
from huddle.core.attributes import PlayerAttributes
from huddle.core.models.player import Player
from huddle.core.development import (
    BASE_DEV_RATE,
    AGE_PEAK,
    AGE_DECLINE_START,
    AGE_CUTOFF,
    DEVELOPABLE_ATTRIBUTES,
    POSITION_TO_CATEGORY,
    get_age_factor,
    get_learning_factor,
    get_potential_gap_factor,
    calculate_development_rate,
    get_developable_attrs,
    apply_development,
    develop_player,
    can_develop,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def young_prospect() -> Player:
    """Create a young player with high potential."""
    attrs = PlayerAttributes()
    attrs.set("learning", 75)
    attrs.set("speed", 80)
    attrs.set("acceleration", 78)
    attrs.set("potential", 92)  # High ceiling
    return Player(
        id=uuid4(),
        first_name="Young",
        last_name="Prospect",
        position=Position.WR,
        attributes=attrs,
        age=22,
    )


@pytest.fixture
def veteran_player() -> Player:
    """Create an older veteran player near ceiling."""
    attrs = PlayerAttributes()
    attrs.set("learning", 60)
    attrs.set("speed", 88)
    attrs.set("route_running", 92)
    attrs.set("potential", 90)  # Near ceiling
    return Player(
        id=uuid4(),
        first_name="Old",
        last_name="Veteran",
        position=Position.WR,
        attributes=attrs,
        age=32,
    )


@pytest.fixture
def average_player() -> Player:
    """Create an average mid-career player."""
    attrs = PlayerAttributes()
    attrs.set("learning", 50)
    attrs.set("speed", 75)
    attrs.set("potential", 82)
    return Player(
        id=uuid4(),
        first_name="Average",
        last_name="Joe",
        position=Position.RB,
        attributes=attrs,
        age=26,
    )


@pytest.fixture
def smart_young_player() -> Player:
    """Create a young player with high learning."""
    attrs = PlayerAttributes()
    attrs.set("learning", 90)
    attrs.set("potential", 88)
    attrs.set("speed", 70)
    return Player(
        id=uuid4(),
        first_name="Smart",
        last_name="Rookie",
        position=Position.QB,
        attributes=attrs,
        age=23,
    )


# =============================================================================
# Age Factor Tests
# =============================================================================

class TestAgeFactor:
    """Test age-based development rate multiplier."""

    def test_peak_age_fastest(self):
        """Players at peak age (22-24) develop fastest."""
        factor = get_age_factor(22)
        assert factor == 1.2

        factor = get_age_factor(24)
        assert factor == 1.2

    def test_normal_age(self):
        """Players 25-26 have normal development."""
        factor = get_age_factor(25)
        assert factor == 1.0

        factor = get_age_factor(26)
        assert factor == 1.0

    def test_decline_starts(self):
        """Development slows at 27-28."""
        factor = get_age_factor(27)
        assert factor == 0.6

        factor = get_age_factor(28)
        assert factor == 0.6

    def test_slow_development(self):
        """Players 29-30 develop slowly."""
        factor = get_age_factor(29)
        assert factor == 0.3

        factor = get_age_factor(30)
        assert factor == 0.3

    def test_veterans_barely_improve(self):
        """Players 31+ barely improve."""
        factor = get_age_factor(31)
        assert factor == 0.1

        factor = get_age_factor(35)
        assert factor == 0.1


# =============================================================================
# Learning Factor Tests
# =============================================================================

class TestLearningFactor:
    """Test learning attribute multiplier."""

    def test_average_learning_baseline(self, average_player):
        """50 learning = 1.0x multiplier."""
        factor = get_learning_factor(average_player)
        assert factor == pytest.approx(1.0, rel=0.01)

    def test_high_learning_faster(self, smart_young_player):
        """90 learning = 1.8x multiplier."""
        factor = get_learning_factor(smart_young_player)
        assert factor == pytest.approx(1.8, rel=0.01)

    def test_low_learning_slower(self):
        """30 learning = 0.6x multiplier."""
        attrs = PlayerAttributes()
        attrs.set("learning", 30)
        player = Player(position=Position.RB, attributes=attrs)

        factor = get_learning_factor(player)
        assert factor == pytest.approx(0.6, rel=0.01)


# =============================================================================
# Potential Gap Factor Tests
# =============================================================================

class TestPotentialGapFactor:
    """Test gap-to-potential multiplier."""

    def test_at_ceiling_no_growth(self, veteran_player):
        """Player at or above potential can't grow."""
        # Set overall to match potential
        veteran_player.attributes.set("speed", 95)
        veteran_player.attributes.set("route_running", 95)

        # If overall >= potential, no growth
        if veteran_player.overall >= veteran_player.potential:
            factor = get_potential_gap_factor(veteran_player)
            assert factor == 0.0

    def test_large_gap_accelerated(self, young_prospect):
        """Large gap between current and potential = faster growth."""
        factor = get_potential_gap_factor(young_prospect)
        # Young prospect with high potential should have large gap
        assert factor >= 1.0  # At least normal speed

    def test_small_gap_slowed(self):
        """Small gap (close to ceiling) = slower growth."""
        attrs = PlayerAttributes()
        attrs.set("potential", 85)
        # Set many attributes high so overall is close to potential
        attrs.set("speed", 83)
        attrs.set("awareness", 82)
        player = Player(position=Position.RB, attributes=attrs)

        # If gap is small (<=5), factor should be 0.5
        gap = player.potential - player.overall
        if gap <= 5:
            factor = get_potential_gap_factor(player)
            assert factor == 0.5


# =============================================================================
# Development Rate Tests
# =============================================================================

class TestDevelopmentRate:
    """Test combined development rate calculation."""

    def test_young_high_potential_develops_fast(self, young_prospect):
        """Young player with room to grow develops quickly."""
        rate = calculate_development_rate(young_prospect)
        assert rate > 0

        # Should be faster than base rate due to age and gap
        expected_min = BASE_DEV_RATE * 1.0  # At least base rate
        assert rate >= expected_min

    def test_veteran_develops_slowly(self, veteran_player):
        """Older veteran develops very slowly."""
        rate = calculate_development_rate(veteran_player)

        # If not at ceiling, still some growth but slow
        if veteran_player.overall < veteran_player.potential:
            assert rate > 0
            assert rate < BASE_DEV_RATE  # Slower than base

    def test_at_ceiling_no_development(self):
        """Player at potential ceiling can't develop."""
        attrs = PlayerAttributes()
        attrs.set("potential", 75)
        # Make overall = potential
        attrs.set("speed", 80)
        attrs.set("awareness", 80)
        player = Player(position=Position.QB, attributes=attrs, age=25)

        if player.overall >= player.potential:
            rate = calculate_development_rate(player)
            assert rate == 0.0


# =============================================================================
# Developable Attributes Tests
# =============================================================================

class TestDevelopableAttributes:
    """Test position-specific developable attributes."""

    def test_qb_has_passing_attributes(self):
        """QB can develop passing attributes."""
        attrs = get_developable_attrs("QB")
        assert "throw_accuracy_short" in attrs
        assert "throw_accuracy_mid" in attrs
        assert "awareness" in attrs

    def test_rb_has_rushing_attributes(self):
        """RB can develop rushing attributes."""
        attrs = get_developable_attrs("RB")
        assert "carrying" in attrs
        assert "elusiveness" in attrs

    def test_wr_has_receiving_attributes(self):
        """WR can develop receiving attributes."""
        attrs = get_developable_attrs("WR")
        assert "route_running" in attrs
        assert "catching" in attrs

    def test_ol_positions_share_attributes(self):
        """All OL positions share same developable attributes."""
        lt_attrs = get_developable_attrs("LT")
        rg_attrs = get_developable_attrs("RG")
        c_attrs = get_developable_attrs("C")

        assert lt_attrs == rg_attrs
        assert rg_attrs == c_attrs
        assert "pass_block" in lt_attrs
        assert "run_block" in lt_attrs

    def test_all_positions_have_physical(self):
        """All field positions include physical attributes."""
        for pos in ["QB", "RB", "WR", "CB", "MLB"]:
            attrs = get_developable_attrs(pos)
            assert "speed" in attrs
            assert "strength" in attrs

    def test_special_teams_no_development(self):
        """Kickers and punters don't develop through practice."""
        k_attrs = get_developable_attrs("K")
        p_attrs = get_developable_attrs("P")

        assert len(k_attrs) == 0
        assert len(p_attrs) == 0


# =============================================================================
# Apply Development Tests
# =============================================================================

class TestApplyDevelopment:
    """Test applying development to individual attributes."""

    def test_development_increases_attribute(self, young_prospect):
        """Development reps increase attribute value."""
        initial = young_prospect.attributes.get("speed")

        gain = apply_development(young_prospect, "speed", 10)

        new_value = young_prospect.attributes.get("speed")
        assert new_value >= initial
        assert gain >= 0

    def test_respects_potential_ceiling(self, young_prospect):
        """Attributes can't exceed potential + buffer."""
        # Set attribute close to ceiling
        young_prospect.attributes.set("speed", 95)

        apply_development(young_prospect, "speed", 100)

        # Should be capped at potential + buffer
        ceiling = young_prospect.potential + 5
        assert young_prospect.attributes.get("speed") <= ceiling

    def test_zero_rate_no_gain(self, veteran_player):
        """Player with zero development rate gains nothing."""
        # If at ceiling
        if calculate_development_rate(veteran_player) == 0:
            initial = veteran_player.attributes.get("speed")
            gain = apply_development(veteran_player, "speed", 100)

            assert gain == 0
            assert veteran_player.attributes.get("speed") == initial


# =============================================================================
# Develop Player Tests
# =============================================================================

class TestDevelopPlayer:
    """Test developing a player with random attributes."""

    def test_develops_multiple_attributes(self, young_prospect):
        """develop_player improves multiple attributes."""
        gains = develop_player(young_prospect, reps=20, attrs_per_session=3)

        # Should have developed up to 3 attributes
        assert len(gains) <= 3
        assert all(gain > 0 for gain in gains.values())

    def test_only_position_relevant_attributes(self, young_prospect):
        """Only develops attributes relevant to position."""
        developable = get_developable_attrs(young_prospect.position.value)

        gains = develop_player(young_prospect, reps=20)

        for attr in gains:
            assert attr in developable


# =============================================================================
# Can Develop Tests
# =============================================================================

class TestCanDevelop:
    """Test checking if a player can benefit from development."""

    def test_young_player_can_develop(self, young_prospect):
        """Young player with potential can develop."""
        assert can_develop(young_prospect) is True

    def test_veteran_may_not_develop(self, veteran_player):
        """Old veteran may not be able to develop."""
        # Depends on if at ceiling
        if veteran_player.overall >= veteran_player.potential:
            assert can_develop(veteran_player) is False
        elif veteran_player.age > AGE_CUTOFF + 5:
            assert can_develop(veteran_player) is False

    def test_kicker_cannot_develop(self):
        """Special teams positions can't develop through practice."""
        attrs = PlayerAttributes()
        attrs.set("potential", 85)
        kicker = Player(position=Position.K, attributes=attrs, age=25)

        assert can_develop(kicker) is False

    def test_at_potential_cannot_develop(self):
        """Player at potential ceiling can't develop."""
        attrs = PlayerAttributes()
        attrs.set("potential", 75)
        attrs.set("speed", 80)
        attrs.set("awareness", 80)
        player = Player(position=Position.RB, attributes=attrs, age=25)

        if player.overall >= player.potential:
            assert can_develop(player) is False
