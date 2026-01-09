"""Role-specific WorldState contexts for AI brains.

Each brain type receives a context tailored to its needs:
- Base fields that all brains need (position, teammates, ball, etc.)
- Role-specific fields (QB gets timing info, WR gets route info, etc.)

This clarifies the contract between orchestrator and brains,
making it explicit what data each brain type can access.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.entities import Player, Field
    from ..core.vec2 import Vec2
    from ..core.phases import PlayPhase
    from ..game_state import PlayHistory, GameSituation


# Forward reference for type hints
class PlayerView:
    """Imported from orchestrator to avoid circular imports."""
    pass


class BallView:
    """Imported from orchestrator to avoid circular imports."""
    pass


# =============================================================================
# Base Context - Shared by all brains
# =============================================================================

@dataclass
class WorldStateBase:
    """Base world state shared by all AI brains.

    Contains the fundamental information every brain needs:
    - Self reference and spatial awareness
    - Teammates and opponents
    - Ball state
    - Time and phase information
    - Situational context (down, distance, etc.)
    """
    # Core identity
    me: Any  # Player - using Any to avoid circular import

    # Other players (as views, not full Player objects)
    teammates: List[Any] = dataclass_field(default_factory=list)  # List[PlayerView]
    opponents: List[Any] = dataclass_field(default_factory=list)  # List[PlayerView]

    # Ball state
    ball: Any = None  # BallView

    # Field reference
    field: Any = None  # Field

    # Time
    current_time: float = 0.0
    tick: int = 0
    dt: float = 0.05  # Time delta for this tick

    # Play context
    phase: Any = None  # PlayPhase
    time_since_snap: float = 0.0

    # Assignment info
    assignment: str = ""
    target_id: Optional[str] = None  # Man coverage target, blocking assignment, etc.

    # Spatial awareness
    threats: List[Any] = dataclass_field(default_factory=list)  # List[PlayerView]
    opportunities: Dict[str, Any] = dataclass_field(default_factory=dict)

    # Situational
    down: int = 1
    distance: float = 10.0
    los_y: float = 0.0  # Line of scrimmage Y position

    # Game-level state
    play_history: Any = None  # PlayHistory
    game_situation: Any = None  # GameSituation

    # Run play flag (needed by multiple brains)
    is_run_play: bool = False

    # Convenience methods
    def get_teammate(self, player_id: str) -> Optional[Any]:
        """Get a specific teammate by ID."""
        for t in self.teammates:
            if t.id == player_id:
                return t
        return None

    def get_opponent(self, player_id: str) -> Optional[Any]:
        """Get a specific opponent by ID."""
        for o in self.opponents:
            if o.id == player_id:
                return o
        return None

    def nearest_threat(self) -> Optional[Any]:
        """Get the closest threat."""
        if not self.threats:
            return None
        return min(self.threats, key=lambda t: t.distance)

    def ball_carrier(self) -> Optional[Any]:
        """Get the ball carrier if any."""
        if self.ball and self.ball.carrier_id:
            if self.ball.carrier_id == self.me.id:
                return None  # That's me
            for t in self.teammates:
                if t.id == self.ball.carrier_id:
                    return t
            for o in self.opponents:
                if o.id == self.ball.carrier_id:
                    return o
        return None


# =============================================================================
# Role-Specific Contexts
# =============================================================================

@dataclass
class QBContext(WorldStateBase):
    """Context for QB brain.

    Adds QB-specific timing and read progression info.
    """
    # Dropback timing
    dropback_depth: float = 7.0  # Target depth for QB dropback
    dropback_target_pos: Any = None  # Vec2 - exact position QB is dropping to
    qb_is_set: bool = False  # True when QB has completed dropback AND planted
    qb_set_time: float = 0.0  # When QB became fully set

    # Pre-snap adjustments
    hot_routes: Dict[str, str] = dataclass_field(default_factory=dict)  # player_id -> route_name

    # Pressure tracking (from PressureSystem)
    pressure_state: Any = None  # PressureState - current pocket pressure


@dataclass
class WRContext(WorldStateBase):
    """Context for WR/receiver brain.

    Adds route-running specific information.
    """
    # Route info
    route_target: Any = None  # Vec2 - current waypoint target
    route_phase: Optional[str] = None  # release, stem, break, post_break, complete
    at_route_break: bool = False  # Is receiver at the break point?
    route_settles: bool = False  # Does this route settle (curl/hitch)?


@dataclass
class OLContext(WorldStateBase):
    """Context for offensive line brain.

    Adds blocking assignment and protection info.
    """
    # Run blocking
    run_play_side: str = ""  # "left", "right", or "balanced"
    run_blocking_assignment: Optional[str] = None  # "zone_step", "combo", etc.
    run_gap_target: Optional[str] = None  # "a_left", "b_right", etc.
    combo_partner_position: Optional[str] = None  # Position to combo with

    # Pass protection
    slide_direction: str = ""  # "left", "right", or ""
    mike_id: Optional[str] = None  # Identified MIKE linebacker

    # State after getting beat
    is_beaten: bool = False  # True if block was just shed


@dataclass
class DLContext(WorldStateBase):
    """Context for defensive line brain.

    Adds pass rush and run defense info.
    """
    # Shed state
    has_shed_immunity: bool = False  # True if just shed a block, free to sprint


@dataclass
class LBContext(WorldStateBase):
    """Context for linebacker brain.

    LBs use base context - they read and react to the play.
    """
    pass  # No additional fields needed currently


@dataclass
class DBContext(WorldStateBase):
    """Context for defensive back (CB/S) brain.

    DBs use base context for coverage responsibilities.
    """
    pass  # No additional fields needed currently


@dataclass
class RBContext(WorldStateBase):
    """Context for running back brain.

    Adds run path and aiming point info.
    """
    # Run play info
    run_path: List[Any] = dataclass_field(default_factory=list)  # List[Vec2] - waypoints
    run_aiming_point: Optional[str] = None  # Target gap (e.g., "a_right")
    run_mesh_depth: float = 4.0  # Yards behind LOS for handoff
    run_play_side: str = ""  # "left", "right", or "balanced"


@dataclass
class BallcarrierContext(WorldStateBase):
    """Context for ballcarrier brain (after catch or during run).

    Ballcarrier needs spatial awareness but not route/assignment info.
    """
    # Shed immunity for broken tackles
    has_shed_immunity: bool = False


# =============================================================================
# Type alias for backwards compatibility
# =============================================================================

# WorldState is now an alias - brains can accept WorldStateBase or any subclass
WorldState = WorldStateBase
