"""Tests for SimulationEngine."""

import pytest
from uuid import uuid4

from huddle.core.enums import PassType, PlayOutcome, PlayType, RunType
from huddle.core.models.field import DownState, FieldPosition
from huddle.core.models.game import GameClock, GamePhase, GameState
from huddle.core.models.play import DefensiveCall, PlayCall, PlayResult
from huddle.events.bus import EventBus
from huddle.simulation.engine import SimulationEngine, SimulationMode, SpecialTeamsPhase


class TestSimulationEngineInit:
    """Tests for SimulationEngine initialization."""

    def test_default_initialization(self):
        """Engine should initialize with defaults."""
        engine = SimulationEngine()
        assert engine.mode == SimulationMode.PLAY_BY_PLAY
        assert engine.event_bus is not None

    def test_custom_mode(self):
        """Engine should accept custom mode."""
        engine = SimulationEngine(mode=SimulationMode.FAST)
        assert engine.mode == SimulationMode.FAST

    def test_custom_event_bus(self):
        """Engine should accept custom event bus."""
        bus = EventBus()
        engine = SimulationEngine(event_bus=bus)
        assert engine.event_bus is bus


class TestCreateGame:
    """Tests for create_game()."""

    def test_creates_valid_game_state(self, home_team, away_team):
        """create_game should return valid GameState."""
        engine = SimulationEngine()
        game = engine.create_game(home_team, away_team)

        assert isinstance(game, GameState)
        assert game.home_team == home_team
        assert game.away_team == away_team

    def test_sets_first_quarter(self, home_team, away_team):
        """Game should start in first quarter."""
        engine = SimulationEngine()
        game = engine.create_game(home_team, away_team)

        assert game.phase == GamePhase.FIRST_QUARTER
        assert game.clock.quarter == 1
        assert game.clock.time_remaining_seconds == 900

    def test_sets_initial_score_zero(self, home_team, away_team):
        """Game should start 0-0."""
        engine = SimulationEngine()
        game = engine.create_game(home_team, away_team)

        assert game.score.home_score == 0
        assert game.score.away_score == 0

    def test_sets_kickoff_phase(self, home_team, away_team):
        """Game should be ready for opening kickoff."""
        engine = SimulationEngine()
        game = engine.create_game(home_team, away_team)

        assert engine._special_teams_phase == SpecialTeamsPhase.KICKOFF

    def test_coin_toss_sets_receiving_second_half(self, home_team, away_team):
        """Coin toss should determine who receives in 2nd half."""
        engine = SimulationEngine()
        game = engine.create_game(home_team, away_team)

        # One team should be set to receive 2nd half
        assert game.possession.receiving_second_half in [home_team.id, away_team.id]


class TestSimulatePlay:
    """Tests for simulate_play()."""

    def test_requires_both_teams(self):
        """simulate_play should raise if teams not set."""
        engine = SimulationEngine()
        game = GameState()  # No teams

        with pytest.raises(ValueError, match="both teams"):
            engine.simulate_play(
                game,
                PlayCall.run(RunType.INSIDE),
                DefensiveCall.cover_3(),
            )

    def test_returns_play_result(self, new_game_state):
        """simulate_play should return PlayResult."""
        engine = SimulationEngine()
        engine._special_teams_phase = SpecialTeamsPhase.NONE

        result = engine.simulate_play(
            new_game_state,
            PlayCall.run(RunType.INSIDE),
            DefensiveCall.cover_3(),
        )

        assert isinstance(result, PlayResult)

    def test_updates_clock(self, new_game_state):
        """simulate_play should consume time."""
        engine = SimulationEngine()
        engine._special_teams_phase = SpecialTeamsPhase.NONE

        initial_time = new_game_state.clock.time_remaining_seconds

        engine.simulate_play(
            new_game_state,
            PlayCall.run(RunType.INSIDE),
            DefensiveCall.cover_3(),
        )

        assert new_game_state.clock.time_remaining_seconds < initial_time


class TestApplyPlayResult:
    """Tests for _apply_play_result() state transitions."""

    def test_normal_play_advances_down(self, new_game_state):
        """Normal play should advance down and distance."""
        engine = SimulationEngine()
        new_game_state.down_state = DownState(
            down=1, yards_to_go=10, line_of_scrimmage=FieldPosition(25)
        )

        result = PlayResult(
            play_call=PlayCall.run(RunType.INSIDE),
            defensive_call=DefensiveCall.cover_3(),
            outcome=PlayOutcome.RUSH,
            yards_gained=4,
            time_elapsed_seconds=28,
        )

        engine._apply_play_result(new_game_state, result)

        assert new_game_state.down_state.down == 2
        assert new_game_state.down_state.yards_to_go == 6
        assert new_game_state.down_state.line_of_scrimmage.yard_line == 29

    def test_first_down_resets_downs(self, new_game_state):
        """Gaining first down should reset to 1st and 10."""
        engine = SimulationEngine()
        new_game_state.down_state = DownState(
            down=2, yards_to_go=7, line_of_scrimmage=FieldPosition(30)
        )

        result = PlayResult(
            play_call=PlayCall.pass_play(PassType.MEDIUM),
            defensive_call=DefensiveCall.cover_3(),
            outcome=PlayOutcome.COMPLETE,
            yards_gained=12,
            time_elapsed_seconds=6,
        )

        engine._apply_play_result(new_game_state, result)

        assert new_game_state.down_state.down == 1
        assert new_game_state.down_state.yards_to_go == 10
        assert new_game_state.down_state.line_of_scrimmage.yard_line == 42

    def test_touchdown_adds_six_points(self, new_game_state):
        """Touchdown should add 6 points and setup PAT."""
        engine = SimulationEngine()
        new_game_state.down_state = DownState(
            down=1, yards_to_go=5, line_of_scrimmage=FieldPosition(95)
        )

        result = PlayResult(
            play_call=PlayCall.run(RunType.INSIDE),
            defensive_call=DefensiveCall.cover_3(),
            outcome=PlayOutcome.TOUCHDOWN,
            yards_gained=5,
            is_touchdown=True,
            time_elapsed_seconds=4,
        )

        initial_score = new_game_state.score.home_score

        engine._apply_play_result(new_game_state, result)

        assert new_game_state.score.home_score == initial_score + 6
        assert engine._special_teams_phase == SpecialTeamsPhase.EXTRA_POINT

    def test_interception_flips_possession(self, new_game_state):
        """Interception should change possession."""
        engine = SimulationEngine()
        original_possession = new_game_state.possession.team_with_ball

        result = PlayResult(
            play_call=PlayCall.pass_play(PassType.DEEP),
            defensive_call=DefensiveCall.cover_3(),
            outcome=PlayOutcome.INTERCEPTION,
            yards_gained=0,
            is_turnover=True,
            time_elapsed_seconds=4,
        )

        engine._apply_play_result(new_game_state, result)

        assert new_game_state.possession.team_with_ball != original_possession

    def test_fumble_flips_possession(self, new_game_state):
        """Fumble should change possession."""
        engine = SimulationEngine()
        original_possession = new_game_state.possession.team_with_ball

        result = PlayResult(
            play_call=PlayCall.run(RunType.INSIDE),
            defensive_call=DefensiveCall.cover_3(),
            outcome=PlayOutcome.FUMBLE_LOST,
            yards_gained=3,
            is_turnover=True,
            time_elapsed_seconds=5,
        )

        engine._apply_play_result(new_game_state, result)

        assert new_game_state.possession.team_with_ball != original_possession

    def test_field_goal_good_adds_three_points(self, new_game_state):
        """Made field goal should add 3 points."""
        engine = SimulationEngine()
        new_game_state.down_state = DownState(
            down=4, yards_to_go=8, line_of_scrimmage=FieldPosition(75)
        )

        result = PlayResult(
            play_call=PlayCall.field_goal(),
            defensive_call=DefensiveCall.cover_3(),
            outcome=PlayOutcome.FIELD_GOAL_GOOD,
            yards_gained=0,
            time_elapsed_seconds=5,
        )

        initial_score = new_game_state.score.home_score

        engine._apply_play_result(new_game_state, result)

        assert new_game_state.score.home_score == initial_score + 3
        assert engine._special_teams_phase == SpecialTeamsPhase.KICKOFF

    def test_field_goal_miss_gives_ball_to_opponent(self, new_game_state):
        """Missed field goal should flip possession and setup kickoff."""
        engine = SimulationEngine()
        original_possession = new_game_state.possession.team_with_ball

        result = PlayResult(
            play_call=PlayCall.field_goal(),
            defensive_call=DefensiveCall.cover_3(),
            outcome=PlayOutcome.FIELD_GOAL_MISSED,
            yards_gained=0,
            time_elapsed_seconds=5,
        )

        engine._apply_play_result(new_game_state, result)

        assert new_game_state.possession.team_with_ball != original_possession

    def test_punt_flips_possession(self, new_game_state):
        """Punt should change possession."""
        engine = SimulationEngine()
        original_possession = new_game_state.possession.team_with_ball

        result = PlayResult(
            play_call=PlayCall.punt(),
            defensive_call=DefensiveCall.cover_3(),
            outcome=PlayOutcome.PUNT_RESULT,
            yards_gained=45,
            time_elapsed_seconds=5,
        )

        engine._apply_play_result(new_game_state, result)

        assert new_game_state.possession.team_with_ball != original_possession


class TestPenaltyHandling:
    """Tests for penalty result handling."""

    def test_offensive_penalty_moves_back(self, new_game_state):
        """Offensive penalty should move ball backward."""
        engine = SimulationEngine()
        new_game_state.down_state = DownState(
            down=1, yards_to_go=10, line_of_scrimmage=FieldPosition(30)
        )

        result = PlayResult(
            play_call=PlayCall.run(RunType.INSIDE),
            defensive_call=DefensiveCall.cover_3(),
            outcome=PlayOutcome.PENALTY_OFFENSE,
            yards_gained=0,
            penalty_on_offense=True,
            penalty_yards=10,
            penalty_type="HOLDING",
            time_elapsed_seconds=0,
        )

        engine._apply_play_result(new_game_state, result)

        assert new_game_state.down_state.line_of_scrimmage.yard_line == 20
        assert new_game_state.down_state.down == 1  # Replay down

    def test_defensive_penalty_moves_forward(self, new_game_state):
        """Defensive penalty should move ball forward."""
        engine = SimulationEngine()
        new_game_state.down_state = DownState(
            down=2, yards_to_go=8, line_of_scrimmage=FieldPosition(30)
        )

        result = PlayResult(
            play_call=PlayCall.pass_play(PassType.SHORT),
            defensive_call=DefensiveCall.cover_3(),
            outcome=PlayOutcome.PENALTY_DEFENSE,
            yards_gained=0,
            penalty_on_offense=False,
            penalty_yards=15,
            penalty_type="PASS_INTERFERENCE",
            time_elapsed_seconds=0,
        )

        engine._apply_play_result(new_game_state, result)

        # Should be at 45 yard line (30 + 15)
        assert new_game_state.down_state.line_of_scrimmage.yard_line == 45


class TestQuarterManagement:
    """Tests for quarter end handling."""

    def test_quarter_end_advances_phase(self, new_game_state):
        """End of quarter should advance to next phase."""
        engine = SimulationEngine()
        new_game_state.clock.time_remaining_seconds = 0

        engine._check_quarter_end(new_game_state)

        assert new_game_state.phase == GamePhase.SECOND_QUARTER

    def test_second_quarter_end_goes_to_halftime(self, new_game_state):
        """End of Q2 should go to halftime."""
        engine = SimulationEngine()
        new_game_state.phase = GamePhase.SECOND_QUARTER
        new_game_state.clock = GameClock(quarter=2, time_remaining_seconds=0)

        engine._check_quarter_end(new_game_state)

        assert new_game_state.phase == GamePhase.HALFTIME

    def test_fourth_quarter_end_is_final_when_not_tied(self, new_game_state):
        """End of Q4 should end game when not tied."""
        engine = SimulationEngine()
        new_game_state.phase = GamePhase.FOURTH_QUARTER
        new_game_state.clock = GameClock(quarter=4, time_remaining_seconds=0)
        new_game_state.score.home_score = 21  # Not tied

        engine._check_quarter_end(new_game_state)

        assert new_game_state.phase == GamePhase.FINAL

    def test_fourth_quarter_end_goes_to_overtime_when_tied(self, new_game_state):
        """End of Q4 should go to overtime when tied."""
        engine = SimulationEngine()
        new_game_state.phase = GamePhase.FOURTH_QUARTER
        new_game_state.clock = GameClock(quarter=4, time_remaining_seconds=0)
        # Score is 0-0 (tied) by default

        engine._check_quarter_end(new_game_state)

        assert new_game_state.phase == GamePhase.OVERTIME
        assert new_game_state.clock.quarter == 5
        assert new_game_state.clock.time_remaining_seconds == 600


class TestHalftimeHandling:
    """Tests for halftime procedures."""

    def test_halftime_resets_timeouts(self, new_game_state):
        """Halftime should reset timeouts."""
        engine = SimulationEngine()
        new_game_state.possession.home_timeouts = 1
        new_game_state.possession.away_timeouts = 0

        engine._handle_halftime(new_game_state)

        assert new_game_state.possession.home_timeouts == 3
        assert new_game_state.possession.away_timeouts == 3

    def test_halftime_starts_third_quarter(self, new_game_state):
        """Halftime should transition to Q3."""
        engine = SimulationEngine()

        engine._handle_halftime(new_game_state)

        assert new_game_state.phase == GamePhase.THIRD_QUARTER
        assert new_game_state.clock.quarter == 3
        assert new_game_state.clock.time_remaining_seconds == 900

    def test_halftime_sets_up_kickoff(self, new_game_state):
        """Halftime should setup second half kickoff."""
        engine = SimulationEngine()

        engine._handle_halftime(new_game_state)

        assert engine._special_teams_phase == SpecialTeamsPhase.KICKOFF


class TestAIPlayCalling:
    """Tests for AI play calling."""

    def test_fourth_down_punt_when_deep(self, new_game_state):
        """AI should punt on 4th down in own territory."""
        engine = SimulationEngine()
        new_game_state.down_state = DownState(
            down=4, yards_to_go=10, line_of_scrimmage=FieldPosition(25)
        )

        call = engine._get_ai_offensive_call(new_game_state)

        assert call.play_type == PlayType.PUNT

    def test_fourth_down_fg_in_range(self, new_game_state):
        """AI should kick FG when in range on 4th down."""
        engine = SimulationEngine()
        new_game_state.down_state = DownState(
            down=4, yards_to_go=8, line_of_scrimmage=FieldPosition(75)
        )

        call = engine._get_ai_offensive_call(new_game_state)

        assert call.play_type == PlayType.FIELD_GOAL

    def test_defensive_call_returns_valid_call(self, new_game_state):
        """AI should return valid defensive call."""
        engine = SimulationEngine()

        call = engine._get_ai_defensive_call(new_game_state)

        assert isinstance(call, DefensiveCall)


class TestTwoMinuteWarning:
    """Tests for two-minute warning handling."""

    def test_two_minute_warning_stops_clock(self, new_game_state):
        """Crossing 2:00 should trigger clock stoppage."""
        engine = SimulationEngine()
        new_game_state.phase = GamePhase.FOURTH_QUARTER
        new_game_state.clock = GameClock(quarter=4, time_remaining_seconds=125)
        new_game_state.down_state = DownState(
            down=1, yards_to_go=10, line_of_scrimmage=FieldPosition(50)
        )

        result = PlayResult(
            play_call=PlayCall.run(RunType.INSIDE),
            defensive_call=DefensiveCall.cover_3(),
            outcome=PlayOutcome.RUSH,
            yards_gained=5,
            time_elapsed_seconds=30,  # Should cross 2:00 mark
        )

        engine._apply_play_result(new_game_state, result)

        assert result.clock_stopped is True
        assert result.clock_stop_reason == "two_minute_warning"


class TestTurnoverOnDowns:
    """Tests for turnover on downs."""

    def test_handles_turnover_on_downs(self, new_game_state):
        """Should flip possession and set field position."""
        engine = SimulationEngine()
        original_possession = new_game_state.possession.team_with_ball
        new_game_state.down_state = DownState(
            down=5,  # After failed 4th down
            yards_to_go=2,
            line_of_scrimmage=FieldPosition(60)
        )

        engine._handle_turnover_on_downs(new_game_state)

        assert new_game_state.possession.team_with_ball != original_possession
        assert new_game_state.down_state.down == 1
        assert new_game_state.down_state.yards_to_go == 10
        # 60 from own perspective = 40 from opponent's = opponent at their 40
        assert new_game_state.down_state.line_of_scrimmage.yard_line == 40
