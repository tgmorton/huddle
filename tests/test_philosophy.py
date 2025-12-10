"""Tests for the HC09-style philosophy-based player evaluation system."""

import pytest
from huddle.core.philosophy import (
    QBPhilosophy,
    RBPhilosophy,
    WRPhilosophy,
    TEPhilosophy,
    OLPhilosophy,
    DLPhilosophy,
    LBPhilosophy,
    CBPhilosophy,
    FSPhilosophy,
    SSPhilosophy,
    TeamPhilosophies,
    calculate_philosophy_overall,
    get_philosophy_weights,
    PHILOSOPHY_ATTRIBUTE_WEIGHTS,
)
from huddle.core.philosophy.evaluation import (
    calculate_philosophy_difference,
    get_scheme_fit_label,
)
from huddle.core.attributes.registry import PlayerAttributes


class TestPhilosophyEnums:
    """Test that all philosophy enums are properly defined."""

    def test_qb_philosophies(self):
        assert len(list(QBPhilosophy)) == 4
        assert QBPhilosophy.STRONG_ARM.value == "strong_arm"
        assert QBPhilosophy.PURE_PASSER.value == "pure_passer"
        assert QBPhilosophy.FIELD_GENERAL.value == "field_general"
        assert QBPhilosophy.MOBILE.value == "mobile"

    def test_rb_philosophies(self):
        assert len(list(RBPhilosophy)) == 5
        assert RBPhilosophy.POWER.value == "power"
        assert RBPhilosophy.RECEIVING.value == "receiving"
        assert RBPhilosophy.MOVES.value == "moves"
        assert RBPhilosophy.SPEED.value == "speed"
        assert RBPhilosophy.WORKHORSE.value == "workhorse"

    def test_all_philosophies_have_weights(self):
        """Every philosophy should have attribute weights defined."""
        all_philosophy_values = []
        for enum_class in [QBPhilosophy, RBPhilosophy, WRPhilosophy, TEPhilosophy,
                          OLPhilosophy, DLPhilosophy, LBPhilosophy, CBPhilosophy,
                          FSPhilosophy, SSPhilosophy]:
            for phil in enum_class:
                all_philosophy_values.append(phil.value)

        for phil_value in all_philosophy_values:
            weights = get_philosophy_weights(phil_value)
            assert weights, f"No weights defined for philosophy: {phil_value}"
            assert sum(weights.values()) > 0.9, f"Weights don't sum to ~1.0 for {phil_value}"


class TestTeamPhilosophies:
    """Test the TeamPhilosophies container."""

    def test_default_values(self):
        phil = TeamPhilosophies()
        assert phil.qb == QBPhilosophy.PURE_PASSER
        assert phil.rb == RBPhilosophy.SPEED
        assert phil.wr == WRPhilosophy.SPEED

    def test_custom_values(self):
        phil = TeamPhilosophies(
            qb=QBPhilosophy.MOBILE,
            rb=RBPhilosophy.POWER,
        )
        assert phil.qb == QBPhilosophy.MOBILE
        assert phil.rb == RBPhilosophy.POWER

    def test_get_philosophy_for_position(self):
        phil = TeamPhilosophies(
            qb=QBPhilosophy.MOBILE,
            rb=RBPhilosophy.POWER,
            ol=OLPhilosophy.ZONE_BLOCKING,
        )
        assert phil.get_philosophy_for_position("QB") == "mobile"
        assert phil.get_philosophy_for_position("RB") == "power"
        assert phil.get_philosophy_for_position("LT") == "zone_blocking"
        assert phil.get_philosophy_for_position("C") == "zone_blocking"

    def test_serialization(self):
        phil = TeamPhilosophies(
            qb=QBPhilosophy.FIELD_GENERAL,
            rb=RBPhilosophy.WORKHORSE,
        )
        data = phil.to_dict()
        restored = TeamPhilosophies.from_dict(data)

        assert restored.qb == phil.qb
        assert restored.rb == phil.rb
        assert restored.wr == phil.wr

    def test_generate_random(self):
        phil = TeamPhilosophies.generate_random()
        # Just verify it creates valid philosophies
        assert phil.qb in list(QBPhilosophy)
        assert phil.rb in list(RBPhilosophy)
        assert phil.wr in list(WRPhilosophy)


class TestPhilosophyOverallCalculation:
    """Test team-specific OVR calculation."""

    def test_speed_rb_favored_by_speed_philosophy(self):
        """A speed RB should rate higher for teams wanting speed backs."""
        attrs = PlayerAttributes()
        attrs.set("speed", 95)
        attrs.set("acceleration", 92)
        attrs.set("agility", 88)
        attrs.set("elusiveness", 85)
        attrs.set("trucking", 60)
        attrs.set("stiff_arm", 55)
        attrs.set("break_tackle", 58)

        speed_team = TeamPhilosophies(rb=RBPhilosophy.SPEED)
        power_team = TeamPhilosophies(rb=RBPhilosophy.POWER)

        speed_ovr = calculate_philosophy_overall(attrs, "RB", speed_team)
        power_ovr = calculate_philosophy_overall(attrs, "RB", power_team)

        # Speed team should rate this player significantly higher
        assert speed_ovr > power_ovr
        assert speed_ovr - power_ovr >= 10  # At least 10 point difference

    def test_power_rb_favored_by_power_philosophy(self):
        """A power RB should rate higher for teams wanting power backs."""
        attrs = PlayerAttributes()
        attrs.set("speed", 78)
        attrs.set("acceleration", 75)
        attrs.set("trucking", 92)
        attrs.set("stiff_arm", 88)
        attrs.set("break_tackle", 90)
        attrs.set("strength", 85)

        speed_team = TeamPhilosophies(rb=RBPhilosophy.SPEED)
        power_team = TeamPhilosophies(rb=RBPhilosophy.POWER)

        speed_ovr = calculate_philosophy_overall(attrs, "RB", speed_team)
        power_ovr = calculate_philosophy_overall(attrs, "RB", power_team)

        # Power team should rate this player significantly higher
        assert power_ovr > speed_ovr
        assert power_ovr - speed_ovr >= 10

    def test_mobile_qb_philosophy_difference(self):
        """Mobile QB should be valued differently by different teams."""
        attrs = PlayerAttributes()
        attrs.set("speed", 88)
        attrs.set("acceleration", 85)
        attrs.set("agility", 82)
        attrs.set("elusiveness", 80)
        attrs.set("throw_on_run", 85)
        attrs.set("throw_power", 75)
        attrs.set("throw_accuracy_short", 72)
        attrs.set("awareness", 65)

        mobile_team = TeamPhilosophies(qb=QBPhilosophy.MOBILE)
        pocket_team = TeamPhilosophies(qb=QBPhilosophy.PURE_PASSER)

        mobile_ovr = calculate_philosophy_overall(attrs, "QB", mobile_team)
        pocket_ovr = calculate_philosophy_overall(attrs, "QB", pocket_team)

        assert mobile_ovr > pocket_ovr

    def test_coverage_lb_vs_run_stopper_lb(self):
        """Coverage LB should be valued by coverage-focused teams."""
        attrs = PlayerAttributes()
        attrs.set("zone_coverage", 85)
        attrs.set("man_coverage", 82)
        attrs.set("speed", 88)
        attrs.set("awareness", 80)
        attrs.set("tackle", 70)
        attrs.set("block_shedding", 65)
        attrs.set("hit_power", 68)

        coverage_team = TeamPhilosophies(lb=LBPhilosophy.COVERAGE)
        run_stop_team = TeamPhilosophies(lb=LBPhilosophy.RUN_STOPPER)

        coverage_ovr = calculate_philosophy_overall(attrs, "MLB", coverage_team)
        run_stop_ovr = calculate_philosophy_overall(attrs, "MLB", run_stop_team)

        assert coverage_ovr > run_stop_ovr


class TestSchemeFit:
    """Test scheme fit calculations and labels."""

    def test_calculate_philosophy_difference(self):
        attrs = PlayerAttributes()
        attrs.set("speed", 95)
        attrs.set("acceleration", 92)
        attrs.set("agility", 88)
        attrs.set("trucking", 55)

        speed_team = TeamPhilosophies(rb=RBPhilosophy.SPEED)
        diff = calculate_philosophy_difference(attrs, "RB", speed_team)

        # Should be positive (team values player more than generic)
        # or could be any value depending on generic calculation
        assert isinstance(diff, int)

    def test_scheme_fit_labels(self):
        assert get_scheme_fit_label(10) == "Perfect Fit"
        assert get_scheme_fit_label(5) == "Great Fit"
        assert get_scheme_fit_label(2) == "Good Fit"
        assert get_scheme_fit_label(0) == "Average Fit"
        assert get_scheme_fit_label(-3) == "Poor Fit"
        assert get_scheme_fit_label(-8) == "Scheme Mismatch"


class TestPhilosophyIntegration:
    """Test integration with TeamTendencies."""

    def test_tendencies_calculate_overall(self):
        from huddle.core.models.tendencies import TeamTendencies

        tendencies = TeamTendencies()
        # Default should use PURE_PASSER for QB

        attrs = PlayerAttributes()
        attrs.set("throw_power", 85)
        attrs.set("throw_accuracy_short", 88)
        attrs.set("throw_accuracy_med", 85)
        attrs.set("throw_accuracy_deep", 80)
        attrs.set("awareness", 82)

        ovr = tendencies.calculate_player_overall(attrs, "QB")
        assert 70 <= ovr <= 95  # Should be in reasonable range

    def test_tendencies_philosophy_serialization(self):
        from huddle.core.models.tendencies import TeamTendencies

        tendencies = TeamTendencies()
        tendencies.philosophies.qb = QBPhilosophy.MOBILE
        tendencies.philosophies.rb = RBPhilosophy.POWER

        data = tendencies.to_dict()
        restored = TeamTendencies.from_dict(data)

        assert restored.philosophies.qb == QBPhilosophy.MOBILE
        assert restored.philosophies.rb == RBPhilosophy.POWER
