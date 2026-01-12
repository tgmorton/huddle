"""Penalties System - Flag resolution during plays.

Handles penalty types, probabilities, and yardage adjustments.
Based on NFL penalty rates and common football rules.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Literal


# =============================================================================
# Penalty Types
# =============================================================================

class PenaltyType(Enum):
    """Types of penalties."""
    # Pre-snap offense
    FALSE_START = "false_start"
    DELAY_OF_GAME = "delay_of_game"
    ILLEGAL_FORMATION = "illegal_formation"
    ILLEGAL_MOTION = "illegal_motion"
    ILLEGAL_SHIFT = "illegal_shift"

    # Pre-snap defense
    ENCROACHMENT = "encroachment"
    NEUTRAL_ZONE_INFRACTION = "neutral_zone_infraction"
    OFFSIDES = "offsides"

    # Offensive penalties during play
    HOLDING_OFFENSE = "holding_offense"
    ILLEGAL_BLOCK = "illegal_block"
    INELIGIBLE_RECEIVER = "ineligible_receiver"
    INTENTIONAL_GROUNDING = "intentional_grounding"

    # Defensive penalties during play
    HOLDING_DEFENSE = "holding_defense"
    PASS_INTERFERENCE_DEFENSE = "pass_interference_defense"
    ROUGHING_THE_PASSER = "roughing_the_passer"
    UNNECESSARY_ROUGHNESS = "unnecessary_roughness"
    HORSE_COLLAR = "horse_collar"
    FACEMASK = "facemask"

    # Offensive pass interference
    PASS_INTERFERENCE_OFFENSE = "pass_interference_offense"


class PenaltyTiming(Enum):
    """When the penalty occurred."""
    PRE_SNAP = "pre_snap"
    DURING_PLAY = "during_play"
    AFTER_PLAY = "after_play"


# =============================================================================
# Penalty Data
# =============================================================================

@dataclass
class PenaltyInfo:
    """Information about a penalty type."""
    penalty_type: PenaltyType
    yards: int
    is_spot_foul: bool = False  # Penalty enforced from spot of foul
    automatic_first_down: bool = False  # Results in automatic first down
    loss_of_down: bool = False  # Offense loses a down
    timing: PenaltyTiming = PenaltyTiming.DURING_PLAY
    team: Literal["offense", "defense"] = "offense"
    description: str = ""


# Penalty definitions with yardage and rules
PENALTY_INFO = {
    # Pre-snap offense (5 yards)
    PenaltyType.FALSE_START: PenaltyInfo(
        PenaltyType.FALSE_START, 5, timing=PenaltyTiming.PRE_SNAP,
        team="offense", description="False start"
    ),
    PenaltyType.DELAY_OF_GAME: PenaltyInfo(
        PenaltyType.DELAY_OF_GAME, 5, timing=PenaltyTiming.PRE_SNAP,
        team="offense", description="Delay of game"
    ),
    PenaltyType.ILLEGAL_FORMATION: PenaltyInfo(
        PenaltyType.ILLEGAL_FORMATION, 5, timing=PenaltyTiming.PRE_SNAP,
        team="offense", description="Illegal formation"
    ),
    PenaltyType.ILLEGAL_MOTION: PenaltyInfo(
        PenaltyType.ILLEGAL_MOTION, 5, timing=PenaltyTiming.PRE_SNAP,
        team="offense", description="Illegal motion"
    ),
    PenaltyType.ILLEGAL_SHIFT: PenaltyInfo(
        PenaltyType.ILLEGAL_SHIFT, 5, timing=PenaltyTiming.PRE_SNAP,
        team="offense", description="Illegal shift"
    ),

    # Pre-snap defense (5 yards)
    PenaltyType.ENCROACHMENT: PenaltyInfo(
        PenaltyType.ENCROACHMENT, 5, timing=PenaltyTiming.PRE_SNAP,
        team="defense", description="Encroachment"
    ),
    PenaltyType.NEUTRAL_ZONE_INFRACTION: PenaltyInfo(
        PenaltyType.NEUTRAL_ZONE_INFRACTION, 5, timing=PenaltyTiming.PRE_SNAP,
        team="defense", description="Neutral zone infraction"
    ),
    PenaltyType.OFFSIDES: PenaltyInfo(
        PenaltyType.OFFSIDES, 5, timing=PenaltyTiming.PRE_SNAP,
        team="defense", description="Offsides"
    ),

    # Offensive during play (10 yards)
    PenaltyType.HOLDING_OFFENSE: PenaltyInfo(
        PenaltyType.HOLDING_OFFENSE, 10,
        team="offense", description="Offensive holding"
    ),
    PenaltyType.ILLEGAL_BLOCK: PenaltyInfo(
        PenaltyType.ILLEGAL_BLOCK, 10,
        team="offense", description="Illegal block in the back"
    ),
    PenaltyType.INELIGIBLE_RECEIVER: PenaltyInfo(
        PenaltyType.INELIGIBLE_RECEIVER, 5,
        team="offense", description="Ineligible receiver downfield"
    ),
    PenaltyType.INTENTIONAL_GROUNDING: PenaltyInfo(
        PenaltyType.INTENTIONAL_GROUNDING, 10, is_spot_foul=True, loss_of_down=True,
        team="offense", description="Intentional grounding"
    ),

    # Defensive during play
    PenaltyType.HOLDING_DEFENSE: PenaltyInfo(
        PenaltyType.HOLDING_DEFENSE, 5, automatic_first_down=True,
        team="defense", description="Defensive holding"
    ),
    PenaltyType.PASS_INTERFERENCE_DEFENSE: PenaltyInfo(
        PenaltyType.PASS_INTERFERENCE_DEFENSE, 0, is_spot_foul=True, automatic_first_down=True,
        team="defense", description="Pass interference"
    ),
    PenaltyType.ROUGHING_THE_PASSER: PenaltyInfo(
        PenaltyType.ROUGHING_THE_PASSER, 15, automatic_first_down=True,
        team="defense", description="Roughing the passer"
    ),
    PenaltyType.UNNECESSARY_ROUGHNESS: PenaltyInfo(
        PenaltyType.UNNECESSARY_ROUGHNESS, 15, automatic_first_down=True,
        team="defense", description="Unnecessary roughness"
    ),
    PenaltyType.HORSE_COLLAR: PenaltyInfo(
        PenaltyType.HORSE_COLLAR, 15, automatic_first_down=True,
        team="defense", description="Horse collar tackle"
    ),
    PenaltyType.FACEMASK: PenaltyInfo(
        PenaltyType.FACEMASK, 15, automatic_first_down=True,
        team="defense", description="Facemask"
    ),

    # Offensive pass interference (10 yards)
    PenaltyType.PASS_INTERFERENCE_OFFENSE: PenaltyInfo(
        PenaltyType.PASS_INTERFERENCE_OFFENSE, 10,
        team="offense", description="Offensive pass interference"
    ),
}


# =============================================================================
# Penalty Probabilities (per play)
# =============================================================================

# NFL averages roughly 12-13 penalties per game, ~5.5 per team
# With ~125 plays per game, that's ~10% penalty rate per play
# But most plays have no penalties, so we model it as:
# - 6% chance of any penalty on a play
# - Then weighted by penalty type

BASE_PENALTY_RATE = 0.06  # 6% of plays have a penalty

# Relative weights for penalty types (must sum to 1.0)
PENALTY_WEIGHTS = {
    # Pre-snap (30%)
    PenaltyType.FALSE_START: 0.12,
    PenaltyType.DELAY_OF_GAME: 0.03,
    PenaltyType.ILLEGAL_FORMATION: 0.02,
    PenaltyType.ILLEGAL_MOTION: 0.02,
    PenaltyType.ENCROACHMENT: 0.04,
    PenaltyType.NEUTRAL_ZONE_INFRACTION: 0.04,
    PenaltyType.OFFSIDES: 0.03,

    # During play (70%)
    PenaltyType.HOLDING_OFFENSE: 0.25,  # Most common
    PenaltyType.HOLDING_DEFENSE: 0.08,
    PenaltyType.PASS_INTERFERENCE_DEFENSE: 0.12,
    PenaltyType.PASS_INTERFERENCE_OFFENSE: 0.02,
    PenaltyType.ILLEGAL_BLOCK: 0.04,
    PenaltyType.ROUGHING_THE_PASSER: 0.03,
    PenaltyType.FACEMASK: 0.04,
    PenaltyType.UNNECESSARY_ROUGHNESS: 0.03,
    PenaltyType.HORSE_COLLAR: 0.01,
    PenaltyType.INTENTIONAL_GROUNDING: 0.02,
    PenaltyType.INELIGIBLE_RECEIVER: 0.02,
    PenaltyType.ILLEGAL_SHIFT: 0.02,
}


# =============================================================================
# Penalty Result
# =============================================================================

@dataclass
class PenaltyResult:
    """Result of penalty resolution."""
    has_penalty: bool = False
    penalty_type: Optional[PenaltyType] = None
    penalty_info: Optional[PenaltyInfo] = None
    yards: int = 0
    new_down: int = 1
    new_distance: int = 10
    new_los: float = 0.0
    description: str = ""
    accepted: bool = True  # Offense typically declines beneficial penalties

    @property
    def on_offense(self) -> bool:
        """Whether penalty is on offense."""
        if self.penalty_info:
            return self.penalty_info.team == "offense"
        return False

    @property
    def on_defense(self) -> bool:
        """Whether penalty is on defense."""
        if self.penalty_info:
            return self.penalty_info.team == "defense"
        return False


# =============================================================================
# Penalty Resolver
# =============================================================================

class PenaltyResolver:
    """Resolves penalties during plays.

    Usage:
        resolver = PenaltyResolver()

        # Check for penalty on a play
        result = resolver.check_for_penalty(
            play_type="pass",
            down=2,
            distance=7,
            los=35.0,
        )

        if result.has_penalty:
            # Apply penalty
            new_los = result.new_los
            new_down = result.new_down
            new_distance = result.new_distance
    """

    def __init__(self, penalty_rate: float = BASE_PENALTY_RATE):
        self.penalty_rate = penalty_rate

    def check_for_penalty(
        self,
        play_type: Literal["pass", "run"] = "pass",
        down: int = 1,
        distance: int = 10,
        los: float = 25.0,
        play_yards: float = 0.0,
    ) -> PenaltyResult:
        """Check if a penalty occurred on a play.

        Args:
            play_type: Type of play (pass or run)
            down: Current down (1-4)
            distance: Yards to first down
            los: Line of scrimmage (yards from own goal)
            play_yards: Yards gained on the play (for spot fouls)

        Returns:
            PenaltyResult with penalty details if one occurred
        """
        # Roll for penalty
        if random.random() >= self.penalty_rate:
            return PenaltyResult(has_penalty=False)

        # Select penalty type based on weights
        penalty_type = self._select_penalty_type(play_type)
        penalty_info = PENALTY_INFO[penalty_type]

        # Calculate new field position
        new_los, new_down, new_distance = self._apply_penalty(
            penalty_info=penalty_info,
            down=down,
            distance=distance,
            los=los,
            play_yards=play_yards,
        )

        # Build description
        team_str = "on the offense" if penalty_info.team == "offense" else "on the defense"
        desc = f"{penalty_info.description} {team_str}, {penalty_info.yards} yards"
        if penalty_info.automatic_first_down and penalty_info.team == "defense":
            desc += ", automatic first down"

        return PenaltyResult(
            has_penalty=True,
            penalty_type=penalty_type,
            penalty_info=penalty_info,
            yards=penalty_info.yards,
            new_down=new_down,
            new_distance=new_distance,
            new_los=new_los,
            description=desc,
        )

    def _select_penalty_type(
        self,
        play_type: Literal["pass", "run"],
    ) -> PenaltyType:
        """Select a penalty type based on weights and play context."""
        # Adjust weights based on play type
        adjusted_weights = dict(PENALTY_WEIGHTS)

        if play_type == "run":
            # More holding, less PI on run plays
            adjusted_weights[PenaltyType.HOLDING_OFFENSE] *= 1.3
            adjusted_weights[PenaltyType.PASS_INTERFERENCE_DEFENSE] *= 0.1
            adjusted_weights[PenaltyType.PASS_INTERFERENCE_OFFENSE] *= 0.1
            adjusted_weights[PenaltyType.INTENTIONAL_GROUNDING] = 0.0
            adjusted_weights[PenaltyType.ROUGHING_THE_PASSER] *= 0.3

        # Normalize weights
        total = sum(adjusted_weights.values())
        normalized = {k: v / total for k, v in adjusted_weights.items()}

        # Select based on weights
        roll = random.random()
        cumulative = 0.0
        for penalty_type, weight in normalized.items():
            cumulative += weight
            if roll <= cumulative:
                return penalty_type

        # Fallback
        return PenaltyType.HOLDING_OFFENSE

    def _apply_penalty(
        self,
        penalty_info: PenaltyInfo,
        down: int,
        distance: int,
        los: float,
        play_yards: float,
    ) -> tuple[float, int, int]:
        """Apply penalty and return new field position.

        Returns:
            (new_los, new_down, new_distance)
        """
        # Get base yards
        yards = penalty_info.yards

        # Handle spot fouls
        if penalty_info.is_spot_foul:
            # Penalty enforced from spot of foul
            spot = los + play_yards
            if penalty_info.team == "offense":
                # Move back from spot
                new_los = max(1.0, spot - yards) if yards > 0 else spot
            else:
                # Move forward from spot (defensive PI)
                # DPI is spot foul, minimum of actual spot
                new_los = min(99.0, spot + yards) if yards > 0 else spot
        else:
            # Penalty enforced from line of scrimmage
            if penalty_info.team == "offense":
                # Move back
                new_los = max(1.0, los - yards)
            else:
                # Move forward
                new_los = min(99.0, los + yards)

        # Handle half-the-distance-to-goal
        if penalty_info.team == "offense" and los <= yards:
            new_los = los / 2
        if penalty_info.team == "defense" and (100 - los) <= yards:
            new_los = los + (100 - los) / 2

        # Calculate new down and distance
        if penalty_info.timing == PenaltyTiming.PRE_SNAP:
            # Replay the down
            new_down = down
            if penalty_info.team == "offense":
                new_distance = distance + int(los - new_los)
            else:
                new_distance = max(1, distance - int(new_los - los))
        else:
            # During/after play
            if penalty_info.team == "offense":
                # Offense penalty: replay down with more distance
                if penalty_info.loss_of_down:
                    new_down = down + 1
                else:
                    new_down = down
                new_distance = distance + int(los - new_los)
            else:
                # Defense penalty
                if penalty_info.automatic_first_down:
                    new_down = 1
                    new_distance = min(10, int(100 - new_los))
                else:
                    new_down = down
                    new_distance = max(1, distance - int(new_los - los))

        # Ensure valid values
        new_distance = max(1, min(99, new_distance))
        new_down = min(4, max(1, new_down))

        return new_los, new_down, new_distance

    def should_accept_penalty(
        self,
        penalty_result: PenaltyResult,
        play_yards: float,
        down: int,
        distance: int,
    ) -> bool:
        """Decide whether to accept or decline a penalty.

        Returns True if penalty should be accepted.
        """
        if not penalty_result.has_penalty:
            return False

        # Offensive penalties are always enforced (can't decline your own)
        if penalty_result.on_offense:
            return True

        # For defensive penalties, compare outcome
        # Accept if it results in better field position or first down

        # If penalty gives automatic first down, usually accept
        if penalty_result.penalty_info and penalty_result.penalty_info.automatic_first_down:
            # Unless play result was even better (big gain)
            if play_yards >= distance:  # Got first down anyway
                if play_yards > penalty_result.yards:  # And gained more yards
                    return False
            return True

        # Compare yards: accept if penalty gives more than play result
        return penalty_result.yards > play_yards


def check_for_penalty(
    play_type: Literal["pass", "run"] = "pass",
    down: int = 1,
    distance: int = 10,
    los: float = 25.0,
    play_yards: float = 0.0,
) -> PenaltyResult:
    """Convenience function to check for penalty.

    Args:
        play_type: Type of play (pass or run)
        down: Current down (1-4)
        distance: Yards to first down
        los: Line of scrimmage
        play_yards: Yards gained on the play

    Returns:
        PenaltyResult
    """
    resolver = PenaltyResolver()
    return resolver.check_for_penalty(
        play_type=play_type,
        down=down,
        distance=distance,
        los=los,
        play_yards=play_yards,
    )
