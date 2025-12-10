"""
Scouting stages and progression.

Defines the stages of scouting and what information is revealed at each level.
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional


class ScoutingStage(Enum):
    """
    Stages of scouting a player.

    Each stage reveals more detailed attribute information.
    """
    # No scouting - only see name, position, school/team, age
    UNKNOWN = auto()

    # Basic film study - see physical measurables, general impression
    BASIC = auto()

    # Detailed film breakdown - see key position attributes
    INTERMEDIATE = auto()

    # In-person workouts, interviews - see mental/intangible attributes
    ADVANCED = auto()

    # Private workouts, full evaluation - all attributes revealed
    COMPLETE = auto()


class ScoutingLevel(Enum):
    """
    Scout quality levels affecting accuracy.

    Better scouts produce more accurate projections.
    """
    ROOKIE = "rookie"  # New scout, high variance
    AVERAGE = "average"  # Standard accuracy
    EXPERIENCED = "experienced"  # Good accuracy
    ELITE = "elite"  # Minimal variance, near-true values


# Attributes revealed at each scouting stage
# Organized by what kind of evaluation reveals them
STAGE_REQUIREMENTS: dict[ScoutingStage, list[str]] = {
    ScoutingStage.UNKNOWN: [],  # Nothing revealed

    ScoutingStage.BASIC: [
        # Physical measurables visible from combine/tape
        "speed",
        "acceleration",
        "agility",
        "strength",
        "jumping",
        "stamina",
    ],

    ScoutingStage.INTERMEDIATE: [
        # Position-specific skills visible from detailed film
        # Passing
        "throw_power",
        "throw_accuracy_short",
        "throw_accuracy_med",
        "throw_accuracy_deep",
        # Rushing
        "carrying",
        "trucking",
        "elusiveness",
        "spin_move",
        "juke_move",
        "stiff_arm",
        "break_tackle",
        "ball_carrier_vision",
        # Receiving
        "catching",
        "catch_in_traffic",
        "spectacular_catch",
        "route_running",
        "release",
        # Blocking
        "pass_block",
        "run_block",
        "impact_blocking",
        # Defense
        "tackle",
        "hit_power",
        "block_shedding",
        "pursuit",
        "man_coverage",
        "zone_coverage",
        "press",
        "finesse_moves",
        "power_moves",
        # Special teams
        "kick_power",
        "kick_accuracy",
    ],

    ScoutingStage.ADVANCED: [
        # Mental/intangibles from interviews and in-person
        "throw_on_run",
        "play_action",
        "play_recognition",
        "awareness",
        "learning",
        # Durability (medical evaluations)
        "injury",
        "toughness",
    ],

    ScoutingStage.COMPLETE: [
        # Hidden attributes - only from extensive evaluation
        "potential",  # The big one - player ceiling
        # Body part durability (deep medical)
        "head_durability",
        "torso_durability",
        "left_arm_durability",
        "right_arm_durability",
        "left_leg_durability",
        "right_leg_durability",
        "kick_return",
    ],
}


def get_attributes_for_stage(stage: ScoutingStage) -> list[str]:
    """
    Get all attributes revealed up to and including a stage.

    Args:
        stage: The scouting stage

    Returns:
        List of all attribute names visible at this stage
    """
    all_attrs = []
    for s in ScoutingStage:
        all_attrs.extend(STAGE_REQUIREMENTS.get(s, []))
        if s == stage:
            break
    return all_attrs


def get_newly_revealed_attributes(
    from_stage: ScoutingStage,
    to_stage: ScoutingStage,
) -> list[str]:
    """
    Get attributes newly revealed by advancing from one stage to another.

    Args:
        from_stage: Starting stage
        to_stage: Target stage

    Returns:
        List of attribute names newly revealed
    """
    from_attrs = set(get_attributes_for_stage(from_stage))
    to_attrs = set(get_attributes_for_stage(to_stage))
    return list(to_attrs - from_attrs)


# Scouting costs (in scouting points or budget units)
SCOUTING_COSTS: dict[ScoutingStage, int] = {
    ScoutingStage.UNKNOWN: 0,
    ScoutingStage.BASIC: 1,
    ScoutingStage.INTERMEDIATE: 3,
    ScoutingStage.ADVANCED: 5,
    ScoutingStage.COMPLETE: 8,
}


def calculate_scouting_cost(
    current_stage: ScoutingStage,
    target_stage: ScoutingStage,
) -> int:
    """
    Calculate cost to advance scouting from one stage to another.

    Args:
        current_stage: Player's current scouting stage
        target_stage: Desired scouting stage

    Returns:
        Total cost to advance (0 if already at or past target)
    """
    if target_stage.value <= current_stage.value:
        return 0

    total = 0
    for stage in ScoutingStage:
        if stage.value > current_stage.value and stage.value <= target_stage.value:
            total += SCOUTING_COSTS.get(stage, 0)

    return total


def get_next_stage(current: ScoutingStage) -> Optional[ScoutingStage]:
    """Get the next scouting stage, or None if at COMPLETE."""
    stages = list(ScoutingStage)
    current_idx = stages.index(current)
    if current_idx < len(stages) - 1:
        return stages[current_idx + 1]
    return None
