"""Core entities - Player, Ball, and supporting types.

Entities are pure data containers. Behavior is implemented in systems.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any

from .vec2 import Vec2


# =============================================================================
# Enums
# =============================================================================

class Team(str, Enum):
    """Which team a player is on."""
    OFFENSE = "offense"
    DEFENSE = "defense"


class Position(str, Enum):
    """Player positions."""
    # Offense
    QB = "QB"
    RB = "RB"
    FB = "FB"
    WR = "WR"
    TE = "TE"
    LT = "LT"
    LG = "LG"
    C = "C"
    RG = "RG"
    RT = "RT"

    # Defense
    DT = "DT"
    DE = "DE"
    NT = "NT"
    MLB = "MLB"
    OLB = "OLB"
    ILB = "ILB"
    CB = "CB"
    FS = "FS"
    SS = "SS"


class BallState(str, Enum):
    """Current state of the football."""
    DEAD = "dead"           # Before snap
    HELD = "held"           # In a player's hands
    IN_FLIGHT = "in_flight" # Thrown/kicked
    LOOSE = "loose"         # Fumble


# =============================================================================
# Attributes
# =============================================================================

@dataclass
class PlayerAttributes:
    """Player attributes that affect simulation outcomes.

    All attributes are on a 0-99 scale where:
    - 60-70: Below average
    - 70-80: Average NFL player
    - 80-90: Above average / starter quality
    - 90+: Elite

    These are the simulation-relevant attributes, not full player ratings.
    """
    # Physical
    speed: int = 75             # Top speed
    acceleration: int = 75      # Time to top speed
    agility: int = 75          # Change of direction
    strength: int = 75          # Contact outcomes

    # Mental
    awareness: int = 75         # Reaction time, reads
    vision: int = 75           # Seeing the field (ballcarrier)
    play_recognition: int = 75  # Run/pass read, coverage recognition

    # Position-specific (can be expanded)
    route_running: int = 75     # Route crispness
    catching: int = 75          # Catch probability
    throw_power: int = 75       # Arm strength
    throw_accuracy: int = 75    # Accuracy
    tackling: int = 75          # Tackle success rate
    man_coverage: int = 75      # Man-to-man coverage ability
    zone_coverage: int = 75     # Zone coverage ability
    press: int = 75             # Press coverage at LOS
    block_power: int = 75       # Blocking strength
    block_finesse: int = 75     # Blocking technique
    pass_rush: int = 75         # Rush moves
    elusiveness: int = 75       # Avoiding tackles

    def get(self, attr_name: str, default: int = 75) -> int:
        """Get attribute by name."""
        return getattr(self, attr_name, default)


# =============================================================================
# Player
# =============================================================================

@dataclass
class Player:
    """A player entity in the simulation.

    Players are pure data. All behavior is implemented in systems.

    Attributes:
        id: Unique identifier
        name: Display name
        team: Offense or defense
        position: Player's position
        position_slot: Position in formation (X, Y, Z, etc.)

        # Physical state
        pos: Current position on field
        velocity: Current velocity vector
        facing: Direction player is facing

        # Game state
        has_ball: Whether player currently has the ball
        is_down: Player is down (play over for them)
        is_engaged: In a blocking engagement

        # Assignment state
        assignment: Current assignment description
        target_id: ID of player they're assigned to (man coverage, blocking)

        # Attributes
        attributes: Player attribute ratings

        # Physics (set by BodyModel)
        collision_radius: Size for collision detection
        tackle_reach: How far they can reach to tackle
    """
    # Identity
    id: str
    name: str = ""
    team: Team = Team.OFFENSE
    position: Position = Position.WR
    position_slot: str = ""  # e.g., "X", "Y", "Z", "RB1", etc.

    # Physical state
    pos: Vec2 = field(default_factory=Vec2.zero)
    velocity: Vec2 = field(default_factory=Vec2.zero)
    facing: Vec2 = field(default_factory=Vec2.up)

    # Derived state
    current_speed: float = 0.0

    # Game state
    has_ball: bool = False
    is_down: bool = False
    is_engaged: bool = False

    # Assignment
    assignment: str = ""
    target_id: Optional[str] = None

    # Route state (for receivers)
    route_phase: str = ""
    current_waypoint: int = 0
    read_order: int = 1  # QB read progression (1 = first read)
    is_hot_route: bool = False  # Quick throw option vs blitz

    # Attributes
    attributes: PlayerAttributes = field(default_factory=PlayerAttributes)

    # Physics (typically set from BodyModel)
    collision_radius: float = 0.3
    tackle_reach: float = 1.2
    weight: float = 200.0
    height: float = 2.0  # yards

    # Debug/logging state
    _last_decision: str = ""
    _last_decision_reason: str = ""

    def __post_init__(self):
        if not self.name:
            self.name = self.id

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def speed(self) -> float:
        """Current speed (magnitude of velocity)."""
        return self.velocity.length()

    @property
    def is_moving(self) -> bool:
        """Whether player is currently moving."""
        return self.velocity.length() > 0.1

    @property
    def direction(self) -> Vec2:
        """Current direction of movement."""
        if self.is_moving:
            return self.velocity.normalized()
        return self.facing

    # =========================================================================
    # Mutation helpers (return new state)
    # =========================================================================

    def with_position(self, pos: Vec2) -> Player:
        """Return copy with new position."""
        new = self._copy()
        new.pos = pos
        return new

    def with_velocity(self, vel: Vec2) -> Player:
        """Return copy with new velocity."""
        new = self._copy()
        new.velocity = vel
        new.current_speed = vel.length()
        return new

    def _copy(self) -> Player:
        """Create a shallow copy."""
        import copy
        return copy.copy(self)

    # =========================================================================
    # Logging / Debug
    # =========================================================================

    def set_decision(self, decision: str, reason: str = "") -> None:
        """Record the last decision made (for logging)."""
        self._last_decision = decision
        self._last_decision_reason = reason

    def format_state(self) -> str:
        """Format current state for logging."""
        lines = [
            f"Player: {self.name} ({self.position.value})",
            f"  Position: {self.pos}",
            f"  Velocity: {self.velocity} (speed: {self.speed:.2f} yds/s)",
            f"  Facing: {self.facing}",
        ]

        if self.has_ball:
            lines.append("  [HAS BALL]")

        if self.is_engaged:
            lines.append("  [ENGAGED]")

        if self.assignment:
            lines.append(f"  Assignment: {self.assignment}")

        if self._last_decision:
            lines.append(f"  Last decision: {self._last_decision}")
            if self._last_decision_reason:
                lines.append(f"    Reason: {self._last_decision_reason}")

        return "\n".join(lines)

    def format_brief(self) -> str:
        """Brief one-line format."""
        status = []
        if self.has_ball:
            status.append("BALL")
        if self.is_engaged:
            status.append("ENG")

        status_str = f" [{','.join(status)}]" if status else ""
        return f"{self.name}({self.position.value}) @ {self.pos}{status_str}"

    def __repr__(self) -> str:
        return f"Player({self.id}, {self.position.value}, pos={self.pos})"


# =============================================================================
# Ball
# =============================================================================

class ThrowType(str, Enum):
    """Type of throw - affects arc and velocity."""
    BULLET = "bullet"  # Fast, flat trajectory - short/intermediate
    TOUCH = "touch"    # Medium arc - intermediate routes, dropping over defenders
    LOB = "lob"        # High arc - back shoulder fades, deep balls


@dataclass
class Ball:
    """The football.

    Tracks ball state, position, and flight information.
    """
    state: BallState = BallState.DEAD
    pos: Vec2 = field(default_factory=Vec2.zero)
    carrier_id: Optional[str] = None

    # Flight info (when IN_FLIGHT)
    flight_origin: Optional[Vec2] = None
    flight_target: Optional[Vec2] = None
    flight_start_time: float = 0.0
    flight_duration: float = 0.0
    intended_receiver_id: Optional[str] = None

    # Enhanced flight physics
    throw_type: ThrowType = ThrowType.BULLET
    peak_height: float = 0.0  # Max height in yards (for arc visualization)
    release_height: float = 2.0  # QB release point ~6 feet

    @property
    def is_held(self) -> bool:
        return self.state == BallState.HELD

    @property
    def is_in_flight(self) -> bool:
        return self.state == BallState.IN_FLIGHT

    @property
    def is_loose(self) -> bool:
        return self.state == BallState.LOOSE

    def height_at_progress(self, progress: float) -> float:
        """Get ball height at given flight progress (0-1).

        Uses parabolic arc: h(t) = 4 * peak * t * (1-t) + base
        This gives a nice symmetric arc peaking at t=0.5
        """
        if progress <= 0 or progress >= 1:
            return self.release_height if progress <= 0 else 1.0  # Catch height ~3 feet

        # Parabolic arc
        arc_height = 4 * self.peak_height * progress * (1 - progress)
        # Interpolate base height from release to catch
        base_height = self.release_height * (1 - progress) + 1.0 * progress
        return base_height + arc_height

    def position_at_time(self, current_time: float) -> Vec2:
        """Get ball position at given time (handles flight interpolation)."""
        if self.state != BallState.IN_FLIGHT:
            return self.pos

        if self.flight_origin is None or self.flight_target is None:
            return self.pos

        elapsed = current_time - self.flight_start_time
        if elapsed >= self.flight_duration:
            return self.flight_target

        progress = elapsed / self.flight_duration if self.flight_duration > 0 else 1.0
        return self.flight_origin.lerp(self.flight_target, progress)

    def full_position_at_time(self, current_time: float) -> tuple[Vec2, float]:
        """Get ball position and height at given time.

        Returns:
            (xy_position, height_in_yards)
        """
        xy = self.position_at_time(current_time)

        if self.state != BallState.IN_FLIGHT:
            return xy, self.release_height if self.carrier_id else 0.5

        elapsed = current_time - self.flight_start_time
        progress = elapsed / self.flight_duration if self.flight_duration > 0 else 1.0
        progress = max(0, min(1, progress))

        return xy, self.height_at_progress(progress)

    def has_arrived(self, current_time: float) -> bool:
        """Check if ball has reached its target."""
        if self.state != BallState.IN_FLIGHT:
            return False
        return (current_time - self.flight_start_time) >= self.flight_duration

    def format_state(self) -> str:
        """Format ball state for logging."""
        lines = [f"Ball: {self.state.value}"]

        if self.carrier_id:
            lines.append(f"  Carrier: {self.carrier_id}")
        else:
            lines.append(f"  Position: {self.pos}")

        if self.state == BallState.IN_FLIGHT:
            lines.append(f"  Flight: {self.flight_origin} → {self.flight_target}")
            lines.append(f"  Duration: {self.flight_duration:.2f}s")
            if self.intended_receiver_id:
                lines.append(f"  Target: {self.intended_receiver_id}")

        return "\n".join(lines)

    def __repr__(self) -> str:
        if self.carrier_id:
            return f"Ball(held by {self.carrier_id})"
        return f"Ball({self.state.value} @ {self.pos})"
