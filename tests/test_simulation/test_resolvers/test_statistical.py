"""Tests for StatisticalPlayResolver."""

import pytest
import random

from huddle.core.enums import PassType, PlayOutcome, PlayType, RunType
from huddle.core.models.field import DownState, FieldPosition
from huddle.core.models.game import GameState
from huddle.core.models.play import DefensiveCall, PlayCall, PlayResult
from huddle.simulation.resolvers.statistical import StatisticalPlayResolver


class TestStatisticalPlayResolverInit:
    """Tests for StatisticalPlayResolver initialization."""

    def test_has_completion_rates(self):
        """Resolver should have base completion rates defined."""
        resolver = StatisticalPlayResolver()
        assert PassType.SHORT in resolver.BASE_COMPLETION_RATES
        assert PassType.DEEP in resolver.BASE_COMPLETION_RATES

    def test_completion_rates_are_reasonable(self):
        """Completion rates should be realistic (0-1 range, deep < short)."""
        resolver = StatisticalPlayResolver()
        for pass_type, rate in resolver.BASE_COMPLETION_RATES.items():
            assert 0 < rate < 1, f"{pass_type} rate {rate} not in (0, 1)"

        # Deep passes should be harder than short
        assert resolver.BASE_COMPLETION_RATES[PassType.DEEP] < resolver.BASE_COMPLETION_RATES[PassType.SHORT]

    def test_has_yards_distributions(self):
        """Resolver should have yards distributions defined."""
        resolver = StatisticalPlayResolver()
        assert PassType.SHORT in resolver.PASS_YARDS_DISTRIBUTION
        assert RunType.INSIDE in resolver.RUN_YARDS_DISTRIBUTION


class TestResolvePlay:
    """Tests for resolve_play() dispatching."""

    def test_resolves_pass_play(self, new_game_state, home_team, away_team):
        """Should resolve pass plays."""
        resolver = StatisticalPlayResolver()
        call = PlayCall.pass_play(PassType.SHORT)
        def_call = DefensiveCall.cover_3()

        result = resolver.resolve_play(
            new_game_state, home_team, away_team, call, def_call
        )

        assert isinstance(result, PlayResult)
        assert result.play_call == call

    def test_resolves_run_play(self, new_game_state, home_team, away_team):
        """Should resolve run plays."""
        resolver = StatisticalPlayResolver()
        call = PlayCall.run(RunType.INSIDE)
        def_call = DefensiveCall.cover_3()

        result = resolver.resolve_play(
            new_game_state, home_team, away_team, call, def_call
        )

        assert isinstance(result, PlayResult)
        assert result.play_call == call

    def test_resolves_punt(self, new_game_state, home_team, away_team):
        """Should resolve punt plays."""
        resolver = StatisticalPlayResolver()
        call = PlayCall.punt()
        def_call = DefensiveCall.cover_3()

        result = resolver.resolve_play(
            new_game_state, home_team, away_team, call, def_call
        )

        assert result.outcome == PlayOutcome.PUNT_RESULT

    def test_resolves_field_goal(self, new_game_state, home_team, away_team):
        """Should resolve field goal attempts."""
        resolver = StatisticalPlayResolver()
        new_game_state.down_state = DownState(
            down=4, yards_to_go=5, line_of_scrimmage=FieldPosition(75)
        )
        call = PlayCall.field_goal()
        def_call = DefensiveCall.cover_3()

        result = resolver.resolve_play(
            new_game_state, home_team, away_team, call, def_call
        )

        assert result.outcome in (PlayOutcome.FIELD_GOAL_GOOD, PlayOutcome.FIELD_GOAL_MISSED)


class TestPassPlayResolution:
    """Tests for pass play resolution logic."""

    def test_pass_can_be_complete(self, new_game_state, home_team, away_team):
        """Pass plays can result in completions."""
        resolver = StatisticalPlayResolver()
        random.seed(42)  # For reproducibility

        completions = 0
        for _ in range(100):
            result = resolver.resolve_play(
                new_game_state, home_team, away_team,
                PlayCall.pass_play(PassType.SHORT),
                DefensiveCall.cover_3()
            )
            if result.outcome == PlayOutcome.COMPLETE:
                completions += 1

        # Should have some completions (seed 42 should give consistent results)
        assert completions > 0

    def test_pass_can_be_incomplete(self, new_game_state, home_team, away_team):
        """Pass plays can result in incompletions."""
        resolver = StatisticalPlayResolver()
        random.seed(42)

        incompletions = 0
        for _ in range(100):
            result = resolver.resolve_play(
                new_game_state, home_team, away_team,
                PlayCall.pass_play(PassType.DEEP),  # Deep passes less likely to complete
                DefensiveCall.cover_3()
            )
            if result.outcome == PlayOutcome.INCOMPLETE:
                incompletions += 1

        assert incompletions > 0

    def test_incomplete_stops_clock(self, new_game_state, home_team, away_team):
        """Incomplete passes should stop the clock."""
        resolver = StatisticalPlayResolver()
        random.seed(123)

        # Run until we get an incomplete
        for _ in range(100):
            result = resolver.resolve_play(
                new_game_state, home_team, away_team,
                PlayCall.pass_play(PassType.DEEP),
                DefensiveCall.cover_3()
            )
            if result.outcome == PlayOutcome.INCOMPLETE:
                assert result.clock_stopped is True
                assert result.clock_stop_reason == "incomplete"
                break

    def test_sack_loses_yards(self, new_game_state, home_team, away_team):
        """Sacks should result in negative yards."""
        resolver = StatisticalPlayResolver()
        random.seed(42)

        # Run many plays until we get a sack
        for _ in range(200):
            result = resolver.resolve_play(
                new_game_state, home_team, away_team,
                PlayCall.pass_play(PassType.DEEP),
                DefensiveCall.blitz(6)  # Blitz increases sack chance
            )
            if result.outcome == PlayOutcome.SACK:
                assert result.yards_gained < 0
                assert result.is_sack is True
                break

    def test_interception_is_turnover(self, new_game_state, home_team, away_team):
        """Interceptions should be marked as turnovers."""
        resolver = StatisticalPlayResolver()
        random.seed(42)

        # Run many plays until we get an INT
        for _ in range(500):
            result = resolver.resolve_play(
                new_game_state, home_team, away_team,
                PlayCall.pass_play(PassType.DEEP),
                DefensiveCall.cover_3()
            )
            if result.outcome == PlayOutcome.INTERCEPTION:
                assert result.is_turnover is True
                break


class TestRunPlayResolution:
    """Tests for run play resolution logic."""

    def test_run_gains_yards(self, new_game_state, home_team, away_team):
        """Run plays should typically gain some yards."""
        resolver = StatisticalPlayResolver()
        random.seed(42)

        total_yards = 0
        for _ in range(50):
            result = resolver.resolve_play(
                new_game_state, home_team, away_team,
                PlayCall.run(RunType.INSIDE),
                DefensiveCall.cover_3()
            )
            if result.outcome == PlayOutcome.RUSH:
                total_yards += result.yards_gained

        # Average should be positive (around 3-4 yards per carry)
        assert total_yards > 0

    def test_run_can_lose_yards(self, new_game_state, home_team, away_team):
        """Run plays can result in negative yards."""
        resolver = StatisticalPlayResolver()
        random.seed(42)

        losses = 0
        for _ in range(100):
            result = resolver.resolve_play(
                new_game_state, home_team, away_team,
                PlayCall.run(RunType.INSIDE),
                DefensiveCall.blitz(5)
            )
            if result.outcome == PlayOutcome.RUSH and result.yards_gained < 0:
                losses += 1

        # Should have some losses (tackles for loss)
        assert losses > 0

    def test_fumble_is_turnover(self, new_game_state, home_team, away_team):
        """Fumbles should be marked as turnovers."""
        resolver = StatisticalPlayResolver()
        random.seed(42)

        # Run many plays until we get a fumble
        for _ in range(500):
            result = resolver.resolve_play(
                new_game_state, home_team, away_team,
                PlayCall.run(RunType.OUTSIDE),
                DefensiveCall.cover_3()
            )
            if result.outcome == PlayOutcome.FUMBLE_LOST:
                assert result.is_turnover is True
                break


class TestSpecialTeamsResolution:
    """Tests for special teams play resolution."""

    def test_punt_has_positive_distance(self, new_game_state, home_team, away_team):
        """Punts should have reasonable distance."""
        resolver = StatisticalPlayResolver()
        call = PlayCall.punt()
        def_call = DefensiveCall.cover_3()

        result = resolver.resolve_play(
            new_game_state, home_team, away_team, call, def_call
        )

        # yards_gained is negative (because possession changes direction)
        # but the absolute value should be a reasonable punt distance
        assert abs(result.yards_gained) > 0

    def test_field_goal_short_range_usually_good(self, new_game_state, home_team, away_team):
        """Short field goals should usually be made."""
        resolver = StatisticalPlayResolver()
        # 25 yard line = 92 yard line in our coordinate system
        # That's a 25 yard FG (8 + 17 = 25)
        new_game_state.down_state = DownState(
            down=4, yards_to_go=5, line_of_scrimmage=FieldPosition(92)
        )

        random.seed(42)
        made = 0
        for _ in range(20):
            result = resolver.resolve_play(
                new_game_state, home_team, away_team,
                PlayCall.field_goal(),
                DefensiveCall.cover_3()
            )
            if result.outcome == PlayOutcome.FIELD_GOAL_GOOD:
                made += 1

        # 25-yard FGs should be made most of the time
        assert made > 15

    def test_field_goal_long_range_sometimes_misses(self, new_game_state, home_team, away_team):
        """Long field goals should miss sometimes."""
        resolver = StatisticalPlayResolver()
        # 50 yard line = 50 yard FG (33 + 17 = 50)
        new_game_state.down_state = DownState(
            down=4, yards_to_go=10, line_of_scrimmage=FieldPosition(67)
        )

        random.seed(42)
        missed = 0
        for _ in range(30):
            result = resolver.resolve_play(
                new_game_state, home_team, away_team,
                PlayCall.field_goal(),
                DefensiveCall.cover_3()
            )
            if result.outcome == PlayOutcome.FIELD_GOAL_MISSED:
                missed += 1

        # 50-yard FGs should miss sometimes
        assert missed > 0

    def test_extra_point_usually_good(self, new_game_state, home_team, away_team):
        """Extra points should usually be made."""
        resolver = StatisticalPlayResolver()

        random.seed(42)
        made = 0
        for _ in range(50):
            result = resolver.resolve_play(
                new_game_state, home_team, away_team,
                PlayCall.extra_point(),
                DefensiveCall.cover_3()
            )
            if result.outcome == PlayOutcome.EXTRA_POINT_GOOD:
                made += 1

        # PATs should be made ~94% of the time
        assert made > 40

    def test_two_point_conversion_outcomes(self, new_game_state, home_team, away_team):
        """Two-point conversions should succeed about half the time."""
        resolver = StatisticalPlayResolver()

        random.seed(42)
        successes = 0
        for _ in range(100):
            result = resolver.resolve_play(
                new_game_state, home_team, away_team,
                PlayCall.two_point(pass_type=PassType.SHORT),
                DefensiveCall.cover_3()
            )
            if result.outcome == PlayOutcome.TWO_POINT_GOOD:
                successes += 1

        # Should be roughly 40-60% success rate
        assert 30 < successes < 70


class TestTouchdownDetection:
    """Tests for touchdown detection."""

    def test_pass_touchdown_near_goal(self, new_game_state, home_team, away_team):
        """Pass plays near goal line can score touchdowns."""
        resolver = StatisticalPlayResolver()
        new_game_state.down_state = DownState(
            down=1, yards_to_go=5, line_of_scrimmage=FieldPosition(95)
        )

        random.seed(42)
        touchdowns = 0
        for _ in range(100):
            result = resolver.resolve_play(
                new_game_state, home_team, away_team,
                PlayCall.pass_play(PassType.SHORT),
                DefensiveCall.cover_3()
            )
            if result.is_touchdown:
                touchdowns += 1

        assert touchdowns > 0

    def test_run_touchdown_near_goal(self, new_game_state, home_team, away_team):
        """Run plays near goal line can score touchdowns."""
        resolver = StatisticalPlayResolver()
        new_game_state.down_state = DownState(
            down=1, yards_to_go=2, line_of_scrimmage=FieldPosition(98)
        )

        random.seed(42)
        touchdowns = 0
        for _ in range(100):
            result = resolver.resolve_play(
                new_game_state, home_team, away_team,
                PlayCall.run(RunType.INSIDE),
                DefensiveCall.cover_3()
            )
            if result.is_touchdown:
                touchdowns += 1

        assert touchdowns > 0

    def test_touchdown_awards_six_points(self, new_game_state, home_team, away_team):
        """Touchdowns should award 6 points."""
        resolver = StatisticalPlayResolver()
        new_game_state.down_state = DownState(
            down=1, yards_to_go=1, line_of_scrimmage=FieldPosition(99)
        )

        random.seed(42)
        for _ in range(100):
            result = resolver.resolve_play(
                new_game_state, home_team, away_team,
                PlayCall.run(RunType.QB_SNEAK),
                DefensiveCall.cover_3()
            )
            if result.is_touchdown:
                assert result.points_scored == 6
                break


class TestPenaltyGeneration:
    """Tests for penalty generation."""

    def test_penalties_can_occur(self, new_game_state, home_team, away_team):
        """Penalties should occur sometimes."""
        resolver = StatisticalPlayResolver()
        random.seed(42)

        penalties = 0
        for _ in range(200):
            result = resolver.resolve_play(
                new_game_state, home_team, away_team,
                PlayCall.run(RunType.INSIDE),
                DefensiveCall.cover_3()
            )
            if result.outcome in (PlayOutcome.PENALTY_OFFENSE, PlayOutcome.PENALTY_DEFENSE):
                penalties += 1

        # Should have some penalties
        assert penalties > 0

    def test_offensive_penalty_has_yards(self, new_game_state, home_team, away_team):
        """Offensive penalties should have penalty yards."""
        resolver = StatisticalPlayResolver()
        random.seed(42)

        for _ in range(500):
            result = resolver.resolve_play(
                new_game_state, home_team, away_team,
                PlayCall.pass_play(PassType.SHORT),
                DefensiveCall.cover_3()
            )
            if result.outcome == PlayOutcome.PENALTY_OFFENSE:
                assert result.penalty_yards > 0
                assert result.penalty_on_offense is True
                assert result.penalty_type is not None
                break

    def test_defensive_penalty_has_yards(self, new_game_state, home_team, away_team):
        """Defensive penalties should have penalty yards."""
        resolver = StatisticalPlayResolver()
        random.seed(42)

        for _ in range(500):
            result = resolver.resolve_play(
                new_game_state, home_team, away_team,
                PlayCall.pass_play(PassType.DEEP),
                DefensiveCall.man(press=True)
            )
            if result.outcome == PlayOutcome.PENALTY_DEFENSE:
                assert result.penalty_yards > 0
                assert result.penalty_on_offense is False
                assert result.penalty_type is not None
                break


class TestTimeElapsed:
    """Tests for play time consumption."""

    def test_plays_consume_time(self, new_game_state, home_team, away_team):
        """All plays should consume some time."""
        resolver = StatisticalPlayResolver()

        for call in [
            PlayCall.run(RunType.INSIDE),
            PlayCall.pass_play(PassType.SHORT),
            PlayCall.punt(),
            PlayCall.field_goal(),
        ]:
            result = resolver.resolve_play(
                new_game_state, home_team, away_team, call, DefensiveCall.cover_3()
            )
            assert result.time_elapsed_seconds > 0

    def test_clock_stopping_plays_consume_less_time(self, new_game_state, home_team, away_team):
        """Clock-stopping plays should consume less game time."""
        resolver = StatisticalPlayResolver()
        random.seed(42)

        # Get times for incomplete passes (clock stops)
        incomplete_times = []
        for _ in range(50):
            result = resolver.resolve_play(
                new_game_state, home_team, away_team,
                PlayCall.pass_play(PassType.DEEP),
                DefensiveCall.cover_3()
            )
            if result.outcome == PlayOutcome.INCOMPLETE:
                incomplete_times.append(result.time_elapsed_seconds)

        # Get times for completed passes (clock usually runs)
        complete_times = []
        for _ in range(50):
            result = resolver.resolve_play(
                new_game_state, home_team, away_team,
                PlayCall.pass_play(PassType.SHORT),
                DefensiveCall.cover_3()
            )
            if result.outcome == PlayOutcome.COMPLETE and not result.clock_stopped:
                complete_times.append(result.time_elapsed_seconds)

        if incomplete_times and complete_times:
            avg_incomplete = sum(incomplete_times) / len(incomplete_times)
            avg_complete = sum(complete_times) / len(complete_times)
            # Incomplete passes should use less clock time on average
            assert avg_incomplete < avg_complete


class TestDescriptionGeneration:
    """Tests for play description generation."""

    def test_completion_has_description(self, new_game_state, home_team, away_team):
        """Completions should have descriptive text."""
        resolver = StatisticalPlayResolver()
        random.seed(42)

        for _ in range(50):
            result = resolver.resolve_play(
                new_game_state, home_team, away_team,
                PlayCall.pass_play(PassType.SHORT),
                DefensiveCall.cover_3()
            )
            if result.outcome == PlayOutcome.COMPLETE:
                assert "complete" in result.description.lower()
                assert "yards" in result.description.lower()
                break

    def test_rush_has_description(self, new_game_state, home_team, away_team):
        """Rushes should have descriptive text."""
        resolver = StatisticalPlayResolver()

        result = resolver.resolve_play(
            new_game_state, home_team, away_team,
            PlayCall.run(RunType.INSIDE),
            DefensiveCall.cover_3()
        )
        if result.outcome == PlayOutcome.RUSH:
            assert "rush" in result.description.lower()

    def test_touchdown_description_indicates_score(self, new_game_state, home_team, away_team):
        """Touchdown descriptions should clearly indicate TD."""
        resolver = StatisticalPlayResolver()
        new_game_state.down_state = DownState(
            down=1, yards_to_go=1, line_of_scrimmage=FieldPosition(99)
        )
        random.seed(42)

        for _ in range(50):
            result = resolver.resolve_play(
                new_game_state, home_team, away_team,
                PlayCall.run(RunType.QB_SNEAK),
                DefensiveCall.cover_3()
            )
            if result.is_touchdown:
                assert "touchdown" in result.description.lower()
                break
