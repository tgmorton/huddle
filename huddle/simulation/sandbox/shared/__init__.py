"""Shared utilities for sandbox simulations.

This module provides unified implementations of common components used
across pocket_sim, route_sim, play_sim, and the integrated simulator.

Key components:
- Vec2: Unified 2D vector class
- Coordinate system constants and conversion utilities
- Role-specific player attribute classes
- Field position context

Usage:
    from huddle.simulation.sandbox.shared import Vec2, FieldContext
    from huddle.simulation.sandbox.shared import OLineAttributes, DLineAttributes
"""

from .vec2 import Vec2

from .coordinate import (
    # Field dimensions
    FIELD_WIDTH,
    HALF_FIELD_WIDTH,
    SIDELINE_LEFT,
    SIDELINE_RIGHT,
    LEFT_HASH,
    RIGHT_HASH,
    NFL_HASH_DISTANCE,
    COLLEGE_HASH_DISTANCE,
    LEFT_NUMBERS,
    RIGHT_NUMBERS,
    NUMBERS_DISTANCE_FROM_SIDELINE,
    # Player position constants
    QB_SHOTGUN_DEPTH,
    QB_PISTOL_DEPTH,
    QB_UNDER_CENTER_DEPTH,
    OL_DEPTH,
    OL_SPACING,
    LT_X,
    LG_X,
    C_X,
    RG_X,
    RT_X,
    DL_DEPTH,
    DL_DEPTH_TILTED,
    DB_PRESS_DEPTH,
    DB_OFF_DEPTH,
    DB_DEEP_DEPTH,
    WR_OUTSIDE_X,
    WR_SLOT_X,
    TE_X,
    # Coordinate conversion
    convert_pocket_to_unified,
    convert_unified_to_pocket,
    convert_pocket_vec2_to_unified,
    convert_unified_vec2_to_pocket,
    # Boundary utilities
    FieldSide,
    get_field_side,
    get_boundary_side,
    get_distance_to_sideline,
    is_in_bounds,
    clamp_to_field,
    # Zone definitions
    ZoneBoundary,
    FLAT_LEFT,
    FLAT_RIGHT,
    HOOK_LEFT,
    HOOK_RIGHT,
    DEEP_THIRD_LEFT,
    DEEP_THIRD_MIDDLE,
    DEEP_THIRD_RIGHT,
    DEEP_HALF_LEFT,
    DEEP_HALF_RIGHT,
)

from .player_attributes import (
    BaseSimAttributes,
    OLineAttributes,
    DLineAttributes,
    QBSimAttributes,
    ReceiverSimAttributes,
    DBSimAttributes,
    LBSimAttributes,
)

from .field import (
    HashPosition,
    FieldZone,
    FieldContext,
    adjust_receiver_alignment,
    adjust_route_depth,
)


__all__ = [
    # Vec2
    "Vec2",
    # Field dimensions
    "FIELD_WIDTH",
    "HALF_FIELD_WIDTH",
    "SIDELINE_LEFT",
    "SIDELINE_RIGHT",
    "LEFT_HASH",
    "RIGHT_HASH",
    "NFL_HASH_DISTANCE",
    "COLLEGE_HASH_DISTANCE",
    "LEFT_NUMBERS",
    "RIGHT_NUMBERS",
    "NUMBERS_DISTANCE_FROM_SIDELINE",
    # Player positions
    "QB_SHOTGUN_DEPTH",
    "QB_PISTOL_DEPTH",
    "QB_UNDER_CENTER_DEPTH",
    "OL_DEPTH",
    "OL_SPACING",
    "LT_X",
    "LG_X",
    "C_X",
    "RG_X",
    "RT_X",
    "DL_DEPTH",
    "DL_DEPTH_TILTED",
    "DB_PRESS_DEPTH",
    "DB_OFF_DEPTH",
    "DB_DEEP_DEPTH",
    "WR_OUTSIDE_X",
    "WR_SLOT_X",
    "TE_X",
    # Coordinate conversion
    "convert_pocket_to_unified",
    "convert_unified_to_pocket",
    "convert_pocket_vec2_to_unified",
    "convert_unified_vec2_to_pocket",
    # Boundary utilities
    "FieldSide",
    "get_field_side",
    "get_boundary_side",
    "get_distance_to_sideline",
    "is_in_bounds",
    "clamp_to_field",
    # Zone definitions
    "ZoneBoundary",
    "FLAT_LEFT",
    "FLAT_RIGHT",
    "HOOK_LEFT",
    "HOOK_RIGHT",
    "DEEP_THIRD_LEFT",
    "DEEP_THIRD_MIDDLE",
    "DEEP_THIRD_RIGHT",
    "DEEP_HALF_LEFT",
    "DEEP_HALF_RIGHT",
    # Player attributes
    "BaseSimAttributes",
    "OLineAttributes",
    "DLineAttributes",
    "QBSimAttributes",
    "ReceiverSimAttributes",
    "DBSimAttributes",
    "LBSimAttributes",
    # Field context
    "HashPosition",
    "FieldZone",
    "FieldContext",
    "adjust_receiver_alignment",
    "adjust_route_depth",
]
