"""Main simulation engine."""

import random
from datetime import datetime
from enum import Enum, auto
from typing import Optional
from uuid import UUID

from huddle.core.enums import (
    DefensiveScheme,
    Formation,
    PassType,
    PersonnelPackage,
    PlayOutcome,
    PlayType,
    RunType,
)
from huddle.core.models.field import DownState, FieldPosition
from huddle.core.models.game import GameClock, GamePhase, GameState, PossessionState, ScoreState
from huddle.core.models.play import DefensiveCall, DriveResult, PlayCall, PlayResult
from huddle.core.models.team import Team
from huddle.events.bus import EventBus
from huddle.events.types import (
    DriveCompletedEvent,
    GameEndEvent,
    PlayCompletedEvent,
    QuarterEndEvent,
    ScoringEvent,
    TurnoverEvent,
)
from huddle.simulation.resolvers.base import DriveResolver, PlayResolver
from huddle.simulation.resolvers.statistical import StatisticalPlayResolver


class SimulationMode(Enum):
    """Simulation detail level."""

    FAST = auto()  # Drive-level simulation
    PLAY_BY_PLAY = auto()  # Each play simulated


class SpecialTeamsPhase(Enum):
    """Current special teams situation."""

    NONE = auto()
    KICKOFF = auto()
    EXTRA_POINT = auto()
    TWO_POINT = auto()


class SimulationEngine:
    """
    Central orchestrator for game simulation.

    Manages game state and delegates to appropriate resolvers.
    Emits events for UI and logging integration.
    """

    def __init__(
        self,
        mode: SimulationMode = SimulationMode.PLAY_BY_PLAY,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        """
        Initialize simulation engine.

        Args:
            mode: Simulation detail level
            event_bus: Event bus for notifications (creates new if None)
        """
        self.mode = mode
        self.event_bus = event_bus or EventBus()

        # Initialize resolvers
        self._play_resolver: PlayResolver = StatisticalPlayResolver()
        self._drive_resolver: Optional[DriveResolver] = None

        # Special teams state
        self._special_teams_phase = SpecialTeamsPhase.NONE
        self._scoring_team_id: Optional[UUID] = None

        # Overtime state
        self._ot_first_possession: bool = False
        self._ot_first_team: Optional[UUID] = None

    def create_game(self, home_team: Team, away_team: Team) -> GameState:
        """
        Create a new game between two teams.

        Args:
            home_team: Home team
            away_team: Away team

        Returns:
            Initialized GameState ready for simulation
        """
        game = GameState()
        game.set_teams(home_team, away_team)

        # Coin toss - random team receives first
        if random.random() < 0.5:
            receiving_team = away_team.id
            kicking_team = home_team.id
            game.possession.receiving_second_half = home_team.id
        else:
            receiving_team = home_team.id
            kicking_team = away_team.id
            game.possession.receiving_second_half = away_team.id

        # Set kicking team as "possessing" for kickoff
        game.possession.team_with_ball = kicking_team

        # Mark that we need to do opening kickoff
        self._special_teams_phase = SpecialTeamsPhase.KICKOFF

        game.phase = GamePhase.FIRST_QUARTER
        game.clock = GameClock(quarter=1, time_remaining_seconds=900)

        # Temporary field position (will be set after kickoff)
        game.down_state = DownState(
            down=1, yards_to_go=10, line_of_scrimmage=FieldPosition(35)
        )

        return game

    def simulate_play(
        self,
        game_state: GameState,
        offensive_call: PlayCall,
        defensive_call: DefensiveCall,
    ) -> PlayResult:
        """
        Simulate a single play.

        Args:
            game_state: Current game state
            offensive_call: Offensive play call
            defensive_call: Defensive play call

        Returns:
            PlayResult with outcome details
        """
        offense = game_state.get_offensive_team()
        defense = game_state.get_defensive_team()

        if not offense or not defense:
            raise ValueError("Game state must have both teams set")

        # Resolve the play
        result = self._play_resolver.resolve_play(
            game_state, offense, defense, offensive_call, defensive_call
        )

        # Capture possession BEFORE applying result (which may flip possession)
        offense_is_home = game_state.possession.team_with_ball == game_state.home_team_id

        # Apply result to game state
        self._apply_play_result(game_state, result)

        # Emit event with original possession info
        self._emit_play_event(game_state, result, offense_is_home)

        return result

    def simulate_play_with_ai(self, game_state: GameState) -> PlayResult:
        """
        Simulate a play with AI-selected calls for both teams.
        Handles special teams phases (kickoffs, PATs, 2pt).

        Args:
            game_state: Current game state

        Returns:
            PlayResult with outcome details
        """
        # Handle special teams phases
        if self._special_teams_phase == SpecialTeamsPhase.KICKOFF:
            return self._handle_kickoff(game_state)
        elif self._special_teams_phase == SpecialTeamsPhase.EXTRA_POINT:
            return self._handle_pat_decision(game_state)
        elif self._special_teams_phase == SpecialTeamsPhase.TWO_POINT:
            return self._handle_two_point(game_state)

        # Normal play
        off_call = self._get_ai_offensive_call(game_state)
        def_call = self._get_ai_defensive_call(game_state)
        return self.simulate_play(game_state, off_call, def_call)

    def _handle_kickoff(self, game_state: GameState) -> PlayResult:
        """Handle a kickoff play."""
        kicking_team = game_state.get_offensive_team()
        receiving_team = game_state.get_defensive_team()

        call = PlayCall.kickoff()
        def_call = DefensiveCall.cover_3()  # Kickoff return coverage

        result = self._play_resolver.resolve_play(
            game_state, kicking_team, receiving_team, call, def_call
        )

        # Emit the play event before changing possession
        offense_is_home = game_state.possession.team_with_ball == game_state.home_team_id

        # Flip possession to receiving team
        game_state.flip_possession()

        # Set field position based on result
        if result.outcome == PlayOutcome.TOUCHDOWN:
            # Kickoff return TD - score and setup for kickoff going other way
            game_state.add_score(6, for_offense=True)
            self._scoring_team_id = game_state.possession.team_with_ball
            self._special_teams_phase = SpecialTeamsPhase.EXTRA_POINT
            game_state.down_state = DownState(
                down=1, yards_to_go=10, line_of_scrimmage=FieldPosition(15)
            )
        else:
            # Normal kickoff - set up for receiving team's drive
            starting_yard = result.yards_gained
            game_state.down_state = DownState(
                down=1, yards_to_go=10, line_of_scrimmage=FieldPosition(starting_yard)
            )
            self._special_teams_phase = SpecialTeamsPhase.NONE

        # Update clock
        game_state.clock.tick(result.time_elapsed_seconds)

        self._emit_play_event(game_state, result, offense_is_home)

        return result

    def _handle_pat_decision(self, game_state: GameState) -> PlayResult:
        """Handle extra point / 2-point conversion decision."""
        offense = game_state.get_offensive_team()
        defense = game_state.get_defensive_team()

        # AI decision: go for 2 in certain situations
        go_for_two = self._should_go_for_two(game_state)

        if go_for_two:
            # Randomly pick run or pass for 2pt
            if random.random() < 0.6:
                call = PlayCall.two_point(pass_type=PassType.SHORT)
            else:
                call = PlayCall.two_point(run_type=RunType.INSIDE)
        else:
            call = PlayCall.extra_point()

        def_call = DefensiveCall.cover_3()

        result = self._play_resolver.resolve_play(
            game_state, offense, defense, call, def_call
        )

        offense_is_home = game_state.possession.team_with_ball == game_state.home_team_id

        # Add points
        if result.points_scored > 0:
            game_state.add_score(result.points_scored, for_offense=True)
            self._emit_scoring_event(
                game_state,
                result.points_scored,
                "XP" if call.play_type == PlayType.EXTRA_POINT else "2PT",
                self._scoring_team_id
            )

        # Setup for kickoff
        game_state.flip_possession()  # Kicking team now has "possession"
        game_state.down_state = DownState(
            down=1, yards_to_go=10, line_of_scrimmage=FieldPosition(35)
        )
        self._special_teams_phase = SpecialTeamsPhase.KICKOFF

        game_state.clock.tick(result.time_elapsed_seconds)

        self._emit_play_event(game_state, result, offense_is_home)

        return result

    def _handle_two_point(self, game_state: GameState) -> PlayResult:
        """Handle two-point conversion attempt."""
        # This is called if we explicitly set TWO_POINT phase
        # Usually _handle_pat_decision handles both
        return self._handle_pat_decision(game_state)

    def _should_go_for_two(self, game_state: GameState) -> bool:
        """Determine if team should go for 2-point conversion."""
        offense = game_state.get_offensive_team()
        aggression = offense.aggression if offense else 0.5

        score_diff = game_state.score.margin
        if game_state.is_home_on_offense():
            score_diff = score_diff
        else:
            score_diff = -score_diff

        quarter = game_state.current_quarter
        time_left = game_state.clock.time_remaining_seconds

        # Go for 2 in these situations:
        # - Down by 2 (makes it a tie instead of down 1)
        # - Down by 5 (TD + 2 = 7 to tie instead of 6)
        # - Late in game and need points
        # - High aggression coach

        if quarter == 4 and time_left < 300:  # Last 5 minutes
            if score_diff in [-2, -5, -9, -12, -16]:
                return True

        # Random chance based on aggression
        if aggression > 0.7 and random.random() < 0.15:
            return True

        return False

    def simulate_drive(self, game_state: GameState) -> list[PlayResult]:
        """
        Simulate plays until the drive ends.

        A drive ends on:
        - Touchdown
        - Field goal (made or missed)
        - Punt
        - Turnover
        - Turnover on downs
        - End of half

        Args:
            game_state: Current game state

        Returns:
            List of PlayResults for the drive
        """
        results = []
        starting_possession = game_state.possession.team_with_ball

        while True:
            # Check if drive should end
            if self._should_end_drive(game_state, starting_possession):
                break

            # Simulate next play
            result = self.simulate_play_with_ai(game_state)
            results.append(result)

            # Check for scoring or turnover
            if result.is_touchdown or result.is_turnover:
                break

            # Check for turnover on downs
            if game_state.down_state.down > 4:
                self._handle_turnover_on_downs(game_state)
                break

        return results

    def _handle_turnover_on_downs(self, game_state: GameState) -> None:
        """Handle turnover on downs."""
        game_state.flip_possession()
        # Opponent takes over at spot of the ball
        new_los = FieldPosition(
            100 - game_state.down_state.line_of_scrimmage.yard_line
        )
        game_state.down_state = DownState(
            down=1,
            yards_to_go=10,
            line_of_scrimmage=new_los,
        )

    def simulate_game(self, game_state: GameState) -> GameState:
        """
        Simulate an entire game to completion.

        Args:
            game_state: Game state (usually from create_game)

        Returns:
            Final game state
        """
        while not game_state.is_game_over:
            # Simulate a drive
            self.simulate_drive(game_state)

            # Handle end of quarters
            self._check_quarter_end(game_state)

            # Handle halftime
            if game_state.phase == GamePhase.HALFTIME:
                self._handle_halftime(game_state)

        # Emit game end event
        self._emit_game_end_event(game_state)

        return game_state

    def _apply_play_result(self, game_state: GameState, result: PlayResult) -> None:
        """Apply play result to game state."""
        # Check for two-minute warning BEFORE updating clock
        was_before_2min = game_state.clock.time_remaining_seconds > 120

        # Update clock
        game_state.clock.tick(result.time_elapsed_seconds)

        # Check for two-minute warning
        if was_before_2min and game_state.clock.is_two_minute_warning:
            # Two-minute warning triggers clock stoppage
            # This would be visible in the UI, but the clock just crossed 2:00
            result.clock_stopped = True
            result.clock_stop_reason = "two_minute_warning"

        # Handle penalty outcomes
        if result.outcome in (PlayOutcome.PENALTY_OFFENSE, PlayOutcome.PENALTY_DEFENSE):
            self._apply_penalty_result(game_state, result)
            game_state.add_play(result)
            return

        # Handle special outcomes first
        if result.is_safety:
            # Defense scores 2 points
            defensive_team = game_state.get_defensive_team()
            self._scoring_team_id = defensive_team.id if defensive_team else None
            game_state.add_score(2, for_offense=False)
            self._emit_scoring_event(game_state, 2, "SAFETY", self._scoring_team_id)
            # Offense must free kick from own 20 after safety
            # Possession stays with offense for the free kick, then flips
            game_state.down_state = DownState(
                down=1, yards_to_go=10, line_of_scrimmage=FieldPosition(20)
            )
            self._special_teams_phase = SpecialTeamsPhase.KICKOFF
            game_state.add_play(result)
            return

        if result.is_touchdown:
            self._scoring_team_id = game_state.possession.team_with_ball
            game_state.add_score(6)
            self._emit_scoring_event(game_state, 6, "TD", self._scoring_team_id)

            # Check for OT sudden death - TD on first possession ends game
            if game_state.phase == GamePhase.OVERTIME and self._ot_first_possession:
                game_state.phase = GamePhase.FINAL
                game_state.add_play(result)
                return

            # Setup for PAT
            game_state.down_state = DownState(
                down=1, yards_to_go=10, line_of_scrimmage=FieldPosition(15)
            )
            self._special_teams_phase = SpecialTeamsPhase.EXTRA_POINT
            return

        if result.is_turnover:
            # Check for defensive touchdown on turnover return
            if result.is_touchdown:
                # Defensive TD - defense scores 6, then kicks off
                defensive_team = game_state.get_defensive_team()
                self._scoring_team_id = defensive_team.id if defensive_team else None
                game_state.add_score(6, for_offense=False)
                self._emit_scoring_event(game_state, 6, "DEF_TD", self._scoring_team_id)
                # Flip possession so scoring team kicks off
                game_state.flip_possession()
                game_state.down_state = DownState(
                    down=1, yards_to_go=10, line_of_scrimmage=FieldPosition(15)
                )
                self._special_teams_phase = SpecialTeamsPhase.EXTRA_POINT
                game_state.add_play(result)
                return

            # Normal turnover - flip possession, use return yards for field position
            game_state.flip_possession()

            # In OT, turnover ends first possession (opponent now has chance)
            if game_state.phase == GamePhase.OVERTIME and self._ot_first_possession:
                self._ot_first_possession = False

            # Calculate new field position based on where return ended
            # yards_gained represents total yards from original LOS (int_spot + return)
            original_los = game_state.down_state.line_of_scrimmage.yard_line
            # After flip, we need to convert: return endpoint from new team's perspective
            return_endpoint = original_los + result.yards_gained
            new_los = 100 - return_endpoint
            new_los = max(1, min(99, new_los))

            game_state.down_state = DownState(
                down=1, yards_to_go=10, line_of_scrimmage=FieldPosition(new_los)
            )
            self._emit_turnover_event(game_state, result)
            game_state.add_play(result)
            return

        if result.outcome == PlayOutcome.PUNT_RESULT:
            game_state.flip_possession()
            # Flip field position
            new_los = FieldPosition(
                100 - (game_state.down_state.line_of_scrimmage.yard_line - result.yards_gained)
            )
            new_los.yard_line = max(20, min(80, new_los.yard_line))  # Touchback/fair catch
            game_state.down_state = DownState(
                down=1, yards_to_go=10, line_of_scrimmage=new_los
            )
            return

        if result.outcome in (PlayOutcome.FIELD_GOAL_GOOD, PlayOutcome.FIELD_GOAL_MISSED):
            if result.outcome == PlayOutcome.FIELD_GOAL_GOOD:
                self._scoring_team_id = game_state.possession.team_with_ball
                game_state.add_score(3)
                self._emit_scoring_event(game_state, 3, "FG", self._scoring_team_id)

                # OT rules: FG on first possession gives opponent a chance
                # FG on second possession (or later) ends game if ahead
                if game_state.phase == GamePhase.OVERTIME:
                    if not self._ot_first_possession:
                        # Second possession or later - FG wins if now ahead
                        game_state.phase = GamePhase.FINAL
                        game_state.add_play(result)
                        return
                    # First possession FG - opponent gets a chance
                    self._ot_first_possession = False

            # Setup for kickoff (or give opponent ball in OT after FG)
            game_state.flip_possession()
            game_state.down_state = DownState(
                down=1, yards_to_go=10, line_of_scrimmage=FieldPosition(35)
            )
            self._special_teams_phase = SpecialTeamsPhase.KICKOFF
            return

        # Normal play - update down and distance
        new_down_state, is_first_down = game_state.down_state.advance(result.yards_gained)
        game_state.down_state = new_down_state

        # Add to history
        game_state.add_play(result)

    def _apply_penalty_result(self, game_state: GameState, result: PlayResult) -> None:
        """Apply penalty result to game state."""
        from huddle.core.enums import PenaltyType

        current_los = game_state.down_state.line_of_scrimmage.yard_line
        current_down = game_state.down_state.down
        current_ytg = game_state.down_state.yards_to_go

        penalty_type_name = result.penalty_type
        penalty_yards = result.penalty_yards
        is_on_offense = result.penalty_on_offense

        # Try to get PenaltyType enum for property checks
        try:
            penalty_type = PenaltyType[penalty_type_name] if penalty_type_name else None
        except (KeyError, TypeError):
            penalty_type = None

        if is_on_offense:
            # Offensive penalty - move back
            new_los = max(1, current_los - penalty_yards)

            # Check for pre-snap penalty (repeat down)
            is_pre_snap = penalty_type and penalty_type.is_pre_snap if penalty_type else False

            if is_pre_snap:
                # Repeat down, add yards to go
                new_ytg = min(current_ytg + penalty_yards, 99 - new_los)
                new_down = current_down
            else:
                # Loss of down for OPI
                is_loss_of_down = penalty_type and penalty_type.is_loss_of_down if penalty_type else False
                if is_loss_of_down:
                    new_down = current_down + 1
                    new_ytg = current_ytg + penalty_yards
                else:
                    # Normal offensive penalty - replay down with added distance
                    new_down = current_down
                    new_ytg = current_ytg + penalty_yards

            game_state.down_state = DownState(
                down=new_down,
                yards_to_go=new_ytg,
                line_of_scrimmage=FieldPosition(new_los),
            )
        else:
            # Defensive penalty - move forward
            new_los = min(99, current_los + penalty_yards)

            # Check for automatic first down
            is_auto_first = penalty_type and penalty_type.is_automatic_first_down if penalty_type else False

            if is_auto_first or penalty_yards >= current_ytg:
                # First down
                new_down = 1
                new_ytg = min(10, 100 - new_los)
            else:
                # Replay down with fewer yards to go
                new_down = current_down
                new_ytg = current_ytg - penalty_yards

            game_state.down_state = DownState(
                down=new_down,
                yards_to_go=new_ytg,
                line_of_scrimmage=FieldPosition(new_los),
            )

    def _check_quarter_end(self, game_state: GameState) -> None:
        """Check and handle end of quarter."""
        if not game_state.clock.is_quarter_over:
            return

        quarter = game_state.current_quarter

        # Emit quarter end event
        self.event_bus.emit(
            QuarterEndEvent(
                game_id=game_state.id,
                quarter=quarter,
                home_score=game_state.score.home_score,
                away_score=game_state.score.away_score,
                quarter_ended=quarter,
            )
        )

        # Handle end of Q4 - check for tie
        if game_state.phase == GamePhase.FOURTH_QUARTER:
            if game_state.score.is_tied:
                self._handle_overtime_start(game_state)
                return
            else:
                game_state.phase = GamePhase.FINAL
                return

        # Handle end of overtime
        if game_state.phase == GamePhase.OVERTIME:
            # Regular season: game can end in tie after one OT
            # For now, just end the game
            game_state.phase = GamePhase.FINAL
            return

        # Advance to next phase for Q1-Q3
        phase_progression = {
            GamePhase.FIRST_QUARTER: GamePhase.SECOND_QUARTER,
            GamePhase.SECOND_QUARTER: GamePhase.HALFTIME,
            GamePhase.THIRD_QUARTER: GamePhase.FOURTH_QUARTER,
        }

        next_phase = phase_progression.get(game_state.phase)
        if next_phase:
            game_state.phase = next_phase
            if next_phase not in (GamePhase.HALFTIME, GamePhase.FINAL):
                game_state.clock.next_quarter()

    def _handle_overtime_start(self, game_state: GameState) -> None:
        """Set up overtime period."""
        game_state.phase = GamePhase.OVERTIME
        game_state.clock = GameClock(
            quarter=5,
            time_remaining_seconds=600  # 10-minute OT period (NFL rules)
        )
        # Each team gets 2 timeouts in OT
        game_state.possession.home_timeouts = 2
        game_state.possession.away_timeouts = 2

        # Coin toss for OT - winner can choose to receive or defer
        # Simplified: random team receives
        if random.random() < 0.5:
            receiving_team = game_state.home_team_id
        else:
            receiving_team = game_state.away_team_id

        # Set up so kicking team "has the ball" for kickoff setup
        game_state.possession.team_with_ball = receiving_team
        game_state.flip_possession()  # Now kicking team has ball for kickoff

        game_state.down_state = DownState(
            down=1, yards_to_go=10, line_of_scrimmage=FieldPosition(35)
        )
        self._special_teams_phase = SpecialTeamsPhase.KICKOFF
        self._ot_first_possession = True  # Track for sudden death rules
        self._ot_first_team = receiving_team

    def _handle_halftime(self, game_state: GameState) -> None:
        """Handle halftime procedures."""
        # Switch possession to team receiving second half
        game_state.possession.team_with_ball = game_state.possession.receiving_second_half
        game_state.possession.reset_timeouts()

        # Flip possession so kicking team "has the ball" for kickoff
        game_state.flip_possession()

        # Setup for second half kickoff
        game_state.down_state = DownState(
            down=1, yards_to_go=10, line_of_scrimmage=FieldPosition(35)
        )
        self._special_teams_phase = SpecialTeamsPhase.KICKOFF

        # Move to third quarter
        game_state.phase = GamePhase.THIRD_QUARTER
        game_state.clock = GameClock(quarter=3, time_remaining_seconds=900)

    def _should_end_drive(self, game_state: GameState, starting_possession) -> bool:
        """Check if drive should end."""
        # Don't end during special teams
        if self._special_teams_phase != SpecialTeamsPhase.NONE:
            return False

        # Possession changed
        if game_state.possession.team_with_ball != starting_possession:
            return True

        # Quarter/half ended
        if game_state.clock.is_quarter_over:
            return True

        # Game over
        if game_state.is_game_over:
            return True

        return False

    def _get_ai_offensive_call(self, game_state: GameState) -> PlayCall:
        """Get AI offensive play call based on situation."""
        offense = game_state.get_offensive_team()
        down = game_state.down_state.down
        yards_to_go = game_state.down_state.yards_to_go
        field_pos = game_state.down_state.line_of_scrimmage
        quarter = game_state.current_quarter
        time_left = game_state.clock.time_remaining_seconds
        score_margin = game_state.score.margin
        if not game_state.is_home_on_offense():
            score_margin = -score_margin

        # 4th down decisions
        if down == 4:
            return self._get_fourth_down_call(
                game_state, offense, yards_to_go, field_pos, quarter, time_left, score_margin
            )

        # Situational play calling
        run_tendency = offense.run_tendency if offense else 0.5

        # Short yardage - more runs
        if yards_to_go <= 3:
            run_tendency += 0.2

        # Long yardage - more passes
        if yards_to_go >= 7:
            run_tendency -= 0.2

        # Red zone adjustments
        if field_pos.yard_line >= 90:
            run_tendency += 0.1

        # Two-minute drill - more passes
        if quarter in (2, 4) and time_left < 120 and score_margin < 0:
            run_tendency -= 0.3

        # Protecting lead late - more runs
        if quarter == 4 and time_left < 300 and score_margin > 0:
            run_tendency += 0.2

        run_tendency = max(0.2, min(0.8, run_tendency))

        # Select formation and personnel based on situation
        formation, personnel = self._select_formation_and_personnel(
            game_state, yards_to_go, field_pos, run_tendency
        )

        if random.random() < run_tendency:
            # Run play
            run_types = [RunType.INSIDE, RunType.OUTSIDE, RunType.DRAW]
            weights = [0.5, 0.35, 0.15]
            run_type = random.choices(run_types, weights=weights)[0]
            return PlayCall.run(run_type, formation, personnel)
        else:
            # Pass play
            if yards_to_go <= 5:
                pass_type = random.choice([PassType.SHORT, PassType.SCREEN])
            elif yards_to_go <= 12:
                pass_type = random.choice([PassType.SHORT, PassType.MEDIUM])
            else:
                pass_type = random.choice([PassType.MEDIUM, PassType.DEEP])
            return PlayCall.pass_play(pass_type, formation, personnel)

    def _get_fourth_down_call(
        self,
        game_state: GameState,
        offense: Team,
        yards_to_go: int,
        field_pos: FieldPosition,
        quarter: int,
        time_left: int,
        score_margin: int,
    ) -> PlayCall:
        """Get play call for 4th down situations."""
        aggression = offense.aggression if offense else 0.5

        # FG range: inside opponent's 35 (52 yard attempt)
        in_fg_range = field_pos.yard_line >= 65

        # Factors that increase going for it
        go_for_it = False

        # Short yardage in opponent's territory
        if yards_to_go <= 1 and field_pos.yard_line >= 50:
            go_for_it = random.random() < (0.4 + aggression * 0.3)

        # 4th and short at opponent's 35-40 (no man's land)
        if yards_to_go <= 3 and 60 <= field_pos.yard_line < 65:
            go_for_it = random.random() < (0.3 + aggression * 0.3)

        # Desperate situations
        if quarter == 4:
            # Down by more than 3 with less than 5 minutes
            if score_margin < -3 and time_left < 300:
                if field_pos.yard_line >= 50:
                    go_for_it = True
            # Down by any amount in last 2 minutes
            if score_margin < 0 and time_left < 120:
                go_for_it = True

        if go_for_it:
            if yards_to_go <= 1:
                return PlayCall.run(RunType.QB_SNEAK)
            elif yards_to_go <= 3:
                return PlayCall.run(RunType.INSIDE)
            else:
                return PlayCall.pass_play(PassType.SHORT)

        # FG or punt
        if in_fg_range:
            return PlayCall.field_goal()
        else:
            return PlayCall.punt()

    def _select_formation_and_personnel(
        self,
        game_state: GameState,
        yards_to_go: int,
        field_pos: FieldPosition,
        run_tendency: float,
    ) -> tuple[Formation, PersonnelPackage]:
        """Select formation and personnel package based on game situation."""
        # Goal line (inside 3 yard line) - power formations
        if field_pos.yard_line >= 97:
            return Formation.GOAL_LINE, PersonnelPackage.TWENTY_TWO

        # Short yardage (1-2 yards) - heavy personnel
        if yards_to_go <= 2:
            formations = [Formation.I_FORM, Formation.GOAL_LINE, Formation.UNDER_CENTER]
            personnel = [PersonnelPackage.TWENTY_TWO, PersonnelPackage.TWENTY_ONE, PersonnelPackage.THIRTEEN]
            idx = random.randint(0, 2)
            return formations[idx], personnel[idx]

        # Long yardage (8+ yards) - passing formations
        if yards_to_go >= 8:
            formations = [Formation.SHOTGUN, Formation.SPREAD, Formation.EMPTY]
            weights = [0.5, 0.35, 0.15]
            personnel_opts = [PersonnelPackage.ELEVEN, PersonnelPackage.TEN, PersonnelPackage.EMPTY]
            idx = random.choices(range(3), weights=weights)[0]
            return formations[idx], personnel_opts[idx]

        # Run-heavy tendency - balanced/power formations
        if run_tendency >= 0.6:
            formations = [Formation.SINGLEBACK, Formation.I_FORM, Formation.UNDER_CENTER, Formation.PISTOL]
            weights = [0.35, 0.30, 0.20, 0.15]
            personnel_opts = [PersonnelPackage.TWELVE, PersonnelPackage.TWENTY_ONE, PersonnelPackage.TWELVE, PersonnelPackage.TWELVE]
            idx = random.choices(range(4), weights=weights)[0]
            return formations[idx], personnel_opts[idx]

        # Pass-heavy tendency - spread formations
        if run_tendency <= 0.4:
            formations = [Formation.SHOTGUN, Formation.SPREAD, Formation.PISTOL]
            weights = [0.50, 0.30, 0.20]
            personnel_opts = [PersonnelPackage.ELEVEN, PersonnelPackage.TEN, PersonnelPackage.ELEVEN]
            idx = random.choices(range(3), weights=weights)[0]
            return formations[idx], personnel_opts[idx]

        # Balanced - mix of formations
        formations = [Formation.SHOTGUN, Formation.SINGLEBACK, Formation.PISTOL, Formation.I_FORM]
        weights = [0.35, 0.30, 0.20, 0.15]
        personnel_opts = [PersonnelPackage.ELEVEN, PersonnelPackage.TWELVE, PersonnelPackage.ELEVEN, PersonnelPackage.TWENTY_ONE]
        idx = random.choices(range(4), weights=weights)[0]
        return formations[idx], personnel_opts[idx]

    def _get_ai_defensive_call(self, game_state: GameState) -> DefensiveCall:
        """Get AI defensive play call based on situation."""
        defense = game_state.get_defensive_team()
        down = game_state.down_state.down
        yards_to_go = game_state.down_state.yards_to_go
        field_pos = game_state.down_state.line_of_scrimmage

        blitz_tendency = defense.blitz_tendency if defense else 0.3

        # Adjust for situation
        if down == 3 and yards_to_go >= 7:
            blitz_tendency += 0.15

        # Red zone - less blitzing
        if field_pos.yard_line >= 90:
            blitz_tendency -= 0.1

        # Goal line - man press
        if field_pos.yard_line >= 97:
            return DefensiveCall.man(press=True)

        if random.random() < blitz_tendency:
            rushers = random.choice([5, 6])
            return DefensiveCall.blitz(rushers)

        # Zone vs man
        if yards_to_go <= 5:
            return DefensiveCall.man(press=random.random() < 0.4)
        else:
            schemes = [DefensiveScheme.COVER_2, DefensiveScheme.COVER_3]
            return DefensiveCall(scheme=random.choice(schemes))

    def _emit_play_event(
        self, game_state: GameState, result: PlayResult, offense_is_home: bool
    ) -> None:
        """Emit play completed event."""
        self.event_bus.emit(
            PlayCompletedEvent(
                game_id=game_state.id,
                quarter=game_state.current_quarter,
                time_remaining=game_state.clock.display,
                home_score=game_state.score.home_score,
                away_score=game_state.score.away_score,
                result=result,
                down=game_state.down_state.down,
                yards_to_go=game_state.down_state.yards_to_go,
                field_position=game_state.down_state.line_of_scrimmage.display,
                line_of_scrimmage=game_state.down_state.line_of_scrimmage.yard_line,
                first_down_marker=game_state.down_state.first_down_marker,
                offense_is_home=offense_is_home,
            )
        )

    def _emit_scoring_event(
        self, game_state: GameState, points: int, score_type: str, team_id: UUID = None
    ) -> None:
        """Emit scoring event."""
        # Use provided team_id or fall back to current possession
        if team_id is None:
            team_id = game_state.possession.team_with_ball
        self.event_bus.emit(
            ScoringEvent(
                game_id=game_state.id,
                quarter=game_state.current_quarter,
                time_remaining=game_state.clock.display,
                home_score=game_state.score.home_score,
                away_score=game_state.score.away_score,
                team_id=team_id,
                points=points,
                scoring_type=score_type,
            )
        )

    def _emit_turnover_event(self, game_state: GameState, result: PlayResult) -> None:
        """Emit turnover event."""
        turnover_type = "INT" if result.outcome == PlayOutcome.INTERCEPTION else "FUMBLE"
        self.event_bus.emit(
            TurnoverEvent(
                game_id=game_state.id,
                quarter=game_state.current_quarter,
                time_remaining=game_state.clock.display,
                home_score=game_state.score.home_score,
                away_score=game_state.score.away_score,
                turnover_type=turnover_type,
            )
        )

    def _emit_game_end_event(self, game_state: GameState) -> None:
        """Emit game end event."""
        home_score = game_state.score.home_score
        away_score = game_state.score.away_score

        if home_score > away_score:
            winner = game_state.home_team_id
        elif away_score > home_score:
            winner = game_state.away_team_id
        else:
            winner = None

        self.event_bus.emit(
            GameEndEvent(
                game_id=game_state.id,
                quarter=game_state.current_quarter,
                home_score=home_score,
                away_score=away_score,
                winner_id=winner,
                final_home_score=home_score,
                final_away_score=away_score,
            )
        )
