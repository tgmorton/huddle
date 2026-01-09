"""Drive Manager - Execute drives from start to finish.

A drive is a series of plays by one team until:
- Touchdown (TD)
- Field Goal (FG) - successful or missed
- Turnover (INT, fumble)
- Punt
- Turnover on downs

This module handles:
1. Down and distance tracking
2. First down detection
3. Red zone / goal line situations
4. Drive end conditions
5. Play-by-play logging
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Callable, List, Optional

from huddle.core.models.game import GameState, DownState
from huddle.core.models.field import FieldPosition
from huddle.simulation.v2.orchestrator import Orchestrator, PlayConfig, PlayResult

if TYPE_CHECKING:
    from huddle.core.models.team import Team
    from huddle.simulation.v2.core.entities import Player as V2Player


# =============================================================================
# Drive Result Types
# =============================================================================

class DriveEndReason(Enum):
    """How a drive ended."""
    TOUCHDOWN = "touchdown"
    FIELD_GOAL_MADE = "field_goal_made"
    FIELD_GOAL_MISSED = "field_goal_missed"
    PUNT = "punt"
    TURNOVER_INTERCEPTION = "turnover_interception"
    TURNOVER_FUMBLE = "turnover_fumble"
    TURNOVER_ON_DOWNS = "turnover_on_downs"
    END_OF_HALF = "end_of_half"
    SAFETY = "safety"


@dataclass
class PlayLog:
    """Record of a single play in a drive."""
    play_number: int
    down: int
    distance: int
    los: float  # Line of scrimmage (0-100)
    play_type: str  # "run", "pass", "scramble"
    play_call: str  # PlayCode used
    yards_gained: float
    result: str  # "complete", "incomplete", "run", "sack", etc.
    first_down: bool
    touchdown: bool
    turnover: bool
    time_elapsed: float  # Seconds


@dataclass
class DriveResult:
    """Complete result of a drive.

    Attributes:
        end_reason: How the drive ended
        plays: List of all plays in the drive
        total_yards: Net yards gained
        time_of_possession: Total time in seconds
        starting_los: Where drive started
        ending_los: Where drive ended
        points_scored: Points from this drive (0, 3, 6, 7, 8)
    """
    end_reason: DriveEndReason
    plays: List[PlayLog] = field(default_factory=list)
    total_yards: float = 0.0
    time_of_possession: float = 0.0
    starting_los: float = 25.0
    ending_los: float = 25.0
    points_scored: int = 0

    @property
    def play_count(self) -> int:
        return len(self.plays)

    @property
    def is_scoring_drive(self) -> bool:
        return self.points_scored > 0

    def format_summary(self) -> str:
        """Format drive summary."""
        return (
            f"{self.play_count} plays, {self.total_yards:.0f} yards, "
            f"{self.time_of_possession:.0f}s - {self.end_reason.value}"
        )


# =============================================================================
# Drive Manager
# =============================================================================

@dataclass
class DriveManager:
    """Manages execution of a single drive.

    The drive manager runs plays until a drive-ending condition is met.
    It tracks down/distance, checks for first downs, and handles
    scoring opportunities.

    Attributes:
        game_state: Current game state (modified during drive)
        orchestrator: V2 simulation orchestrator
        offense: Offensive V2 players
        defense: Defensive V2 players
        play_caller: Callback to get next play (coach mode)
    """

    game_state: GameState
    orchestrator: Orchestrator
    offense: List["V2Player"]
    defense: List["V2Player"]
    play_caller: Optional[Callable[["DriveManager"], PlayConfig]] = None

    # Internal state
    _plays: List[PlayLog] = field(default_factory=list)
    _drive_start_los: float = 25.0
    _current_los: float = 25.0
    _total_time: float = 0.0

    def __post_init__(self):
        self._plays = []
        # line_of_scrimmage is in "own yard line" format (25 = own 25)
        # V2 uses y=0 at own endzone, y=100 at opponent endzone
        # So own 25 → y=25 in V2 coordinates
        self._drive_start_los = self.game_state.down_state.line_of_scrimmage
        self._current_los = self._drive_start_los
        self._total_time = 0.0
        self._forced_end_reason: Optional[DriveEndReason] = None

    def run_drive(self) -> DriveResult:
        """Execute the drive to completion.

        Returns:
            DriveResult with all plays and outcome
        """
        while not self._is_drive_over():
            # Check for 4th down decisions before running play
            if self._should_punt():
                # End drive as punt (don't run the play)
                self._force_drive_end(DriveEndReason.PUNT)
                break

            if self._should_attempt_fg():
                # End drive as FG attempt (resolved by manager)
                # For now, 50% success rate on long FGs
                import random
                fg_distance = 100 - self._current_los + 17
                success_rate = max(0.3, 1.0 - (fg_distance - 20) / 60)
                if random.random() < success_rate:
                    self._force_drive_end(DriveEndReason.FIELD_GOAL_MADE)
                else:
                    self._force_drive_end(DriveEndReason.FIELD_GOAL_MISSED)
                break

            play_result = self._execute_play()
            self._process_play_result(play_result)

        return self._compile_result()

    def _force_drive_end(self, reason: DriveEndReason) -> None:
        """Force the drive to end with a specific reason."""
        # Store the forced end reason for _compile_result
        self._forced_end_reason = reason

    def _execute_play(self) -> PlayResult:
        """Execute a single play.

        Gets play call from play_caller callback, sets up the play,
        and runs the simulation.
        """
        # Get play configuration
        if self.play_caller:
            config = self.play_caller(self)
        else:
            # Default: simple run/pass based on situation
            config = self._default_play_call()

        # Reposition players at current LOS
        # Players have formation-relative positions that need translation
        los_y = self._current_los
        self._reposition_players(los_y)

        # Set up the play
        self.orchestrator.setup_play(
            self.offense,
            self.defense,
            config,
            los_y=los_y,
        )

        # Run simulation
        result = self.orchestrator.run()

        return result

    def _reposition_players(self, los_y: float) -> None:
        """Reposition players to their formation alignments at the current LOS.

        Players store their formation-relative positions in position_slot.
        We translate these to field coordinates based on current LOS.
        """
        from huddle.game.roster_bridge import OFFENSIVE_ALIGNMENTS, DEFENSIVE_ALIGNMENTS
        from huddle.simulation.v2.core.vec2 import Vec2

        # Reposition offense
        for player in self.offense:
            if player.position_slot in OFFENSIVE_ALIGNMENTS:
                alignment = OFFENSIVE_ALIGNMENTS[player.position_slot]
                player.pos = Vec2(alignment.x, alignment.y + los_y)
                player.velocity = Vec2.zero()

        # Reposition defense
        for player in self.defense:
            if player.position_slot in DEFENSIVE_ALIGNMENTS:
                alignment = DEFENSIVE_ALIGNMENTS[player.position_slot]
                player.pos = Vec2(alignment.x, alignment.y + los_y)
                player.velocity = Vec2.zero()

    def _default_play_call(self) -> PlayConfig:
        """Generate a default play call based on situation."""
        down = self.game_state.down_state.down
        distance = self.game_state.down_state.yards_to_go
        los = self._current_los

        # Very simple AI:
        # - 1st and 10: 50/50 run/pass
        # - 3rd and long: pass
        # - 4th down: handled separately
        # - Red zone: more runs
        import random

        is_run = False
        if down == 1:
            is_run = random.random() < 0.50
        elif down == 2:
            is_run = random.random() < 0.45 if distance <= 5 else 0.30
        elif down == 3:
            is_run = distance <= 2
        else:
            is_run = distance <= 1

        # Red zone adjustments
        if los >= 80:  # Inside 20
            is_run = random.random() < 0.55

        if is_run:
            return PlayConfig(
                is_run_play=True,
                run_concept="inside_zone",
                run_direction="inside_right",
                handoff_timing=0.6,
                max_duration=10.0,
            )
        else:
            # Simple pass play
            return PlayConfig(
                routes={
                    p.id: "slant" for p in self.offense
                    if p.position.value in ("WR", "TE")
                },
                max_duration=8.0,
            )

    def _process_play_result(self, result: PlayResult) -> None:
        """Process the result of a play and update state."""
        import random

        down_state = self.game_state.down_state
        yards = result.yards_gained

        # Check for turnover
        is_turnover = result.outcome in ("interception", "fumble_lost")
        is_touchdown = self._check_touchdown(yards)
        is_safety = self._check_safety(yards)

        # Calculate realistic time elapsed:
        # - Play action: result.duration (typically 3-8 seconds)
        # - Play clock between plays: 20-35 seconds (huddle, formation, snap)
        play_action_time = result.duration
        play_clock_time = random.uniform(20.0, 35.0)
        total_play_time = play_action_time + play_clock_time

        # Create play log
        play_log = PlayLog(
            play_number=len(self._plays) + 1,
            down=down_state.down,
            distance=down_state.yards_to_go,
            los=self._current_los,
            play_type="run" if "run" in result.outcome else "pass",
            play_call="unknown",  # Would come from config
            yards_gained=yards,
            result=result.outcome,
            first_down=yards >= down_state.yards_to_go,
            touchdown=is_touchdown,
            turnover=is_turnover,
            time_elapsed=total_play_time,
        )
        self._plays.append(play_log)

        # Update time with realistic play clock
        self._total_time += total_play_time

        # Update field position
        self._current_los += yards

        # Update down state
        if is_turnover or is_touchdown or is_safety:
            # Drive over
            return

        if yards >= down_state.yards_to_go:
            # First down!
            self._reset_downs()
        else:
            # Advance down
            down_state.down += 1
            down_state.yards_to_go = max(1, down_state.yards_to_go - int(yards))

    def _check_touchdown(self, yards: float) -> bool:
        """Check if the play resulted in a touchdown."""
        return self._current_los + yards >= 100

    def _check_safety(self, yards: float) -> bool:
        """Check if the play resulted in a safety."""
        return self._current_los + yards <= 0

    def _reset_downs(self) -> None:
        """Reset to 1st and 10 (or goal)."""
        down_state = self.game_state.down_state
        down_state.down = 1

        # Distance to goal
        distance_to_goal = 100 - self._current_los
        down_state.yards_to_go = min(10, int(distance_to_goal))

    def _is_drive_over(self) -> bool:
        """Check if the drive should end."""
        if not self._plays:
            return False

        last_play = self._plays[-1]

        # Touchdown
        if last_play.touchdown:
            return True

        # Turnover
        if last_play.turnover:
            return True

        # Safety (rare edge case)
        if self._current_los <= 0:
            return True

        # Fourth down not converted
        down_state = self.game_state.down_state
        if down_state.down > 4:
            return True

        # TODO: Check game clock for end of half

        return False

    def _should_punt(self) -> bool:
        """Check if team should punt on 4th down."""
        down = self.game_state.down_state.down
        distance = self.game_state.down_state.yards_to_go

        if down != 4:
            return False

        # Never punt in opponent red zone
        if self._current_los >= 60:  # Opponent 40 or closer
            return False

        # Always punt from own territory with long distance
        if self._current_los < 50 and distance > 3:
            return True

        # Punt if distance is long (> 5 yards)
        if distance > 5:
            return True

        return False

    def _should_attempt_fg(self) -> bool:
        """Check if team should attempt field goal on 4th down."""
        down = self.game_state.down_state.down

        if down != 4:
            return False

        # FG range check (need to be inside opponent 35 for ~52 yard attempt)
        # FG distance = 100 - los + 17 (endzone + snap distance)
        fg_distance = 100 - self._current_los + 17

        # Attempt FG if within 55 yards
        return fg_distance <= 55

    def _compile_result(self) -> DriveResult:
        """Compile the final drive result."""
        points = 0

        # Check for forced end reason (punt/FG decision)
        if self._forced_end_reason:
            end_reason = self._forced_end_reason
            if end_reason == DriveEndReason.FIELD_GOAL_MADE:
                points = 3
        elif not self._plays:
            end_reason = DriveEndReason.PUNT
        else:
            # Determine end reason from last play
            last_play = self._plays[-1]

            if last_play.touchdown:
                end_reason = DriveEndReason.TOUCHDOWN
                points = 6  # PAT handled separately
            elif last_play.turnover:
                if "interception" in last_play.result:
                    end_reason = DriveEndReason.TURNOVER_INTERCEPTION
                else:
                    end_reason = DriveEndReason.TURNOVER_FUMBLE
            elif self._current_los <= 0:
                end_reason = DriveEndReason.SAFETY
            elif self.game_state.down_state.down > 4:
                end_reason = DriveEndReason.TURNOVER_ON_DOWNS
            else:
                end_reason = DriveEndReason.PUNT

        return DriveResult(
            end_reason=end_reason,
            plays=self._plays,
            total_yards=self._current_los - self._drive_start_los,
            time_of_possession=self._total_time,
            starting_los=self._drive_start_los,
            ending_los=self._current_los,
            points_scored=points,
        )

    # =========================================================================
    # Coach Mode Interface
    # =========================================================================

    def get_situation(self) -> dict:
        """Get current game situation for UI display.

        Returns dict with down, distance, field position, score, time, etc.
        """
        down_state = self.game_state.down_state
        return {
            "down": down_state.down,
            "distance": down_state.yards_to_go,
            "los": self._current_los,
            "yard_line": self._get_yard_line_display(),
            "quarter": self.game_state.clock.quarter,
            "time": self.game_state.clock.display,
            "home_score": self.game_state.score.home_score,
            "away_score": self.game_state.score.away_score,
            "is_red_zone": self._current_los >= 80,
            "is_goal_to_go": down_state.yards_to_go >= (100 - self._current_los),
        }

    def _get_yard_line_display(self) -> str:
        """Get human-readable yard line (e.g., 'OPP 25')."""
        if self._current_los >= 50:
            yard_line = 100 - self._current_los
            return f"OPP {yard_line:.0f}"
        else:
            return f"OWN {self._current_los:.0f}"

    def get_available_plays(self) -> List[str]:
        """Get list of available play codes based on situation.

        In a full implementation, this would filter based on:
        - Team playbook
        - Down and distance
        - Field position
        - Player availability
        """
        # Return a basic set for now
        plays = [
            "RUN_INSIDE_ZONE",
            "RUN_OUTSIDE_ZONE",
            "RUN_POWER",
            "PASS_SLANT",
            "PASS_HITCH",
            "PASS_CURL",
            "PASS_POST",
        ]

        # Add screens on 2nd/3rd and long
        if self.game_state.down_state.yards_to_go >= 7:
            plays.append("PASS_SCREEN_RB")

        # Add deep passes on early downs
        if self.game_state.down_state.down <= 2:
            plays.extend(["PASS_FOUR_VERTS", "PASS_CORNER"])

        return plays
