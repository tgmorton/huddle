"""Tests for game state models."""

import pytest
from uuid import uuid4

from huddle.core.models.game import (
    GameClock,
    GamePhase,
    GameState,
    PossessionState,
    ScoreState,
)


class TestGamePhase:
    """Tests for GamePhase enum."""

    def test_is_active_for_playing_phases(self):
        """Active phases should return True for is_active."""
        active_phases = [
            GamePhase.FIRST_QUARTER,
            GamePhase.SECOND_QUARTER,
            GamePhase.THIRD_QUARTER,
            GamePhase.FOURTH_QUARTER,
            GamePhase.OVERTIME,
        ]
        for phase in active_phases:
            assert phase.is_active is True, f"{phase} should be active"

    def test_is_active_for_non_playing_phases(self):
        """Non-playing phases should return False for is_active."""
        inactive_phases = [
            GamePhase.PREGAME,
            GamePhase.COIN_TOSS,
            GamePhase.KICKOFF,
            GamePhase.HALFTIME,
            GamePhase.FINAL,
        ]
        for phase in inactive_phases:
            assert phase.is_active is False, f"{phase} should not be active"

    def test_quarter_number(self):
        """Quarter numbers should be correct."""
        assert GamePhase.FIRST_QUARTER.quarter_number == 1
        assert GamePhase.SECOND_QUARTER.quarter_number == 2
        assert GamePhase.THIRD_QUARTER.quarter_number == 3
        assert GamePhase.FOURTH_QUARTER.quarter_number == 4
        assert GamePhase.OVERTIME.quarter_number == 5

    def test_quarter_number_non_playing(self):
        """Non-playing phases should return 0."""
        assert GamePhase.PREGAME.quarter_number == 0
        assert GamePhase.HALFTIME.quarter_number == 0
        assert GamePhase.FINAL.quarter_number == 0


class TestGameClock:
    """Tests for GameClock."""

    def test_default_values(self):
        """Default clock should start Q1 with 15:00."""
        clock = GameClock()
        assert clock.quarter == 1
        assert clock.time_remaining_seconds == 900
        assert clock.play_clock == 40

    def test_minutes_property(self):
        """Minutes should calculate correctly."""
        clock = GameClock(time_remaining_seconds=725)
        assert clock.minutes == 12

    def test_seconds_property(self):
        """Seconds should calculate correctly."""
        clock = GameClock(time_remaining_seconds=725)
        assert clock.seconds == 5

    def test_display_format(self):
        """Display should format as MM:SS."""
        clock = GameClock(time_remaining_seconds=725)
        assert clock.display == "12:05"

        clock = GameClock(time_remaining_seconds=60)
        assert clock.display == "1:00"

        clock = GameClock(time_remaining_seconds=5)
        assert clock.display == "0:05"

    def test_is_quarter_over(self):
        """Quarter over detection."""
        clock = GameClock(time_remaining_seconds=1)
        assert clock.is_quarter_over is False

        clock.tick(1)
        assert clock.is_quarter_over is True

    def test_is_two_minute_warning(self):
        """Two-minute warning only in Q2 and Q4."""
        # Q1 - no two minute warning
        clock = GameClock(quarter=1, time_remaining_seconds=120)
        assert clock.is_two_minute_warning is False

        # Q2 - yes
        clock = GameClock(quarter=2, time_remaining_seconds=120)
        assert clock.is_two_minute_warning is True

        # Q3 - no
        clock = GameClock(quarter=3, time_remaining_seconds=120)
        assert clock.is_two_minute_warning is False

        # Q4 - yes
        clock = GameClock(quarter=4, time_remaining_seconds=120)
        assert clock.is_two_minute_warning is True

        # Q4 but more than 2 minutes
        clock = GameClock(quarter=4, time_remaining_seconds=121)
        assert clock.is_two_minute_warning is False

    def test_is_hurry_up_time(self):
        """Hurry up time should match two minute warning conditions."""
        clock = GameClock(quarter=4, time_remaining_seconds=100)
        assert clock.is_hurry_up_time is True

        clock = GameClock(quarter=2, time_remaining_seconds=100)
        assert clock.is_hurry_up_time is True

        clock = GameClock(quarter=3, time_remaining_seconds=100)
        assert clock.is_hurry_up_time is False

    def test_tick(self):
        """Tick should reduce time correctly."""
        clock = GameClock(time_remaining_seconds=100)
        clock.tick(25)
        assert clock.time_remaining_seconds == 75

    def test_tick_does_not_go_negative(self):
        """Tick should not go below 0."""
        clock = GameClock(time_remaining_seconds=10)
        clock.tick(20)
        assert clock.time_remaining_seconds == 0

    def test_next_quarter(self):
        """Next quarter should advance and reset time."""
        clock = GameClock(quarter=1, time_remaining_seconds=0)
        clock.next_quarter()
        assert clock.quarter == 2
        assert clock.time_remaining_seconds == 900

    def test_reset_play_clock(self):
        """Reset play clock should set to specified value."""
        clock = GameClock()
        clock.reset_play_clock(25)
        assert clock.play_clock == 25

        clock.reset_play_clock()
        assert clock.play_clock == 40

    def test_copy(self):
        """Copy should create independent copy."""
        original = GameClock(quarter=3, time_remaining_seconds=500)
        copy = original.copy()

        assert copy.quarter == 3
        assert copy.time_remaining_seconds == 500

        # Modifying copy should not affect original
        copy.tick(100)
        assert original.time_remaining_seconds == 500
        assert copy.time_remaining_seconds == 400

    def test_to_dict_from_dict(self):
        """Serialization round-trip should preserve data."""
        original = GameClock(quarter=3, time_remaining_seconds=456, play_clock=25)
        data = original.to_dict()
        restored = GameClock.from_dict(data)

        assert restored.quarter == 3
        assert restored.time_remaining_seconds == 456
        assert restored.play_clock == 25


class TestScoreState:
    """Tests for ScoreState."""

    def test_default_values(self):
        """Default score should be 0-0."""
        score = ScoreState()
        assert score.home_score == 0
        assert score.away_score == 0

    def test_add_score_home(self):
        """Adding home score should work correctly."""
        score = ScoreState()
        score.add_score(is_home=True, points=7, quarter=1)
        assert score.home_score == 7
        assert score.away_score == 0
        assert score.home_by_quarter[0] == 7

    def test_add_score_away(self):
        """Adding away score should work correctly."""
        score = ScoreState()
        score.add_score(is_home=False, points=3, quarter=2)
        assert score.home_score == 0
        assert score.away_score == 3
        assert score.away_by_quarter[1] == 3

    def test_add_score_multiple_quarters(self):
        """Scores should accumulate across quarters."""
        score = ScoreState()
        score.add_score(is_home=True, points=7, quarter=1)
        score.add_score(is_home=True, points=3, quarter=2)
        score.add_score(is_home=False, points=14, quarter=2)
        score.add_score(is_home=True, points=7, quarter=3)

        assert score.home_score == 17
        assert score.away_score == 14
        assert score.home_by_quarter == [7, 3, 7, 0]
        assert score.away_by_quarter == [0, 14, 0, 0]

    def test_add_score_expands_quarters_for_overtime(self):
        """Quarter list should expand for overtime."""
        score = ScoreState()
        score.add_score(is_home=True, points=6, quarter=5)

        assert score.home_score == 6
        assert len(score.home_by_quarter) >= 5
        assert score.home_by_quarter[4] == 6

    def test_margin(self):
        """Margin should be positive when home is winning."""
        score = ScoreState(home_score=21, away_score=14)
        assert score.margin == 7

        score = ScoreState(home_score=10, away_score=17)
        assert score.margin == -7

    def test_is_tied(self):
        """is_tied should return True when scores equal."""
        score = ScoreState(home_score=14, away_score=14)
        assert score.is_tied is True

        score = ScoreState(home_score=14, away_score=7)
        assert score.is_tied is False

    def test_display(self):
        """Display should show HOME - AWAY format."""
        score = ScoreState(home_score=21, away_score=17)
        assert score.display == "21 - 17"

    def test_to_dict_from_dict(self):
        """Serialization round-trip should preserve data."""
        original = ScoreState(
            home_score=28,
            away_score=21,
            home_by_quarter=[7, 14, 7, 0],
            away_by_quarter=[7, 7, 7, 0],
        )
        data = original.to_dict()
        restored = ScoreState.from_dict(data)

        assert restored.home_score == 28
        assert restored.away_score == 21
        assert restored.home_by_quarter == [7, 14, 7, 0]
        assert restored.away_by_quarter == [7, 7, 7, 0]


class TestPossessionState:
    """Tests for PossessionState."""

    def test_default_timeouts(self):
        """Teams should start with 3 timeouts."""
        possession = PossessionState()
        assert possession.home_timeouts == 3
        assert possession.away_timeouts == 3

    def test_flip_possession(self):
        """Flip possession should switch team with ball."""
        home_id = uuid4()
        away_id = uuid4()
        possession = PossessionState(team_with_ball=home_id)

        possession.flip_possession(home_id, away_id)
        assert possession.team_with_ball == away_id

        possession.flip_possession(home_id, away_id)
        assert possession.team_with_ball == home_id

    def test_use_timeout_success(self):
        """Using timeout should decrement and return True."""
        possession = PossessionState()

        assert possession.use_timeout(is_home=True) is True
        assert possession.home_timeouts == 2

        assert possession.use_timeout(is_home=False) is True
        assert possession.away_timeouts == 2

    def test_use_timeout_failure(self):
        """Using timeout when none left should return False."""
        possession = PossessionState(home_timeouts=0)

        assert possession.use_timeout(is_home=True) is False
        assert possession.home_timeouts == 0

    def test_reset_timeouts(self):
        """Reset should restore all timeouts."""
        possession = PossessionState(home_timeouts=1, away_timeouts=0)
        possession.reset_timeouts()

        assert possession.home_timeouts == 3
        assert possession.away_timeouts == 3

    def test_to_dict_from_dict(self):
        """Serialization round-trip should preserve data."""
        home_id = uuid4()
        away_id = uuid4()
        original = PossessionState(
            team_with_ball=home_id,
            receiving_second_half=away_id,
            home_timeouts=2,
            away_timeouts=1,
        )
        data = original.to_dict()
        restored = PossessionState.from_dict(data)

        assert restored.team_with_ball == home_id
        assert restored.receiving_second_half == away_id
        assert restored.home_timeouts == 2
        assert restored.away_timeouts == 1


class TestGameState:
    """Tests for GameState."""

    def test_set_teams(self, home_team, away_team):
        """set_teams should store team references and IDs."""
        state = GameState()
        state.set_teams(home_team, away_team)

        assert state.home_team_id == home_team.id
        assert state.away_team_id == away_team.id
        assert state.home_team == home_team
        assert state.away_team == away_team

    def test_get_offensive_team(self, new_game_state):
        """get_offensive_team should return team with ball."""
        state = new_game_state

        # Home has ball
        state.possession.team_with_ball = state.home_team_id
        assert state.get_offensive_team() == state.home_team

        # Away has ball
        state.possession.team_with_ball = state.away_team_id
        assert state.get_offensive_team() == state.away_team

    def test_get_defensive_team(self, new_game_state):
        """get_defensive_team should return team without ball."""
        state = new_game_state

        # Home has ball, away is defense
        state.possession.team_with_ball = state.home_team_id
        assert state.get_defensive_team() == state.away_team

        # Away has ball, home is defense
        state.possession.team_with_ball = state.away_team_id
        assert state.get_defensive_team() == state.home_team

    def test_is_home_on_offense(self, new_game_state):
        """is_home_on_offense should return correct boolean."""
        state = new_game_state

        state.possession.team_with_ball = state.home_team_id
        assert state.is_home_on_offense() is True

        state.possession.team_with_ball = state.away_team_id
        assert state.is_home_on_offense() is False

    def test_is_game_over(self):
        """is_game_over should be True only for FINAL phase."""
        state = GameState(phase=GamePhase.FOURTH_QUARTER)
        assert state.is_game_over is False

        state.phase = GamePhase.FINAL
        assert state.is_game_over is True

    def test_current_quarter(self):
        """current_quarter should return phase's quarter number."""
        state = GameState(phase=GamePhase.FIRST_QUARTER)
        assert state.current_quarter == 1

        state.phase = GamePhase.THIRD_QUARTER
        assert state.current_quarter == 3

    def test_flip_possession(self, new_game_state):
        """flip_possession should switch team with ball."""
        state = new_game_state
        original_team = state.possession.team_with_ball

        state.flip_possession()

        assert state.possession.team_with_ball != original_team

    def test_add_score_for_offense(self, new_game_state):
        """add_score for offense should add to correct team."""
        state = new_game_state
        state.possession.team_with_ball = state.home_team_id
        state.phase = GamePhase.FIRST_QUARTER

        state.add_score(7, for_offense=True)
        assert state.score.home_score == 7
        assert state.score.away_score == 0

    def test_add_score_for_defense(self, new_game_state):
        """add_score for defense (e.g., pick-six) should add to correct team."""
        state = new_game_state
        state.possession.team_with_ball = state.home_team_id
        state.phase = GamePhase.FIRST_QUARTER

        state.add_score(6, for_offense=False)
        assert state.score.home_score == 0
        assert state.score.away_score == 6

    def test_add_play(self, new_game_state, completed_pass):
        """add_play should append to history."""
        state = new_game_state
        assert len(state.play_history) == 0

        state.add_play(completed_pass)
        assert len(state.play_history) == 1
        assert state.play_history[0] == completed_pass

    def test_to_dict_from_dict(self, new_game_state):
        """Serialization round-trip should preserve core data."""
        original = new_game_state
        original.phase = GamePhase.SECOND_QUARTER
        original.score.home_score = 14
        original.clock.tick(300)

        data = original.to_dict()
        restored = GameState.from_dict(data)

        assert restored.phase == GamePhase.SECOND_QUARTER
        assert restored.score.home_score == 14
        assert restored.clock.time_remaining_seconds == 600

    def test_str_representation(self, new_game_state):
        """String representation should be readable."""
        state = new_game_state
        state.score.home_score = 14
        state.score.away_score = 7

        str_repr = str(state)
        assert "14" in str_repr
        assert "7" in str_repr
