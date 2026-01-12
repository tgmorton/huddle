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

    def _set_possession(self, is_home: bool, los: float) -> None:
        """Set possession and initial downs."""
        self._possession_home = is_home
        self._game_state.down_state = DownState(
            down=1,
            yards_to_go=10,
            line_of_scrimmage=los,
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
        return {
            "quarter": self.quarter,
            "time": self._format_time(self.time_remaining),
            "home_score": self.home_score,
            "away_score": self.away_score,
            "possession_home": self._possession_home,
            "down": down_state.down,
            "distance": down_state.yards_to_go,
            "los": down_state.line_of_scrimmage,
            "yard_line": self._format_yard_line(down_state.line_of_scrimmage),
            "is_red_zone": down_state.line_of_scrimmage >= 80,
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
