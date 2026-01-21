"""Game Manager - Full game orchestration.

The Game Manager coordinates all aspects of a complete football game:
- Coin toss and initial possession
- Quarter/half transitions
- Kickoffs and punt returns
- Scoring sequences (TD → PAT/2PT, FG)
- Two-minute warning
- Overtime rules

This is the top-level interface for running games against the V2 simulation.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Callable, List, Optional

from huddle.core.models.game import (
    GameState,
    GameClock,
    GamePhase,
    ScoreState,
    PossessionState,
    DownState,
)
from huddle.simulation.v2.orchestrator import Orchestrator, PlayConfig

from huddle.game.roster_bridge import RosterBridge
from huddle.game.play_adapter import PlayAdapter, build_play_config
from huddle.game.special_teams import SpecialTeamsResolver, SpecialTeamsOutcome
from huddle.game.drive import DriveManager, DriveResult, DriveEndReason
from huddle.game.decision_logic import should_call_timeout

if TYPE_CHECKING:
    from huddle.core.models.team import Team
    from huddle.simulation.v2.core.entities import Player as V2Player


# =============================================================================
# Game Result
# =============================================================================

@dataclass
class GameResult:
    """Complete result of a game.

    Attributes:
        home_team_id: UUID of home team (as string)
        away_team_id: UUID of away team
        home_score: Final home score
        away_score: Final away score
        drives: All drives in the game
        winner: 'home', 'away', or 'tie'
    """
    home_team_id: str
    away_team_id: str
    home_score: int
    away_score: int
    drives: List[DriveResult] = field(default_factory=list)

    @property
    def winner(self) -> str:
        if self.home_score > self.away_score:
            return "home"
        elif self.away_score > self.home_score:
            return "away"
        return "tie"

    @property
    def margin(self) -> int:
        return abs(self.home_score - self.away_score)

    def format_score(self) -> str:
        return f"Home {self.home_score} - Away {self.away_score}"


# =============================================================================
# Game Manager
# =============================================================================

@dataclass
class GameManager:
    """Orchestrates a complete football game.

    The GameManager is the main entry point for running games. It:
    1. Sets up teams from the management layer
    2. Handles game flow (quarters, halftime, etc.)
    3. Coordinates drives and special teams
    4. Tracks and updates scoring

    Usage:
        manager = GameManager(home_team, away_team)
        result = manager.play_game()  # Auto-play full game

        # Or for coach mode:
        manager = GameManager(home_team, away_team, coach_mode=True)
        manager.start_game()
        while not manager.is_game_over:
            situation = manager.get_situation()
            play = get_user_play_call()
            manager.execute_play(play)
    """

    home_team: "Team"
    away_team: "Team"
    coach_mode: bool = False

    # Internal state
    _game_state: GameState = field(init=False)
    _orchestrator: Orchestrator = field(init=False)
    _special_teams: SpecialTeamsResolver = field(init=False)
    _home_bridge: RosterBridge = field(init=False)
    _away_bridge: RosterBridge = field(init=False)
    _drives: List[DriveResult] = field(default_factory=list)
    _possession_home: bool = True  # True = home has ball
    _receiving_2nd_half: Optional[bool] = None  # Track deferred choice
    # Timeout tracking (3 per half)
    _home_timeouts: int = 3
    _away_timeouts: int = 3

    def __post_init__(self):
        # Initialize game state
        self._game_state = GameState(
            phase=GamePhase.PREGAME,
            clock=GameClock(quarter=1, time_remaining_seconds=900),
            score=ScoreState(),
            possession=PossessionState(),
            down_state=DownState(down=1, yards_to_go=10, line_of_scrimmage=25),
        )

        # Initialize simulation components
        self._orchestrator = Orchestrator()
        self._special_teams = SpecialTeamsResolver()

        # Initialize roster bridges
        self._home_bridge = RosterBridge(self.home_team)
        self._away_bridge = RosterBridge(self.away_team)

        self._drives = []
        # Initialize timeouts (3 per half)
        self._home_timeouts = 3
        self._away_timeouts = 3

    # =========================================================================
    # Full Auto-Play
    # =========================================================================

    def play_game(self) -> GameResult:
        """Play a complete game automatically.

        Returns:
            GameResult with final score and all drives
        """
        self.start_game()

        while not self.is_game_over:
            self._play_drive()

            # Handle end-of-drive transitions
            if not self.is_game_over:
                self._handle_possession_change()

        return self._compile_result()

    def start_game(self) -> None:
        """Initialize game with coin toss and opening kickoff."""
        self._game_state.phase = GamePhase.FIRST_QUARTER

        # Coin toss - away team calls
        home_wins_toss = random.random() < 0.5

        # Winner typically defers, receiving in 2nd half
        if home_wins_toss:
            # Home defers, away receives
            self._possession_home = False
            self._receiving_2nd_half = True
        else:
            # Away defers, home receives
            self._possession_home = True
            self._receiving_2nd_half = False

        # Set initial field position (after kickoff)
        kickoff_result = self._handle_kickoff()
        self._set_possession(
            is_home=self._possession_home,
            los=kickoff_result.new_los,
        )

    # =========================================================================
    # Drive Execution
    # =========================================================================

    def _play_drive(self) -> DriveResult:
        """Execute a single drive."""
        # Get current offensive/defensive players
        offense, defense = self._get_players_for_drive()

        # Create drive manager
        drive_mgr = DriveManager(
            game_state=self._game_state,
            orchestrator=self._orchestrator,
            offense=offense,
            defense=defense,
            play_caller=None,  # Auto-play
        )

        # Execute drive
        result = drive_mgr.run_drive()
        self._drives.append(result)

        # Handle scoring
        self._process_drive_result(result)

        # Update game clock
        self._update_clock(result.time_of_possession)

        return result

    def _get_players_for_drive(self) -> tuple[List["V2Player"], List["V2Player"]]:
        """Get offensive and defensive players for current drive."""
        if self._possession_home:
            offense = self._home_bridge.get_offensive_11()
            defense = self._away_bridge.get_defensive_11()
        else:
            offense = self._away_bridge.get_offensive_11()
            defense = self._home_bridge.get_defensive_11()

        return offense, defense

    def _process_drive_result(self, result: DriveResult) -> None:
        """Process drive result and update score."""
        if result.end_reason == DriveEndReason.TOUCHDOWN:
            # TD scores 6, then handle PAT
            self._add_score(6)
            pat_result = self._handle_pat()
            self._add_score(pat_result.points)

        elif result.end_reason == DriveEndReason.FIELD_GOAL_MADE:
            self._add_score(3)

        elif result.end_reason == DriveEndReason.SAFETY:
            # Safety gives 2 points to defense
            self._add_score(-2)  # Negative for offense = positive for defense

    def _add_score(self, points: int) -> None:
        """Add points to current offensive team."""
        if points >= 0:
            if self._possession_home:
                self._game_state.score.home_score += points
            else:
                self._game_state.score.away_score += points
        else:
            # Negative points go to defense (safety)
            if self._possession_home:
                self._game_state.score.away_score += abs(points)
            else:
                self._game_state.score.home_score += abs(points)

    # =========================================================================
    # Special Teams
    # =========================================================================

    def _handle_kickoff(self, onside: bool = False) -> SpecialTeamsOutcome:
        """Handle a kickoff."""
        # Get kicker and returner
        kicker = None
        returner = None

        if self._possession_home:
            # Home kicks, away returns
            kicker = self.home_team.roster.get_starter("K1")
            returner = self.away_team.roster.get_starter("PR1")
        else:
            kicker = self.away_team.roster.get_starter("K1")
            returner = self.home_team.roster.get_starter("PR1")

        return self._special_teams.resolve_kickoff(kicker, returner, onside)

    def _handle_punt(self) -> SpecialTeamsOutcome:
        """Handle a punt."""
        punter = None
        returner = None

        if self._possession_home:
            punter = self.home_team.roster.get_starter("P1")
            returner = self.away_team.roster.get_starter("PR1")
        else:
            punter = self.away_team.roster.get_starter("P1")
            returner = self.home_team.roster.get_starter("PR1")

        los = self._game_state.down_state.line_of_scrimmage
        return self._special_teams.resolve_punt(punter, returner, los)

    def _handle_pat(self, go_for_two: bool = False) -> SpecialTeamsOutcome:
        """Handle PAT or 2-point conversion."""
        if go_for_two:
            return self._special_teams.resolve_two_point_statistical()

        # Get kicker
        kicker = None
        if self._possession_home:
            kicker = self.home_team.roster.get_starter("K1")
        else:
            kicker = self.away_team.roster.get_starter("K1")

        return self._special_teams.resolve_pat(kicker)

    def _handle_field_goal(self, distance: float) -> SpecialTeamsOutcome:
        """Handle a field goal attempt."""
        kicker = None
        if self._possession_home:
            kicker = self.home_team.roster.get_starter("K1")
        else:
            kicker = self.away_team.roster.get_starter("K1")

        return self._special_teams.resolve_field_goal(distance, kicker)

    # =========================================================================
    # Possession & Clock
    # =========================================================================

    def _handle_possession_change(self) -> None:
        """Handle change of possession after drive ends."""
        last_drive = self._drives[-1] if self._drives else None

        if last_drive:
            if last_drive.end_reason == DriveEndReason.PUNT:
                # Flip possession first, then punt
                self._possession_home = not self._possession_home
                punt_result = self._handle_punt()
                new_los = 100 - punt_result.new_los  # Flip perspective

            elif last_drive.end_reason in (
                DriveEndReason.TURNOVER_INTERCEPTION,
                DriveEndReason.TURNOVER_FUMBLE,
            ):
                # Ball at turnover spot
                self._possession_home = not self._possession_home
                new_los = 100 - last_drive.ending_los

            elif last_drive.end_reason == DriveEndReason.TURNOVER_ON_DOWNS:
                self._possession_home = not self._possession_home
                new_los = 100 - last_drive.ending_los

            elif last_drive.end_reason == DriveEndReason.FIELD_GOAL_MISSED:
                # Missed FG: ball goes to other team at spot of kick or 20, whichever is farther
                self._possession_home = not self._possession_home
                kick_spot = last_drive.ending_los
                new_los = max(100 - kick_spot, 20.0)

            elif last_drive.end_reason in (
                DriveEndReason.TOUCHDOWN,
                DriveEndReason.FIELD_GOAL_MADE,
                DriveEndReason.SAFETY,
            ):
                # Kickoff: team that just had possession kicks BEFORE flip
                # (scoring team kicks after TD/FG, team that gave up safety kicks)
                kickoff_result = self._handle_kickoff()
                new_los = kickoff_result.new_los
                # Now flip possession to receiving team
                self._possession_home = not self._possession_home

            else:
                self._possession_home = not self._possession_home
                new_los = 25.0
        else:
            self._possession_home = not self._possession_home
            new_los = 25.0

        self._set_possession(self._possession_home, new_los)

    def _set_possession(self, is_home: bool, los: float, ball_x: float = 0.0) -> None:
        """Set possession and initial downs.

        Args:
            is_home: True if home team has possession
            los: Line of scrimmage (0-100)
            ball_x: Ball lateral position (will be snapped to hash if outside)
        """
        self._possession_home = is_home
        self._game_state.down_state = DownState(
            down=1,
            yards_to_go=10,
            line_of_scrimmage=los,
            ball_x=ball_x,  # DownState.__post_init__ applies hash snap
        )

    def _update_clock(self, time_used: float) -> None:
        """Update game clock after a drive."""
        clock = self._game_state.clock
        clock.time_remaining_seconds -= int(time_used)

        # Check for quarter change
        if clock.time_remaining_seconds <= 0:
            self._advance_quarter()

    def _advance_quarter(self) -> None:
        """Advance to next quarter or end game."""
        clock = self._game_state.clock

        if clock.quarter < 4:
            clock.quarter += 1
            clock.time_remaining_seconds = 900  # 15 minutes

            # Handle halftime
            if clock.quarter == 3:
                self._handle_halftime()

            # Update phase
            if clock.quarter == 2:
                self._game_state.phase = GamePhase.SECOND_QUARTER
            elif clock.quarter == 3:
                self._game_state.phase = GamePhase.THIRD_QUARTER
            elif clock.quarter == 4:
                self._game_state.phase = GamePhase.FOURTH_QUARTER
        else:
            # End of regulation
            if self._game_state.score.home_score == self._game_state.score.away_score:
                # Overtime (simplified)
                self._game_state.phase = GamePhase.OVERTIME
                clock.quarter = 5
                clock.time_remaining_seconds = 600  # 10 min OT
            else:
                self._game_state.phase = GamePhase.FINAL

    def _handle_halftime(self) -> None:
        """Handle halftime kickoff switch and timeout reset."""
        # Reset timeouts for second half
        self._home_timeouts = 3
        self._away_timeouts = 3

        # Team that deferred gets ball
        if self._receiving_2nd_half is not None:
            self._possession_home = self._receiving_2nd_half
            kickoff_result = self._handle_kickoff()
            self._set_possession(self._possession_home, kickoff_result.new_los)

    # =========================================================================
    # Game State Properties
    # =========================================================================

    @property
    def is_game_over(self) -> bool:
        """Check if game has ended."""
        return self._game_state.phase == GamePhase.FINAL

    @property
    def home_score(self) -> int:
        return self._game_state.score.home_score

    @property
    def away_score(self) -> int:
        return self._game_state.score.away_score

    @property
    def quarter(self) -> int:
        return self._game_state.clock.quarter

    @property
    def time_remaining(self) -> float:
        return float(self._game_state.clock.time_remaining_seconds)

    @property
    def home_timeouts(self) -> int:
        return self._home_timeouts

    @property
    def away_timeouts(self) -> int:
        return self._away_timeouts

    @property
    def possession_home(self) -> bool:
        """True if home team has possession."""
        return self._possession_home

    def get_players_for_drive(self):
        """Get offensive and defensive players for current drive."""
        return self._get_players_for_drive()

    # =========================================================================
    # Timeout Management
    # =========================================================================

    def use_timeout(self, is_home: bool) -> bool:
        """Use a timeout for the specified team.

        Args:
            is_home: True for home team, False for away team

        Returns:
            True if timeout was used, False if none remaining
        """
        if is_home:
            if self._home_timeouts > 0:
                self._home_timeouts -= 1
                return True
        else:
            if self._away_timeouts > 0:
                self._away_timeouts -= 1
                return True
        return False

    def get_timeouts(self, is_home: bool) -> int:
        """Get remaining timeouts for a team."""
        return self._home_timeouts if is_home else self._away_timeouts

    def check_auto_timeout(self) -> Optional[bool]:
        """Check if AI should call a timeout based on game situation.

        Returns:
            True if home should call timeout, False if away should,
            None if no timeout should be called.
        """
        clock = self._game_state.clock
        score_diff = self.home_score - self.away_score

        # Check if defense (non-possession team) should call timeout
        defense_is_home = not self._possession_home
        defense_timeouts = self._home_timeouts if defense_is_home else self._away_timeouts
        defense_score_diff = score_diff if defense_is_home else -score_diff

        if should_call_timeout(
            time_remaining=clock.time_remaining_seconds,
            quarter=clock.quarter,
            score_diff=defense_score_diff,
            timeouts_remaining=defense_timeouts,
            is_offense=False,
        ):
            return defense_is_home

        # Check if offense should call timeout
        offense_timeouts = self._home_timeouts if self._possession_home else self._away_timeouts
        offense_score_diff = score_diff if self._possession_home else -score_diff

        if should_call_timeout(
            time_remaining=clock.time_remaining_seconds,
            quarter=clock.quarter,
            score_diff=offense_score_diff,
            timeouts_remaining=offense_timeouts,
            is_offense=True,
        ):
            return self._possession_home

        return None

    # =========================================================================
    # Coach Mode Interface
    # =========================================================================

    def get_situation(self) -> dict:
        """Get current game situation for coach mode UI."""
        down_state = self._game_state.down_state
        # Extract numeric yard line (FieldPosition has .yard_line property)
        los = down_state.line_of_scrimmage
        los_value = los.yard_line if hasattr(los, 'yard_line') else los
        return {
            "quarter": self.quarter,
            "time": self._format_time(self.time_remaining),
            "home_score": self.home_score,
            "away_score": self.away_score,
            "possession_home": self._possession_home,
            "down": down_state.down,
            "distance": down_state.yards_to_go,
            "los": los_value,
            "yard_line": self._format_yard_line(los_value),
            "is_red_zone": los_value >= 80,
            "home_timeouts": self._home_timeouts,
            "away_timeouts": self._away_timeouts,
        }

    def execute_play(self, play_config: PlayConfig) -> DriveResult:
        """Execute a single play in coach mode.

        Args:
            play_config: The play configuration to run

        Returns:
            DriveResult (partial - single play)
        """
        offense, defense = self._get_players_for_drive()

        # Set up and run single play
        los_y = self._game_state.down_state.line_of_scrimmage
        self._orchestrator.setup_play(offense, defense, play_config, los_y)
        self._orchestrator.register_default_brains()
        result = self._orchestrator.run()

        # Process result and update state
        # ... (would need single-play processing logic)

        return DriveResult(
            end_reason=DriveEndReason.PUNT,  # Placeholder
            total_yards=result.yards_gained,
        )

    # =========================================================================
    # Coach Mode Public API - Play Execution
    # =========================================================================

    def execute_play_by_code(
        self,
        play_code: str,
        shotgun: bool = True,
        defensive_call: Optional[str] = None,
    ) -> dict:
        """Execute a play by code in coach mode.

        This is the main public API for executing plays. It handles:
        - Building the play configuration from the code
        - Getting AI defensive call if not provided
        - Running the simulation
        - Updating down/distance, field position, scoring
        - Consuming clock time

        Args:
            play_code: Offensive play code (e.g., "PASS_SLANT", "RUN_POWER")
            shotgun: Whether QB is in shotgun formation
            defensive_call: Optional defensive play code (AI calls if None)

        Returns:
            Dict with play result suitable for API response:
            {
                "outcome": str,  # "complete", "incomplete", "run", etc.
                "yards_gained": float,
                "is_touchdown": bool,
                "is_turnover": bool,
                "is_safety": bool,
                "is_first_down": bool,
                "is_drive_over": bool,
                "drive_end_reason": Optional[str],
                "new_down": int,
                "new_distance": int,
                "new_los": float,
                "passer_id": Optional[str],
                "receiver_id": Optional[str],
                "tackler_id": Optional[str],
                "time_elapsed": float,
                "play_duration": float,
            }
        """
        from huddle.game.play_adapter import PlayAdapter
        from huddle.game.coordinator import DefensiveCoordinator, SituationContext

        # Get players
        offense, defense = self._get_players_for_drive()

        # Build play config
        adapter = PlayAdapter(offense, defense)
        config = adapter.build_offensive_config(play_code, shotgun)

        # Get AI defensive call if not provided
        if defensive_call is None:
            down_state = self._game_state.down_state
            los_value = self._extract_los_value(down_state.line_of_scrimmage)
            context = SituationContext(
                down=down_state.down,
                distance=down_state.yards_to_go,
                los=los_value,
                quarter=self.quarter,
                time_remaining=self.time_remaining,
                score_diff=self.home_score - self.away_score if self._possession_home else self.away_score - self.home_score,
                timeouts=self._home_timeouts if self._possession_home else self._away_timeouts,
            )
            dc = DefensiveCoordinator()
            defensive_call = dc.call_coverage(context)

        # Add defensive assignments
        man_assign, zone_assign = adapter.build_defensive_config(defensive_call)
        config.man_assignments = man_assign
        config.zone_assignments = zone_assign

        # Execute play
        down_state = self._game_state.down_state
        los_value = self._extract_los_value(down_state.line_of_scrimmage)

        # Reposition players to current LOS (critical for correct dropback targeting)
        self._reposition_players(offense, defense, los_value)

        self._orchestrator.setup_play(offense, defense, config, los_value)
        self._orchestrator.register_default_brains()
        result = self._orchestrator.run()

        # Process result and update state
        return self._process_play_result(result, offense, defense)

    def execute_play_by_code_with_frames(
        self,
        play_code: str,
        shotgun: bool = True,
        defensive_call: Optional[str] = None,
    ) -> tuple:
        """Execute a play and collect frames for visualization.

        Same as execute_play_by_code but also returns frames for animation.
        Frame collection is handled by the caller (coach_mode.py) since it's
        visualization-specific.

        Args:
            play_code: Offensive play code
            shotgun: Whether QB is in shotgun
            defensive_call: Optional defensive play code

        Returns:
            Tuple of (result_dict, orchestrator, offense, defense)
            Caller can collect frames using the orchestrator.
        """
        from huddle.game.play_adapter import PlayAdapter
        from huddle.game.coordinator import DefensiveCoordinator, SituationContext

        # Get players
        offense, defense = self._get_players_for_drive()

        # Build play config
        adapter = PlayAdapter(offense, defense)
        config = adapter.build_offensive_config(play_code, shotgun)

        # Get AI defensive call if not provided
        if defensive_call is None:
            down_state = self._game_state.down_state
            los_value = self._extract_los_value(down_state.line_of_scrimmage)
            context = SituationContext(
                down=down_state.down,
                distance=down_state.yards_to_go,
                los=los_value,
                quarter=self.quarter,
                time_remaining=self.time_remaining,
                score_diff=self.home_score - self.away_score if self._possession_home else self.away_score - self.home_score,
                timeouts=self._home_timeouts if self._possession_home else self._away_timeouts,
            )
            dc = DefensiveCoordinator()
            defensive_call = dc.call_coverage(context)

        # Add defensive assignments
        man_assign, zone_assign = adapter.build_defensive_config(defensive_call)
        config.man_assignments = man_assign
        config.zone_assignments = zone_assign

        # Set up play (don't run yet - caller will collect frames)
        down_state = self._game_state.down_state
        los_value = self._extract_los_value(down_state.line_of_scrimmage)

        # Reposition players to current LOS (critical for correct dropback targeting)
        self._reposition_players(offense, defense, los_value)

        self._orchestrator.setup_play(offense, defense, config, los_value)
        self._orchestrator.register_default_brains()

        return self._orchestrator, offense, defense

    def finalize_play_result(self, result) -> dict:
        """Process a play result after running the orchestrator.

        Used when caller runs the orchestrator manually (e.g., for frame collection).

        Args:
            result: PlayResult from orchestrator.run()

        Returns:
            Dict with play result (same format as execute_play_by_code)
        """
        offense, defense = self._get_players_for_drive()
        return self._process_play_result(result, offense, defense)

    def _process_play_result(self, result, offense, defense) -> dict:
        """Process play result and update game state.

        Internal method that handles:
        - TD/turnover/safety detection
        - Down/distance updates
        - Field position updates
        - Clock consumption
        - Scoring

        Args:
            result: PlayResult from orchestrator
            offense: Offensive players
            defense: Defensive players

        Returns:
            Dict with processed result
        """
        import random

        down_state = self._game_state.down_state
        los_value = self._extract_los_value(down_state.line_of_scrimmage)

        old_down = down_state.down
        old_distance = down_state.yards_to_go
        yards = result.yards_gained

        # Check for touchdown
        is_touchdown = los_value + yards >= 100

        # Check for safety (ball carrier tackled behind own goal line)
        is_safety = los_value + yards <= 0

        # Check for turnover
        is_turnover = result.outcome in ("interception", "fumble", "fumble_lost")

        # Determine drive end conditions
        drive_over = False
        drive_reason = None

        if is_touchdown:
            drive_over = True
            drive_reason = "touchdown"
            self._add_score(6)
        elif is_safety:
            drive_over = True
            drive_reason = "safety"
            # Safety gives 2 points to defense
            self._add_score(-2)
        elif is_turnover:
            drive_over = True
            drive_reason = "turnover"
        else:
            # Update down/distance
            if yards >= old_distance:
                # First down
                is_first_down = True
                new_los = los_value + yards
                new_los = min(99, new_los)  # Clamp to field
                down_state.down = 1
                down_state.yards_to_go = min(10, int(100 - new_los))
                down_state.line_of_scrimmage = new_los
            else:
                # No first down
                is_first_down = False
                new_los = los_value + yards
                new_los = max(1, min(99, new_los))
                down_state.down += 1
                down_state.yards_to_go = max(1, old_distance - int(yards))
                down_state.line_of_scrimmage = new_los

            # Check for turnover on downs
            if down_state.down > 4:
                drive_over = True
                drive_reason = "turnover_on_downs"

        # Consume clock time
        play_time = result.duration + random.uniform(20.0, 35.0)
        self._consume_play_time(play_time)

        # Build result dict
        result_dict = {
            "outcome": result.outcome,
            "yards_gained": yards,
            "is_touchdown": is_touchdown,
            "is_turnover": is_turnover,
            "is_safety": is_safety,
            "is_first_down": not drive_over and yards >= old_distance,
            "is_drive_over": drive_over,
            "drive_end_reason": drive_reason,
            "new_down": down_state.down,
            "new_distance": down_state.yards_to_go,
            "new_los": self._extract_los_value(down_state.line_of_scrimmage),
            "passer_id": result.passer_id,
            "receiver_id": result.receiver_id,
            "tackler_id": result.tackler_id,
            "time_elapsed": play_time,
            "play_duration": result.duration,
        }

        return result_dict

    def execute_special_teams(
        self,
        play_type: str,
        go_for_two: bool = False,
        onside: bool = False,
    ) -> dict:
        """Execute a special teams play.

        Args:
            play_type: "punt", "field_goal", "pat", "kickoff"
            go_for_two: For PAT, whether to go for 2-point conversion
            onside: For kickoff, whether to attempt onside kick

        Returns:
            Dict with result:
            {
                "play_type": str,
                "result": str,
                "new_los": float,
                "points_scored": int,
                "description": str,
                "kicking_team_ball": bool,  # For onside kicks
            }
        """
        down_state = self._game_state.down_state
        los_value = self._extract_los_value(down_state.line_of_scrimmage)

        if play_type == "punt":
            result = self._handle_punt()
            # Punt result.new_los is from receiving team's perspective
            description = f"Punt from the {los_value:.0f}"
            if result.result == "touchback":
                description += " - Touchback"
            elif result.result == "fair_catch":
                description += f" - Fair catch at the {result.new_los:.0f}"
            else:
                description += f" - Returned to the {result.new_los:.0f}"

            # Store the new LOS so handle_drive_end can use it
            # This is already in receiving team's perspective
            down_state.line_of_scrimmage = result.new_los

            return {
                "play_type": "punt",
                "result": result.result,
                "new_los": result.new_los,
                "points_scored": 0,
                "description": description,
                "kicking_team_ball": False,
            }

        elif play_type == "field_goal":
            fg_distance = (100 - los_value) + 17
            result = self._handle_field_goal(fg_distance)

            if result.points > 0:
                self._add_score(3)
                description = f"{fg_distance:.0f}-yard field goal is GOOD"
            else:
                description = f"{fg_distance:.0f}-yard field goal is NO GOOD"

            return {
                "play_type": "field_goal",
                "result": result.result,
                "new_los": result.new_los,
                "points_scored": result.points,
                "description": description,
                "kicking_team_ball": False,
            }

        elif play_type == "pat":
            result = self._handle_pat(go_for_two=go_for_two)

            if go_for_two:
                description = "Two-point conversion " + ("GOOD" if result.points > 0 else "FAILED")
            else:
                description = "Extra point is " + ("GOOD" if result.points > 0 else "NO GOOD")

            if result.points > 0:
                self._add_score(result.points)

            return {
                "play_type": "pat" if not go_for_two else "two_point",
                "result": result.result,
                "new_los": 25.0,
                "points_scored": result.points,
                "description": description,
                "kicking_team_ball": False,
            }

        elif play_type == "kickoff":
            result = self._handle_kickoff(onside=onside)

            if onside:
                description = "Onside kick " + ("RECOVERED" if result.kicking_team_ball else "FAILED")
            elif result.result == "touchback":
                description = "Kickoff - Touchback"
            else:
                description = f"Kickoff returned to the {result.new_los:.0f}"

            return {
                "play_type": "kickoff",
                "result": result.result,
                "new_los": result.new_los,
                "points_scored": 0,
                "description": description,
                "kicking_team_ball": result.kicking_team_ball,
            }

        else:
            raise ValueError(f"Unknown special teams play type: {play_type}")

    def step_auto_play(self) -> dict:
        """Execute one AI-controlled play (for spectator mode).

        AI controls both offense and defense. Handles:
        - 4th down decisions (punt/FG/go for it)
        - Play calling
        - Play execution
        - State updates

        Returns:
            Dict with result:
            {
                "type": "play" | "special_teams",
                "play_code": Optional[str],  # For regular plays
                "result": dict,  # Play or special teams result
                "is_drive_over": bool,
                "drive_end_reason": Optional[str],
            }
        """
        from huddle.game.coordinator import OffensiveCoordinator, SituationContext
        from huddle.game.decision_logic import fourth_down_decision, FourthDownDecision

        down_state = self._game_state.down_state
        los_value = self._extract_los_value(down_state.line_of_scrimmage)

        # Build situation context
        context = SituationContext(
            down=down_state.down,
            distance=down_state.yards_to_go,
            los=los_value,
            quarter=self.quarter,
            time_remaining=self.time_remaining,
            score_diff=self.home_score - self.away_score if self._possession_home else self.away_score - self.home_score,
            timeouts=self._home_timeouts if self._possession_home else self._away_timeouts,
        )

        # Check for 4th down decisions
        if down_state.down == 4:
            decision = fourth_down_decision(
                yard_line=int(los_value),
                yards_to_go=int(down_state.yards_to_go),
                score_diff=context.score_diff,
                time_remaining=int(self.time_remaining),
            )

            if decision == FourthDownDecision.PUNT:
                result = self.execute_special_teams("punt")
                return {
                    "type": "special_teams",
                    "play_code": None,
                    "result": result,
                    "is_drive_over": True,
                    "drive_end_reason": "punt",
                }

            elif decision == FourthDownDecision.FIELD_GOAL:
                result = self.execute_special_teams("field_goal")
                drive_reason = "field_goal_made" if result["points_scored"] > 0 else "field_goal_missed"
                return {
                    "type": "special_teams",
                    "play_code": None,
                    "result": result,
                    "is_drive_over": True,
                    "drive_end_reason": drive_reason,
                }

        # AI calls the play
        offense_team = self.home_team if self._possession_home else self.away_team
        oc = OffensiveCoordinator(team=offense_team)
        play_code = oc.call_play(context)

        # Execute play
        result = self.execute_play_by_code(play_code, shotgun=True)

        return {
            "type": "play",
            "play_code": play_code,
            "result": result,
            "is_drive_over": result["is_drive_over"],
            "drive_end_reason": result["drive_end_reason"],
        }

    def handle_drive_end(self, reason: str) -> dict:
        """Handle end of drive and possession change.

        Called after a drive ends to set up the next possession.

        Args:
            reason: Drive end reason ("touchdown", "field_goal_made",
                    "field_goal_missed", "punt", "turnover", "turnover_on_downs", "safety")

        Returns:
            Dict with new possession info:
            {
                "possession_home": bool,
                "new_los": float,
                "kickoff_result": Optional[dict],  # If there was a kickoff
            }
        """
        down_state = self._game_state.down_state

        if reason in ("touchdown", "field_goal_made"):
            # Scoring team kicks off
            kickoff_result = self.execute_special_teams("kickoff")
            # Flip possession to receiving team
            self._possession_home = not self._possession_home
            new_los = kickoff_result["new_los"]
            self._set_possession(self._possession_home, new_los)

            return {
                "possession_home": self._possession_home,
                "new_los": new_los,
                "kickoff_result": kickoff_result,
            }

        elif reason == "safety":
            # Team that gave up safety kicks from their own 20
            # This is a free kick, not a regular kickoff
            self._possession_home = not self._possession_home
            new_los = 25.0  # Simplified - actual free kick return
            self._set_possession(self._possession_home, new_los)

            return {
                "possession_home": self._possession_home,
                "new_los": new_los,
                "kickoff_result": None,
            }

        elif reason == "punt":
            # Punt was already resolved, possession flips
            # The punt result new_los is from receiving team's perspective
            self._possession_home = not self._possession_home
            # Note: new_los should have been set by execute_special_teams
            # which returns receiving team's starting position
            self._set_possession(self._possession_home, down_state.line_of_scrimmage)

            return {
                "possession_home": self._possession_home,
                "new_los": down_state.line_of_scrimmage,
                "kickoff_result": None,
            }

        elif reason in ("turnover", "turnover_on_downs", "field_goal_missed"):
            # Ball goes to other team at current spot (or 20 for missed FG)
            self._possession_home = not self._possession_home
            current_los = self._extract_los_value(down_state.line_of_scrimmage)

            if reason == "field_goal_missed":
                # Ball at spot of kick or 20, whichever is farther from own goal
                new_los = max(100 - current_los, 20.0)
            else:
                # Flip field position for other team
                new_los = 100 - current_los

            self._set_possession(self._possession_home, new_los)

            return {
                "possession_home": self._possession_home,
                "new_los": new_los,
                "kickoff_result": None,
            }

        else:
            # Unknown reason, default handling
            self._possession_home = not self._possession_home
            self._set_possession(self._possession_home, 25.0)

            return {
                "possession_home": self._possession_home,
                "new_los": 25.0,
                "kickoff_result": None,
            }

    def _extract_los_value(self, los) -> float:
        """Extract numeric yard line from FieldPosition or float.

        Args:
            los: Either a FieldPosition object or numeric value

        Returns:
            Numeric yard line (0-100)
        """
        if hasattr(los, 'yard_line'):
            return float(los.yard_line)
        return float(los)

    def _reposition_players(
        self,
        offense: List["V2Player"],
        defense: List["V2Player"],
        los_y: float,
        ball_x: float = None,
    ) -> None:
        """Reposition players to their formation alignments at the current LOS.

        Players from RosterBridge are created with los_y=0 by default.
        This method translates their positions to the actual field LOS.

        Args:
            offense: Offensive players to reposition
            defense: Defensive players to reposition
            los_y: Line of scrimmage Y position in field coordinates
            ball_x: Ball lateral position (if None, uses down_state.ball_x)
        """
        from huddle.game.roster_bridge import OFFENSIVE_ALIGNMENTS, DEFENSIVE_ALIGNMENTS
        from huddle.simulation.v2.core.vec2 import Vec2

        # Get ball_x from down_state if not provided
        if ball_x is None:
            ball_x = self._game_state.down_state.ball_x

        # Reposition offense (offset by ball_x for hash-relative positioning)
        for player in offense:
            if player.position_slot in OFFENSIVE_ALIGNMENTS:
                alignment = OFFENSIVE_ALIGNMENTS[player.position_slot]
                player.pos = Vec2(alignment.x + ball_x, alignment.y + los_y)
                player.velocity = Vec2.zero()

        # Reposition defense (offset by ball_x for hash-relative positioning)
        for player in defense:
            if player.position_slot in DEFENSIVE_ALIGNMENTS:
                alignment = DEFENSIVE_ALIGNMENTS[player.position_slot]
                player.pos = Vec2(alignment.x + ball_x, alignment.y + los_y)
                player.velocity = Vec2.zero()

    def _consume_play_time(self, seconds: float) -> None:
        """Decrement game clock after a play.

        Args:
            seconds: Seconds to consume
        """
        clock = self._game_state.clock
        clock.time_remaining_seconds = max(0, clock.time_remaining_seconds - int(seconds))

        # Check for quarter change
        if clock.time_remaining_seconds <= 0:
            self._advance_quarter()

    def _format_time(self, seconds: float) -> str:
        """Format time as MM:SS."""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"

    def _format_yard_line(self, los: float) -> str:
        """Format yard line for display."""
        if los >= 50:
            return f"OPP {100 - los:.0f}"
        return f"OWN {los:.0f}"

    # =========================================================================
    # Results
    # =========================================================================

    def _compile_result(self) -> GameResult:
        """Compile final game result."""
        return GameResult(
            home_team_id=str(self.home_team.id),
            away_team_id=str(self.away_team.id),
            home_score=self.home_score,
            away_score=self.away_score,
            drives=self._drives,
        )
