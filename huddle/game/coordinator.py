"""Play Coordinator - AI play-calling for auto-play mode.

Provides intelligent play selection based on:
- Down and distance
- Field position
- Score differential
- Time remaining
- Team tendencies

Two modes:
1. Offensive Coordinator - Calls offensive plays
2. Defensive Coordinator - Calls defensive coverages
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, List, Optional, Tuple

from huddle.core.playbook.play_codes import (
    OFFENSIVE_PLAYS,
    DEFENSIVE_PLAYS,
    PlayCategory,
)
from huddle.simulation.v2.orchestrator import PlayConfig

from huddle.game.play_adapter import PlayAdapter, PLAY_ROUTE_MAP, PLAY_RUN_MAP

if TYPE_CHECKING:
    from huddle.core.models.team import Team
    from huddle.simulation.v2.core.entities import Player as V2Player


# =============================================================================
# Situation Analysis
# =============================================================================

class GameSituation(Enum):
    """High-level game situation categories."""
    NORMAL = "normal"
    RED_ZONE = "red_zone"
    GOAL_LINE = "goal_line"
    TWO_MINUTE = "two_minute"
    GARBAGE_TIME = "garbage_time"
    PROTECT_LEAD = "protect_lead"
    COMEBACK = "comeback"
    MUST_SCORE = "must_score"


@dataclass
class SituationContext:
    """Complete context for play-calling decisions."""
    down: int
    distance: int
    los: float  # 0-100, higher = closer to opponent end zone
    quarter: int
    time_remaining: float  # Seconds in quarter
    score_diff: int  # Positive = winning, negative = losing
    timeouts: int

    @property
    def yards_to_goal(self) -> float:
        return 100 - self.los

    @property
    def is_red_zone(self) -> bool:
        return self.los >= 80

    @property
    def is_goal_line(self) -> bool:
        return self.los >= 95

    @property
    def is_two_minute(self) -> bool:
        return self.quarter in (2, 4) and self.time_remaining <= 120

    @property
    def is_fourth_quarter(self) -> bool:
        return self.quarter == 4

    @property
    def is_short_yardage(self) -> bool:
        return self.distance <= 2

    @property
    def is_long_yardage(self) -> bool:
        return self.distance >= 7

    @property
    def game_situation(self) -> GameSituation:
        """Determine high-level game situation."""
        # Two-minute drill
        if self.is_two_minute and self.score_diff <= 0:
            return GameSituation.TWO_MINUTE

        # Must score (4th quarter, down by 2+ scores)
        if self.is_fourth_quarter and self.score_diff <= -9 and self.time_remaining <= 300:
            return GameSituation.MUST_SCORE

        # Protect lead (4th quarter, up by 1+ scores)
        if self.is_fourth_quarter and self.score_diff >= 7 and self.time_remaining <= 300:
            return GameSituation.PROTECT_LEAD

        # Garbage time (blowout either way)
        if abs(self.score_diff) >= 21:
            return GameSituation.GARBAGE_TIME

        # Red zone / goal line
        if self.is_goal_line:
            return GameSituation.GOAL_LINE
        if self.is_red_zone:
            return GameSituation.RED_ZONE

        return GameSituation.NORMAL


# =============================================================================
# Play Selection Weights
# =============================================================================

# Base run/pass tendencies by down
DOWN_RUN_TENDENCY = {
    1: 0.45,  # 1st down: balanced
    2: 0.40,  # 2nd down: slightly pass-heavy
    3: 0.25,  # 3rd down: pass-heavy
    4: 0.30,  # 4th down: situational
}

# Distance modifiers (added to base tendency)
DISTANCE_RUN_MODIFIER = {
    (1, 2): 0.25,    # Short yardage: more runs
    (3, 4): 0.10,    # Medium-short
    (5, 7): 0.0,     # Medium: neutral
    (8, 10): -0.10,  # Medium-long: fewer runs
    (11, 99): -0.20, # Long: pass-heavy
}

# Situation overrides
SITUATION_RUN_TENDENCY = {
    GameSituation.PROTECT_LEAD: 0.70,  # Run to kill clock
    GameSituation.TWO_MINUTE: 0.10,    # Pass to move quickly
    GameSituation.MUST_SCORE: 0.15,    # Pass to score fast
    GameSituation.GOAL_LINE: 0.55,     # Slight run tendency
}


# =============================================================================
# Offensive Coordinator
# =============================================================================

@dataclass
class OffensiveCoordinator:
    """AI offensive play-caller.

    Selects plays based on situation, tendencies, and playbook.

    Attributes:
        team: Team for tendencies (optional)
        playbook: Available plays (defaults to all)
        aggression: 0.0-1.0, affects risk-taking
    """

    team: Optional["Team"] = None
    playbook: Optional[List[str]] = None
    aggression: float = 0.5

    def __post_init__(self):
        if self.playbook is None:
            # Use all offensive plays
            self.playbook = list(OFFENSIVE_PLAYS.keys())

        # Get team tendencies if available
        if self.team and self.team.tendencies:
            self.aggression = self.team.tendencies.aggression

    def call_play(self, context: SituationContext) -> str:
        """Select a play for the given situation.

        Args:
            context: Complete situation context

        Returns:
            PlayCode string (e.g., "PASS_SLANT", "RUN_POWER")
        """
        # Determine run vs pass
        is_run = self._decide_run_or_pass(context)

        if is_run:
            return self._select_run_play(context)
        else:
            return self._select_pass_play(context)

    def _decide_run_or_pass(self, context: SituationContext) -> bool:
        """Decide whether to run or pass."""
        # Check for situation overrides
        situation = context.game_situation
        if situation in SITUATION_RUN_TENDENCY:
            run_pct = SITUATION_RUN_TENDENCY[situation]
            return random.random() < run_pct

        # Start with base tendency for down
        run_pct = DOWN_RUN_TENDENCY.get(context.down, 0.40)

        # Apply distance modifier
        for (low, high), modifier in DISTANCE_RUN_MODIFIER.items():
            if low <= context.distance <= high:
                run_pct += modifier
                break

        # Apply team tendency
        if self.team and self.team.tendencies:
            # run_tendency is 0.0-1.0, shift by +/- 0.15
            team_mod = (self.team.tendencies.run_tendency - 0.5) * 0.30
            run_pct += team_mod

        # Clamp and roll
        run_pct = max(0.10, min(0.90, run_pct))
        return random.random() < run_pct

    def _select_run_play(self, context: SituationContext) -> str:
        """Select a specific run play."""
        available_runs = [p for p in self.playbook if p.startswith("RUN_")]

        if not available_runs:
            return "RUN_INSIDE_ZONE"  # Fallback

        # Short yardage: prefer power, sneak
        if context.is_short_yardage:
            preferred = ["RUN_POWER", "RUN_QB_SNEAK", "RUN_INSIDE_ZONE"]
            for play in preferred:
                if play in available_runs:
                    return play

        # Goal line: power, inside zone
        if context.is_goal_line:
            preferred = ["RUN_POWER", "RUN_INSIDE_ZONE", "RUN_QB_SNEAK"]
            for play in preferred:
                if play in available_runs:
                    return play

        # Long yardage: draw to catch defense off guard
        if context.is_long_yardage and random.random() < 0.3:
            if "RUN_DRAW" in available_runs:
                return "RUN_DRAW"

        # Default: weight toward zone runs
        weights = []
        for play in available_runs:
            if "ZONE" in play:
                weights.append(2.0)
            elif play == "RUN_POWER":
                weights.append(1.5)
            else:
                weights.append(1.0)

        return random.choices(available_runs, weights=weights)[0]

    def _select_pass_play(self, context: SituationContext) -> str:
        """Select a specific pass play."""
        available_passes = [p for p in self.playbook if p.startswith("PASS_")]

        if not available_passes:
            return "PASS_SLANT"  # Fallback

        # Two-minute drill: quick passes, no play action
        if context.game_situation == GameSituation.TWO_MINUTE:
            quick = ["PASS_SLANT", "PASS_QUICK_OUT", "PASS_HITCH", "PASS_DIG"]
            options = [p for p in quick if p in available_passes]
            if options:
                return random.choice(options)

        # Short yardage: quick hitters
        if context.is_short_yardage:
            quick = ["PASS_SLANT", "PASS_HITCH", "PASS_QUICK_OUT"]
            options = [p for p in quick if p in available_passes]
            if options:
                return random.choice(options)

        # Long yardage: deep routes, screens
        if context.is_long_yardage:
            deep = ["PASS_FOUR_VERTS", "PASS_POST", "PASS_CORNER", "PASS_SCREEN_RB"]
            options = [p for p in deep if p in available_passes]
            if options:
                return random.choice(options)

        # Red zone: shorter routes, back shoulder
        if context.is_red_zone:
            rz = ["PASS_SLANT", "PASS_CORNER", "PASS_FADE", "PASS_MESH"]
            options = [p for p in rz if p in available_passes]
            if options:
                return random.choice(options)

        # Normal situation: weighted selection
        weights = []
        for play in available_passes:
            # Weight based on distance
            if context.distance <= 5:
                # Short distance: quick game
                if play in ["PASS_SLANT", "PASS_HITCH", "PASS_QUICK_OUT"]:
                    weights.append(2.0)
                else:
                    weights.append(1.0)
            elif context.distance <= 10:
                # Medium: balanced
                if play in ["PASS_CURL", "PASS_DIG", "PASS_CROSSER"]:
                    weights.append(2.0)
                else:
                    weights.append(1.0)
            else:
                # Long: deep routes
                if play in ["PASS_FOUR_VERTS", "PASS_POST", "PASS_CORNER"]:
                    weights.append(2.0)
                else:
                    weights.append(1.0)

        return random.choices(available_passes, weights=weights)[0]

    def should_go_for_it(self, context: SituationContext) -> bool:
        """Decide whether to go for it on 4th down.

        Returns True if should go for it, False if should punt/kick FG.
        """
        if context.down != 4:
            return False

        # Always go for it in goal-to-go inside 2
        if context.is_goal_line and context.distance <= 2:
            return True

        # Two-minute drill: go for it more
        if context.game_situation == GameSituation.TWO_MINUTE:
            if context.distance <= 3:
                return True
            if context.los >= 50:  # Past midfield
                return True

        # Must score: always go for it
        if context.game_situation == GameSituation.MUST_SCORE:
            return True

        # Normal: very conservative
        if context.distance <= 1 and context.los >= 60:
            return random.random() < self.aggression

        return False

    def should_kick_fg(self, context: SituationContext) -> bool:
        """Decide whether to attempt a field goal."""
        if context.down != 4:
            return False

        # Don't kick if should go for it
        if self.should_go_for_it(context):
            return False

        # FG range: inside opponent 35 (52 yard attempt)
        fg_distance = context.yards_to_goal + 17  # Add 17 for snap + end zone
        return fg_distance <= 52


# =============================================================================
# Defensive Coordinator
# =============================================================================

@dataclass
class DefensiveCoordinator:
    """AI defensive play-caller.

    Selects coverages based on situation and offensive tendencies.

    Attributes:
        team: Team for tendencies (optional)
        blitz_tendency: 0.0-1.0, affects blitz frequency
    """

    team: Optional["Team"] = None
    blitz_tendency: float = 0.3

    def __post_init__(self):
        if self.team and self.team.tendencies:
            self.blitz_tendency = self.team.tendencies.blitz_tendency

    def call_coverage(self, context: SituationContext) -> str:
        """Select a coverage for the given situation.

        Args:
            context: Complete situation context

        Returns:
            Defensive PlayCode string (e.g., "COVER_3", "MAN_PRESS")
        """
        # Decide man vs zone
        is_man = self._decide_man_or_zone(context)

        # Decide to blitz
        is_blitz = self._decide_blitz(context)

        if is_blitz:
            return self._select_blitz(context)
        elif is_man:
            return self._select_man_coverage(context)
        else:
            return self._select_zone_coverage(context)

    def _decide_man_or_zone(self, context: SituationContext) -> bool:
        """Decide man or zone coverage."""
        # Red zone: more man
        if context.is_red_zone:
            return random.random() < 0.60

        # Short yardage: man to prevent easy completions
        if context.is_short_yardage:
            return random.random() < 0.55

        # Long yardage: zone to protect deep
        if context.is_long_yardage:
            return random.random() < 0.30

        # Default: slight zone preference
        return random.random() < 0.40

    def _decide_blitz(self, context: SituationContext) -> bool:
        """Decide whether to blitz."""
        # Don't blitz as much in two-minute
        if context.game_situation == GameSituation.TWO_MINUTE:
            return random.random() < self.blitz_tendency * 0.5

        # Blitz more on 3rd and long
        if context.down == 3 and context.is_long_yardage:
            return random.random() < self.blitz_tendency * 1.5

        # Default
        return random.random() < self.blitz_tendency

    def _select_blitz(self, context: SituationContext) -> str:
        """Select a blitz package."""
        blitzes = ["BLITZ_ZONE", "BLITZ_DOG", "BLITZ_FIRE"]

        # Short yardage: aggressive blitz
        if context.is_short_yardage:
            return random.choice(["BLITZ_DOG", "COVER_0"])

        return random.choice(blitzes)

    def _select_man_coverage(self, context: SituationContext) -> str:
        """Select a man coverage."""
        # Red zone: press
        if context.is_red_zone:
            return "MAN_PRESS"

        # 50/50 press vs off
        return random.choice(["MAN_PRESS", "MAN_OFF", "COVER_1"])

    def _select_zone_coverage(self, context: SituationContext) -> str:
        """Select a zone coverage."""
        zones = ["COVER_2", "COVER_3", "COVER_4"]

        # Long yardage: more Cover 4 (quarters)
        if context.is_long_yardage:
            return random.choice(["COVER_4", "COVER_3", "COVER_2"])

        # Short yardage: Cover 2 to stop quick routes
        if context.is_short_yardage:
            return random.choice(["COVER_2", "COVER_3"])

        # Default
        return random.choice(zones)


# =============================================================================
# Convenience Functions
# =============================================================================

def get_play_call(
    context: SituationContext,
    team: Optional["Team"] = None,
) -> Tuple[str, str]:
    """Get both offensive and defensive play calls.

    Args:
        context: Game situation
        team: Offensive team (for tendencies)

    Returns:
        Tuple of (offensive_play, defensive_play)
    """
    oc = OffensiveCoordinator(team=team)
    dc = DefensiveCoordinator()

    return oc.call_play(context), dc.call_coverage(context)
