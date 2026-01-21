"""Huddle Position Constants - Player positions during huddle and formation setup.

This module defines where players stand during the HUDDLE phase and provides
configuration for the between-play transition animation.

Coordinate System:
    - Huddle positions are relative to huddle center
    - Huddle center is placed at (ball_x, los_y - huddle_depth)
    - Formation positions are the standard pre-snap alignments

Huddle Formation (offensive):
    QB at center, OL in front arc facing QB, skill players behind/flanking

Huddle Formation (defensive):
    MLB at center calling signals, DL in front, DBs behind/flanking
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from .vec2 import Vec2


# =============================================================================
# Huddle Position Maps
# =============================================================================

# Offensive huddle positions (relative to huddle center, QB at 0,0)
# OL forms arc in front, skill players form arc behind
OFFENSIVE_HUDDLE_POSITIONS: Dict[str, Vec2] = {
    # QB at center, facing team
    "QB1": Vec2(0.0, 0.0),

    # Offensive line in front arc (facing QB)
    "C1": Vec2(0.0, 2.5),
    "LG1": Vec2(-1.5, 2.3),
    "RG1": Vec2(1.5, 2.3),
    "LT1": Vec2(-2.8, 1.8),
    "RT1": Vec2(2.8, 1.8),

    # Skill players behind/flanking QB
    "RB1": Vec2(0.0, -2.0),
    "RB2": Vec2(-1.0, -2.5),  # Second RB if present
    "FB1": Vec2(0.0, -2.5),
    "WR1": Vec2(-2.5, -1.5),
    "WR2": Vec2(2.5, -1.5),
    "WR3": Vec2(-3.5, -0.5),  # Slot receivers flanking
    "WR4": Vec2(3.5, -0.5),
    "TE1": Vec2(2.0, 0.5),    # TE between OL and skill
    "TE2": Vec2(-2.0, 0.5),
}

# Defensive huddle positions (relative to huddle center, MLB at 0,0)
# DL in front, LBs in middle, DBs behind
DEFENSIVE_HUDDLE_POSITIONS: Dict[str, Vec2] = {
    # MLB at center calling signals
    "MLB1": Vec2(0.0, 0.0),
    "MLB2": Vec2(-1.0, 0.0),  # Second MLB if present
    "ILB1": Vec2(1.0, 0.0),
    "ILB2": Vec2(-1.0, 0.0),

    # Defensive line in front (facing MLB)
    "DT1": Vec2(-1.0, -2.0),
    "DT2": Vec2(1.0, -2.0),
    "NT1": Vec2(0.0, -2.0),
    "DE1": Vec2(-2.5, -1.5),
    "DE2": Vec2(2.5, -1.5),

    # OLBs flanking
    "OLB1": Vec2(-2.0, 0.5),
    "OLB2": Vec2(2.0, 0.5),

    # DBs in back arc
    "CB1": Vec2(-3.0, 1.5),
    "CB2": Vec2(3.0, 1.5),
    "CB3": Vec2(-3.5, 2.0),
    "FS1": Vec2(0.0, 2.5),
    "SS1": Vec2(1.5, 2.0),
}


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class HuddleConfig:
    """Configuration for huddle and formation transitions.

    Attributes:
        offense_huddle_depth: How far behind LOS the offensive huddle forms (yards)
        defense_huddle_depth: How far ahead of LOS the defensive huddle forms (yards)
        min_huddle_duration: Minimum time players spend in huddle (seconds)
        jog_to_huddle_speed: Speed multiplier for jogging to huddle (0-1)
        break_to_formation_speed: Speed multiplier for breaking to formation (0-1)
        arrival_threshold: How close players need to be to target (yards)
        no_huddle_enabled: If True, skip HUDDLE phase and go straight to formation
        hurry_up_speed_multiplier: Speed multiplier when no_huddle is enabled
    """
    offense_huddle_depth: float = 10.0  # 10 yards behind LOS
    defense_huddle_depth: float = 15.0  # 15 yards ahead of LOS (their side)
    min_huddle_duration: float = 2.0    # Minimum 2 seconds in huddle
    jog_to_huddle_speed: float = 0.5    # 50% of max speed
    break_to_formation_speed: float = 0.7  # 70% of max speed
    arrival_threshold: float = 0.5      # Within 0.5 yards = arrived
    no_huddle_enabled: bool = False     # Normal huddle by default
    hurry_up_speed_multiplier: float = 1.0  # Full speed for no-huddle


# Default config instance
DEFAULT_HUDDLE_CONFIG = HuddleConfig()


# =============================================================================
# Helper Functions
# =============================================================================

def get_offensive_huddle_position(position_slot: str) -> Vec2:
    """Get the huddle position for an offensive player by their position slot.

    Args:
        position_slot: Position slot identifier (e.g., "QB1", "WR2", "LT1")

    Returns:
        Vec2 position relative to huddle center, or (0, -3) as default
    """
    return OFFENSIVE_HUDDLE_POSITIONS.get(position_slot, Vec2(0.0, -3.0))


def get_defensive_huddle_position(position_slot: str) -> Vec2:
    """Get the huddle position for a defensive player by their position slot.

    Args:
        position_slot: Position slot identifier (e.g., "MLB1", "CB2", "DE1")

    Returns:
        Vec2 position relative to huddle center, or (0, 3) as default
    """
    return DEFENSIVE_HUDDLE_POSITIONS.get(position_slot, Vec2(0.0, 3.0))


def calculate_huddle_center(
    los_y: float,
    ball_x: float,
    is_offense: bool,
    config: HuddleConfig = DEFAULT_HUDDLE_CONFIG,
) -> Vec2:
    """Calculate the center position of a huddle.

    Args:
        los_y: Line of scrimmage Y coordinate
        ball_x: X coordinate of the ball (hash position)
        is_offense: True for offensive huddle, False for defensive
        config: Huddle configuration

    Returns:
        Vec2 position of huddle center in field coordinates
    """
    if is_offense:
        # Offensive huddle is behind LOS (negative Y direction)
        return Vec2(ball_x, los_y - config.offense_huddle_depth)
    else:
        # Defensive huddle is ahead of LOS (positive Y direction)
        return Vec2(ball_x, los_y + config.defense_huddle_depth)


def get_player_huddle_target(
    position_slot: str,
    is_offense: bool,
    huddle_center: Vec2,
) -> Vec2:
    """Get the target position for a player to move to during huddle.

    Args:
        position_slot: Position slot identifier
        is_offense: True for offensive player
        huddle_center: Center of the huddle in field coordinates

    Returns:
        Vec2 target position in field coordinates
    """
    if is_offense:
        relative_pos = get_offensive_huddle_position(position_slot)
    else:
        relative_pos = get_defensive_huddle_position(position_slot)

    return huddle_center + relative_pos
