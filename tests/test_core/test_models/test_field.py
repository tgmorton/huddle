"""Tests for field position and down state models."""

import pytest

from huddle.core.models.field import DownState, FieldPosition, FieldZone


class TestFieldPosition:
    """Tests for FieldPosition."""

    def test_clamps_to_valid_range(self):
        """Yard line should be clamped to 0-100."""
        pos = FieldPosition(-10)
        assert pos.yard_line == 0

        pos = FieldPosition(150)
        assert pos.yard_line == 100

    def test_from_field_position_own_side(self):
        """Own side positions should map correctly."""
        pos = FieldPosition.from_field_position(25, own_side=True)
        assert pos.yard_line == 25

        pos = FieldPosition.from_field_position(1, own_side=True)
        assert pos.yard_line == 1

    def test_from_field_position_opponent_side(self):
        """Opponent side positions should map correctly."""
        pos = FieldPosition.from_field_position(25, own_side=False)
        assert pos.yard_line == 75

        pos = FieldPosition.from_field_position(1, own_side=False)
        assert pos.yard_line == 99

    def test_display_own_territory(self):
        """Display should show 'OWN' for own territory."""
        pos = FieldPosition(25)
        assert pos.display == "OWN 25"

        pos = FieldPosition(10)
        assert pos.display == "OWN 10"

    def test_display_opponent_territory(self):
        """Display should show 'OPP' for opponent territory."""
        pos = FieldPosition(75)
        assert pos.display == "OPP 25"

        pos = FieldPosition(90)
        assert pos.display == "OPP 10"

    def test_display_midfield(self):
        """Display should show '50' for midfield."""
        pos = FieldPosition(50)
        assert pos.display == "50"

    def test_zone_own_endzone(self):
        """Positions 0-10 should be OWN_ENDZONE."""
        for yard in range(0, 11):
            pos = FieldPosition(yard)
            assert pos.zone == FieldZone.OWN_ENDZONE

    def test_zone_own_territory(self):
        """Positions 11-50 should be OWN_TERRITORY."""
        for yard in [11, 25, 50]:
            pos = FieldPosition(yard)
            assert pos.zone == FieldZone.OWN_TERRITORY

    def test_zone_opponent_territory(self):
        """Positions 51-89 should be OPPONENT_TERRITORY."""
        for yard in [51, 75, 89]:
            pos = FieldPosition(yard)
            assert pos.zone == FieldZone.OPPONENT_TERRITORY

    def test_zone_red_zone(self):
        """Positions 90-100 should be RED_ZONE."""
        for yard in [90, 95, 100]:
            pos = FieldPosition(yard)
            assert pos.zone == FieldZone.RED_ZONE

    def test_yards_to_goal(self):
        """yards_to_goal should calculate correctly."""
        pos = FieldPosition(25)
        assert pos.yards_to_goal == 75

        pos = FieldPosition(90)
        assert pos.yards_to_goal == 10

        pos = FieldPosition(100)
        assert pos.yards_to_goal == 0

    def test_yards_to_safety(self):
        """yards_to_safety should return distance to own goal."""
        pos = FieldPosition(25)
        assert pos.yards_to_safety == 25

        pos = FieldPosition(5)
        assert pos.yards_to_safety == 5

    def test_is_goal_to_go(self):
        """is_goal_to_go should be True inside 10 yard line."""
        pos = FieldPosition(89)
        assert pos.is_goal_to_go is False

        pos = FieldPosition(90)
        assert pos.is_goal_to_go is True

        pos = FieldPosition(99)
        assert pos.is_goal_to_go is True

    def test_is_in_field_goal_range(self):
        """is_in_field_goal_range should be True when reasonable FG possible."""
        # 45 yard line = 55 yard FG attempt
        pos = FieldPosition(44)
        assert pos.is_in_field_goal_range is False

        pos = FieldPosition(45)
        assert pos.is_in_field_goal_range is True

        pos = FieldPosition(90)
        assert pos.is_in_field_goal_range is True

    def test_advance_positive(self):
        """advance with positive yards should move toward opponent goal."""
        pos = FieldPosition(25)
        new_pos = pos.advance(10)
        assert new_pos.yard_line == 35

    def test_advance_negative(self):
        """advance with negative yards should move toward own goal."""
        pos = FieldPosition(25)
        new_pos = pos.advance(-5)
        assert new_pos.yard_line == 20

    def test_advance_clamps(self):
        """advance should clamp to valid range."""
        pos = FieldPosition(95)
        new_pos = pos.advance(10)
        assert new_pos.yard_line == 100

        pos = FieldPosition(5)
        new_pos = pos.advance(-10)
        assert new_pos.yard_line == 0

    def test_add_operator(self):
        """+ operator should work like advance."""
        pos = FieldPosition(25)
        new_pos = pos + 15
        assert new_pos.yard_line == 40

    def test_sub_operator(self):
        """- operator should work like negative advance."""
        pos = FieldPosition(25)
        new_pos = pos - 10
        assert new_pos.yard_line == 15


class TestDownState:
    """Tests for DownState."""

    def test_default_values(self):
        """Default should be 1st and 10 at own 25."""
        state = DownState()
        assert state.down == 1
        assert state.yards_to_go == 10
        assert state.line_of_scrimmage.yard_line == 25

    def test_display_normal(self):
        """Display should show down and distance."""
        state = DownState(down=1, yards_to_go=10)
        assert state.display == "1st & 10"

        state = DownState(down=2, yards_to_go=7)
        assert state.display == "2nd & 7"

        state = DownState(down=3, yards_to_go=3)
        assert state.display == "3rd & 3"

        state = DownState(down=4, yards_to_go=1)
        assert state.display == "4th & 1"

    def test_display_goal_to_go(self):
        """Display should show 'Goal' when in goal-to-go situation."""
        state = DownState(
            down=1, yards_to_go=10, line_of_scrimmage=FieldPosition(95)
        )
        assert state.display == "1st & Goal"

    def test_full_display(self):
        """full_display should include field position."""
        state = DownState(
            down=2, yards_to_go=8, line_of_scrimmage=FieldPosition(35)
        )
        assert "2nd & 8" in state.full_display
        assert "OWN 35" in state.full_display

    def test_is_goal_to_go(self):
        """is_goal_to_go when yards to go >= yards to goal."""
        # At the 5, 10 yards to go = goal to go
        state = DownState(
            down=1, yards_to_go=10, line_of_scrimmage=FieldPosition(95)
        )
        assert state.is_goal_to_go is True

        # At the 85, 10 yards to go = not goal to go (need 15)
        state = DownState(
            down=1, yards_to_go=10, line_of_scrimmage=FieldPosition(85)
        )
        assert state.is_goal_to_go is False

    def test_is_fourth_down(self):
        """is_fourth_down should return True only on 4th down."""
        for down in [1, 2, 3]:
            state = DownState(down=down)
            assert state.is_fourth_down is False

        state = DownState(down=4)
        assert state.is_fourth_down is True

    def test_is_short_yardage(self):
        """is_short_yardage should be True for 3 yards or less."""
        state = DownState(yards_to_go=4)
        assert state.is_short_yardage is False

        state = DownState(yards_to_go=3)
        assert state.is_short_yardage is True

        state = DownState(yards_to_go=1)
        assert state.is_short_yardage is True

    def test_is_long_yardage(self):
        """is_long_yardage should be True for 7+ yards."""
        state = DownState(yards_to_go=6)
        assert state.is_long_yardage is False

        state = DownState(yards_to_go=7)
        assert state.is_long_yardage is True

        state = DownState(yards_to_go=15)
        assert state.is_long_yardage is True

    def test_first_down_marker(self):
        """first_down_marker should calculate target yard line."""
        state = DownState(
            down=1, yards_to_go=10, line_of_scrimmage=FieldPosition(25)
        )
        assert state.first_down_marker == 35

    def test_first_down_marker_goal_to_go(self):
        """first_down_marker should cap at 100 (goal line)."""
        state = DownState(
            down=1, yards_to_go=10, line_of_scrimmage=FieldPosition(95)
        )
        assert state.first_down_marker == 100

    def test_reset_for_first_down(self):
        """reset_for_first_down should create new 1st and 10."""
        state = DownState(down=3, yards_to_go=2)
        new_state = state.reset_for_first_down(FieldPosition(50))

        assert new_state.down == 1
        assert new_state.yards_to_go == 10
        assert new_state.line_of_scrimmage.yard_line == 50

    def test_reset_for_first_down_near_goal(self):
        """reset_for_first_down should adjust yards_to_go near goal line."""
        state = DownState()
        new_state = state.reset_for_first_down(FieldPosition(95))

        assert new_state.down == 1
        assert new_state.yards_to_go == 5  # Only 5 yards to goal

    def test_advance_first_down(self):
        """advance should detect first down."""
        state = DownState(
            down=1, yards_to_go=10, line_of_scrimmage=FieldPosition(25)
        )
        new_state, first_down = state.advance(12)

        assert first_down is True
        assert new_state.down == 1
        assert new_state.yards_to_go == 10
        assert new_state.line_of_scrimmage.yard_line == 37

    def test_advance_no_first_down(self):
        """advance should increment down when no first down."""
        state = DownState(
            down=1, yards_to_go=10, line_of_scrimmage=FieldPosition(25)
        )
        new_state, first_down = state.advance(5)

        assert first_down is False
        assert new_state.down == 2
        assert new_state.yards_to_go == 5
        assert new_state.line_of_scrimmage.yard_line == 30

    def test_advance_touchdown(self):
        """advance should detect touchdown."""
        state = DownState(
            down=1, yards_to_go=5, line_of_scrimmage=FieldPosition(95)
        )
        new_state, first_down = state.advance(10)

        assert first_down is True  # TD counts as first down
        assert new_state.line_of_scrimmage.yard_line == 100

    def test_advance_loss_of_yards(self):
        """advance should handle negative yards."""
        state = DownState(
            down=1, yards_to_go=10, line_of_scrimmage=FieldPosition(25)
        )
        new_state, first_down = state.advance(-5)

        assert first_down is False
        assert new_state.down == 2
        assert new_state.yards_to_go == 15
        assert new_state.line_of_scrimmage.yard_line == 20

    def test_advance_exact_first_down(self):
        """advance exactly meeting first down marker should get first down."""
        state = DownState(
            down=2, yards_to_go=7, line_of_scrimmage=FieldPosition(30)
        )
        new_state, first_down = state.advance(7)

        assert first_down is True
        assert new_state.down == 1

    def test_copy(self):
        """copy should create independent copy."""
        original = DownState(
            down=3, yards_to_go=5, line_of_scrimmage=FieldPosition(40)
        )
        copy = original.copy()

        assert copy.down == 3
        assert copy.yards_to_go == 5
        assert copy.line_of_scrimmage.yard_line == 40

        # Modifying copy should not affect original
        copy.down = 4
        assert original.down == 3

    def test_to_dict_from_dict(self):
        """Serialization round-trip should preserve data."""
        original = DownState(
            down=3, yards_to_go=7, line_of_scrimmage=FieldPosition(45)
        )
        data = original.to_dict()
        restored = DownState.from_dict(data)

        assert restored.down == 3
        assert restored.yards_to_go == 7
        assert restored.line_of_scrimmage.yard_line == 45


class TestDownStateEdgeCases:
    """Edge case tests for DownState.advance()."""

    def test_fourth_down_no_conversion(self):
        """4th down without conversion should still advance down to 5."""
        state = DownState(
            down=4, yards_to_go=3, line_of_scrimmage=FieldPosition(50)
        )
        new_state, first_down = state.advance(1)

        # Down becomes 5 (turnover on downs handled by engine)
        assert new_state.down == 5
        assert first_down is False

    def test_goal_line_stand(self):
        """Advance from goal line should not go past 100."""
        state = DownState(
            down=1, yards_to_go=1, line_of_scrimmage=FieldPosition(99)
        )
        new_state, first_down = state.advance(5)

        assert new_state.line_of_scrimmage.yard_line == 100
        assert first_down is True

    def test_backed_up_and_sacked(self):
        """Sack when backed up should not go below 0."""
        state = DownState(
            down=2, yards_to_go=10, line_of_scrimmage=FieldPosition(3)
        )
        new_state, first_down = state.advance(-10)

        # Should be clamped to 0 (safety territory, handled by engine)
        assert new_state.line_of_scrimmage.yard_line == 0
        assert new_state.yards_to_go == 20  # Original 10 + 10 yard loss
