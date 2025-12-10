"""Route running and coverage simulation sandbox.

1v1 WR vs DB simulation with:
- Route waypoint system
- Release contest (press coverage)
- Separation tracking
- Man and zone coverage
"""

from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

# Use shared Vec2 implementation
from .shared import Vec2


# =============================================================================
# Enums
# =============================================================================

class RouteType(str, Enum):
    """Standard route tree."""
    FLAT = "flat"           # 0 - Quick out to flat
    SLANT = "slant"         # 1 - Inside angle
    COMEBACK = "comeback"   # 2 - Vertical + back
    CURL = "curl"           # 3 - Hook/sit
    OUT = "out"             # 4 - Outside cut
    IN = "in"               # 5 - Dig/cross
    CORNER = "corner"       # 6 - Outside fade
    POST = "post"           # 7 - Inside deep
    GO = "go"               # 8 - Vertical streak
    HITCH = "hitch"         # 9 - Quick hook


class CoverageType(str, Enum):
    """DB coverage technique."""
    MAN_PRESS = "man_press"
    MAN_OFF = "man_off"
    ZONE_FLAT = "zone_flat"
    ZONE_DEEP = "zone_deep"


class ReleaseResult(str, Enum):
    """Outcome of press release contest."""
    CLEAN = "clean"           # WR wins cleanly
    SLIGHT_WIN = "slight_win" # WR wins with minor delay
    CONTESTED = "contested"   # Even battle
    REROUTED = "rerouted"     # DB wins, WR pushed off
    JAMMED = "jammed"         # DB dominates


class ReleaseTechnique(str, Enum):
    """WR release moves vs press."""
    SPEED = "speed"       # Burst past
    SWIM = "swim"         # Arm over
    SWIPE = "swipe"       # Knock hands
    HESITATION = "hes"    # Fake direction


class JamTechnique(str, Enum):
    """DB jam techniques at LOS."""
    PUNCH = "punch"       # Quick hands to chest
    MIRROR = "mirror"     # Shadow movement
    FUNNEL = "funnel"     # Force direction


class RoutePhase(str, Enum):
    """Current phase of route."""
    PRE_SNAP = "pre_snap"
    RELEASE = "release"
    STEM = "stem"
    BREAK = "break"
    POST_BREAK = "post_break"
    COMPLETE = "complete"


class Animation(str, Enum):
    """Animation states for WR and DB."""
    # Pre-snap
    STANCE = "stance"

    # WR Release
    RELEASE_BURST = "release_burst"
    RELEASE_SWIM = "release_swim"
    RELEASE_SWIPE = "release_swipe"
    RELEASE_JAMMED = "release_jammed"

    # WR Route
    ROUTE_STEM = "route_stem"
    ROUTE_BREAK = "route_break"
    ROUTE_RUN = "route_run"

    # DB Press
    PRESS_STANCE = "press_stance"
    PRESS_JAM = "press_jam"
    PRESS_RECOVER = "press_recover"
    PRESS_BEAT = "press_beat"

    # DB Coverage
    BACKPEDAL = "backpedal"
    FLIP_HIPS = "flip_hips"
    TRAIL = "trail"
    CLOSING = "closing"
    ZONE_READ = "zone_read"


# =============================================================================
# Dataclasses
# =============================================================================

@dataclass
class RouteWaypoint:
    """A point along a route with timing."""
    position: Vec2
    arrival_tick: int
    is_break: bool = False  # Sharp cut point

    def to_dict(self) -> dict:
        return {
            "position": self.position.to_dict(),
            "arrival_tick": self.arrival_tick,
            "is_break": self.is_break,
        }


@dataclass
class ReceiverAttributes:
    """WR attributes affecting route running."""
    speed: int = 85
    acceleration: int = 85
    route_running: int = 85
    release: int = 80

    def to_dict(self) -> dict:
        return {
            "speed": self.speed,
            "acceleration": self.acceleration,
            "route_running": self.route_running,
            "release": self.release,
        }


@dataclass
class DBAttributes:
    """DB attributes affecting coverage."""
    speed: int = 88
    acceleration: int = 86
    man_coverage: int = 85
    zone_coverage: int = 80
    play_recognition: int = 75
    press: int = 80

    def to_dict(self) -> dict:
        return {
            "speed": self.speed,
            "acceleration": self.acceleration,
            "man_coverage": self.man_coverage,
            "zone_coverage": self.zone_coverage,
            "play_recognition": self.play_recognition,
            "press": self.press,
        }


@dataclass
class Receiver:
    """Wide receiver running a route."""
    id: str
    position: Vec2
    route: list[RouteWaypoint]
    attributes: ReceiverAttributes = field(default_factory=ReceiverAttributes)

    # Route state
    current_waypoint_idx: int = 0
    route_phase: RoutePhase = RoutePhase.PRE_SNAP
    release_result: Optional[ReleaseResult] = None
    release_delay: int = 0  # Ticks delayed by press

    # Physics state - acceleration model
    velocity: Vec2 = field(default_factory=lambda: Vec2(0, 0))
    current_speed: float = 0.0

    # Visual state
    animation: Animation = Animation.STANCE
    facing: Vec2 = field(default_factory=lambda: Vec2(0, 1))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "position": self.position.to_dict(),
            "route": [w.to_dict() for w in self.route],
            "attributes": self.attributes.to_dict(),
            "current_waypoint_idx": self.current_waypoint_idx,
            "route_phase": self.route_phase.value,
            "release_result": self.release_result.value if self.release_result else None,
            "release_delay": self.release_delay,
            "animation": self.animation.value,
            "facing": self.facing.to_dict(),
        }


@dataclass
class DefensiveBack:
    """Cornerback or safety in coverage."""
    id: str
    position: Vec2
    coverage_type: CoverageType
    attributes: DBAttributes = field(default_factory=DBAttributes)

    # Coverage state
    target_position: Optional[Vec2] = None  # Where DB is trying to go
    zone_center: Optional[Vec2] = None      # Center of zone assignment
    zone_radius: float = 8.0                # Zone coverage radius
    reaction_delay: int = 0                 # Ticks until reacting to break
    has_reacted_to_break: bool = False

    # Physics state - acceleration model
    velocity: Vec2 = field(default_factory=lambda: Vec2(0, 0))
    current_speed: float = 0.0

    # Visual state
    animation: Animation = Animation.STANCE
    facing: Vec2 = field(default_factory=lambda: Vec2(0, -1))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "position": self.position.to_dict(),
            "coverage_type": self.coverage_type.value,
            "attributes": self.attributes.to_dict(),
            "zone_center": self.zone_center.to_dict() if self.zone_center else None,
            "zone_radius": self.zone_radius,
            "reaction_delay": self.reaction_delay,
            "has_reacted_to_break": self.has_reacted_to_break,
            "animation": self.animation.value,
            "facing": self.facing.to_dict(),
        }


@dataclass
class RouteSimState:
    """Complete state of route simulation."""
    receiver: Receiver
    defender: DefensiveBack
    route_type: RouteType

    # Metrics
    separation: float = 0.0
    max_separation: float = 0.0
    separation_at_break: float = 0.0

    # Simulation state
    tick: int = 0
    is_complete: bool = False
    result: str = "in_progress"  # "open", "contested", "covered"

    def to_dict(self) -> dict:
        return {
            "receiver": self.receiver.to_dict(),
            "defender": self.defender.to_dict(),
            "route_type": self.route_type.value,
            "separation": round(self.separation, 2),
            "max_separation": round(self.max_separation, 2),
            "separation_at_break": round(self.separation_at_break, 2),
            "tick": self.tick,
            "is_complete": self.is_complete,
            "result": self.result,
        }


# =============================================================================
# Route Factory Functions
# =============================================================================

def create_out_route(depth: int = 10) -> list[RouteWaypoint]:
    """Standard out route - vertical stem then break outside."""
    return [
        RouteWaypoint(Vec2(0, 2), arrival_tick=4, is_break=False),      # Release
        RouteWaypoint(Vec2(0, depth), arrival_tick=14, is_break=False), # Stem
        RouteWaypoint(Vec2(-5, depth), arrival_tick=20, is_break=True), # Break
        RouteWaypoint(Vec2(-8, depth), arrival_tick=26, is_break=False), # Finish
    ]


def create_slant_route() -> list[RouteWaypoint]:
    """Quick slant - release then cut inside at shallow angle."""
    return [
        RouteWaypoint(Vec2(0, 2), arrival_tick=3, is_break=False),     # Release
        RouteWaypoint(Vec2(2, 4), arrival_tick=7, is_break=True),      # Break inside (3-4 yards)
        RouteWaypoint(Vec2(5, 6), arrival_tick=12, is_break=False),    # Continue shallow
        RouteWaypoint(Vec2(8, 8), arrival_tick=18, is_break=False),    # Finish (~8 yards)
    ]


def create_go_route() -> list[RouteWaypoint]:
    """Vertical streak - straight down field."""
    return [
        RouteWaypoint(Vec2(0, 3), arrival_tick=5, is_break=False),     # Release
        RouteWaypoint(Vec2(0, 10), arrival_tick=12, is_break=False),   # Stem
        RouteWaypoint(Vec2(0, 20), arrival_tick=22, is_break=False),   # Deep
        RouteWaypoint(Vec2(0, 30), arrival_tick=32, is_break=False),   # Finish
    ]


def create_curl_route(depth: int = 12) -> list[RouteWaypoint]:
    """Curl/hook - vertical stem then sit."""
    return [
        RouteWaypoint(Vec2(0, 2), arrival_tick=4, is_break=False),           # Release
        RouteWaypoint(Vec2(0, depth), arrival_tick=14, is_break=False),      # Stem
        RouteWaypoint(Vec2(0, depth - 1), arrival_tick=18, is_break=True),   # Turn back
        RouteWaypoint(Vec2(0, depth - 2), arrival_tick=24, is_break=False),  # Settle
    ]


def create_in_route(depth: int = 10) -> list[RouteWaypoint]:
    """In/dig route - vertical stem then break inside."""
    return [
        RouteWaypoint(Vec2(0, 2), arrival_tick=4, is_break=False),      # Release
        RouteWaypoint(Vec2(0, depth), arrival_tick=14, is_break=False), # Stem
        RouteWaypoint(Vec2(5, depth), arrival_tick=20, is_break=True),  # Break inside
        RouteWaypoint(Vec2(12, depth), arrival_tick=28, is_break=False), # Finish
    ]


def create_corner_route() -> list[RouteWaypoint]:
    """Corner route - stem then break to corner of end zone."""
    return [
        RouteWaypoint(Vec2(0, 3), arrival_tick=5, is_break=False),      # Release
        RouteWaypoint(Vec2(0, 12), arrival_tick=14, is_break=False),    # Stem
        RouteWaypoint(Vec2(-6, 20), arrival_tick=24, is_break=True),    # Break to corner
        RouteWaypoint(Vec2(-10, 28), arrival_tick=32, is_break=False),  # Finish
    ]


def create_post_route() -> list[RouteWaypoint]:
    """Post route - stem then break inside toward goal post."""
    return [
        RouteWaypoint(Vec2(0, 3), arrival_tick=5, is_break=False),      # Release
        RouteWaypoint(Vec2(0, 12), arrival_tick=14, is_break=False),    # Stem
        RouteWaypoint(Vec2(4, 20), arrival_tick=24, is_break=True),     # Break to post
        RouteWaypoint(Vec2(8, 28), arrival_tick=32, is_break=False),    # Finish
    ]


def create_hitch_route() -> list[RouteWaypoint]:
    """Quick hitch - short route with immediate turn."""
    return [
        RouteWaypoint(Vec2(0, 2), arrival_tick=3, is_break=False),     # Release
        RouteWaypoint(Vec2(0, 5), arrival_tick=8, is_break=True),      # Turn
        RouteWaypoint(Vec2(0, 4), arrival_tick=12, is_break=False),    # Settle
    ]


def create_flat_route() -> list[RouteWaypoint]:
    """Flat route - quick out to flat area."""
    return [
        RouteWaypoint(Vec2(0, 1), arrival_tick=2, is_break=False),     # Release
        RouteWaypoint(Vec2(-3, 1), arrival_tick=6, is_break=True),     # Break to flat
        RouteWaypoint(Vec2(-8, 2), arrival_tick=14, is_break=False),   # Run flat
    ]


def create_comeback_route(depth: int = 15) -> list[RouteWaypoint]:
    """Comeback route - deep stem then come back to sideline."""
    return [
        RouteWaypoint(Vec2(0, 3), arrival_tick=5, is_break=False),          # Release
        RouteWaypoint(Vec2(0, depth), arrival_tick=18, is_break=False),     # Deep stem
        RouteWaypoint(Vec2(-3, depth - 3), arrival_tick=24, is_break=True), # Comeback
        RouteWaypoint(Vec2(-5, depth - 4), arrival_tick=30, is_break=False),# Finish
    ]


def create_route(route_type: RouteType) -> list[RouteWaypoint]:
    """Factory function to create routes by type."""
    factories = {
        RouteType.FLAT: create_flat_route,
        RouteType.SLANT: create_slant_route,
        RouteType.COMEBACK: create_comeback_route,
        RouteType.CURL: create_curl_route,
        RouteType.OUT: create_out_route,
        RouteType.IN: create_in_route,
        RouteType.CORNER: create_corner_route,
        RouteType.POST: create_post_route,
        RouteType.GO: create_go_route,
        RouteType.HITCH: create_hitch_route,
    }
    return factories[route_type]()


# =============================================================================
# Route Simulator
# =============================================================================

# Constants
MAX_TICKS = 50             # Enough time for deep routes
TICK_MS = 100

# Movement speeds (yards per tick)
# Base speeds are equal - attributes determine who's faster
WR_BASE_SPEED = 0.45       # Base running speed
DB_BASE_SPEED = 0.45       # Same base
DB_REACTION_PENALTY = 0.85 # DB slower when reacting to break (not trailing)
PRESS_SLOWDOWN = 0.3       # Speed reduction during release

# Release contest thresholds
RELEASE_CLEAN_THRESHOLD = 15
RELEASE_WIN_THRESHOLD = 5
RELEASE_LOSS_THRESHOLD = -5
RELEASE_JAMMED_THRESHOLD = -15

# Separation thresholds for results
OPEN_SEPARATION = 3.0      # 3+ yards = open
CONTESTED_SEPARATION = 1.0 # 1-3 yards = contested


class RouteSimulator:
    """Simulates 1v1 WR vs DB route battle."""

    def __init__(
        self,
        route_type: RouteType = RouteType.OUT,
        coverage_type: CoverageType = CoverageType.MAN_OFF,
        wr_attributes: Optional[ReceiverAttributes] = None,
        db_attributes: Optional[DBAttributes] = None,
    ):
        self.route_type = route_type
        self.coverage_type = coverage_type
        self.wr_attributes = wr_attributes or ReceiverAttributes()
        self.db_attributes = db_attributes or DBAttributes()
        self.state: Optional[RouteSimState] = None

    def setup(self) -> None:
        """Initialize simulation with receiver and defender."""
        # Create route
        route = create_route(self.route_type)

        # WR starts at LOS
        wr = Receiver(
            id=str(uuid.uuid4()),
            position=Vec2(0, 0),
            route=route,
            attributes=self.wr_attributes,
        )

        # DB position depends on coverage
        db_pos = self._get_db_start_position()
        zone_center = self._get_zone_center() if self.coverage_type in (
            CoverageType.ZONE_FLAT, CoverageType.ZONE_DEEP
        ) else None

        db = DefensiveBack(
            id=str(uuid.uuid4()),
            position=db_pos,
            coverage_type=self.coverage_type,
            attributes=self.db_attributes,
            zone_center=zone_center,
        )

        self.state = RouteSimState(
            receiver=wr,
            defender=db,
            route_type=self.route_type,
        )

    def _get_db_start_position(self) -> Vec2:
        """Get DB starting position based on coverage."""
        if self.coverage_type == CoverageType.MAN_PRESS:
            return Vec2(0, 1)  # At LOS, 1 yard off WR
        elif self.coverage_type == CoverageType.MAN_OFF:
            return Vec2(0, 6)  # 6 yards off
        elif self.coverage_type == CoverageType.ZONE_FLAT:
            return Vec2(-3, 5)  # Offset toward flat
        elif self.coverage_type == CoverageType.ZONE_DEEP:
            return Vec2(0, 10)  # Deep third
        return Vec2(0, 5)

    def _get_zone_center(self) -> Vec2:
        """Get zone center for zone coverage."""
        if self.coverage_type == CoverageType.ZONE_FLAT:
            return Vec2(-5, 5)  # Flat zone
        elif self.coverage_type == CoverageType.ZONE_DEEP:
            return Vec2(0, 15)  # Deep third
        return Vec2(0, 10)

    def reset(self) -> None:
        """Reset simulation to initial state."""
        self.setup()

    def tick(self) -> RouteSimState:
        """Advance simulation by one tick."""
        if not self.state or self.state.is_complete:
            return self.state

        self.state.tick += 1
        wr = self.state.receiver
        db = self.state.defender

        # Phase transitions
        if self.state.tick == 1:
            wr.route_phase = RoutePhase.RELEASE
            if self.coverage_type == CoverageType.MAN_PRESS:
                self._resolve_release()

        # Process based on phase
        if wr.route_phase == RoutePhase.RELEASE:
            self._process_release()
        else:
            self._process_route()

        # DB reacts
        self._process_db_coverage()

        # Update separation
        self._update_separation()

        # Check completion
        self._check_completion()

        return self.state

    def _resolve_release(self) -> None:
        """Resolve press release contest at snap."""
        wr = self.state.receiver
        db = self.state.defender

        # Calculate scores
        wr_score = (
            wr.attributes.release * 0.5 +
            wr.attributes.speed * 0.3 +
            wr.attributes.acceleration * 0.2
        )
        db_score = (
            db.attributes.press * 0.6 +
            db.attributes.speed * 0.2 +
            db.attributes.man_coverage * 0.2
        )

        margin = wr_score - db_score + random.gauss(0, 8)

        if margin > RELEASE_CLEAN_THRESHOLD:
            wr.release_result = ReleaseResult.CLEAN
            wr.release_delay = 0
            db.animation = Animation.PRESS_BEAT
        elif margin > RELEASE_WIN_THRESHOLD:
            wr.release_result = ReleaseResult.SLIGHT_WIN
            wr.release_delay = 1
        elif margin > RELEASE_LOSS_THRESHOLD:
            wr.release_result = ReleaseResult.CONTESTED
            wr.release_delay = 2
        elif margin > RELEASE_JAMMED_THRESHOLD:
            wr.release_result = ReleaseResult.REROUTED
            wr.release_delay = 3
        else:
            wr.release_result = ReleaseResult.JAMMED
            wr.release_delay = 4
            wr.animation = Animation.RELEASE_JAMMED
            db.animation = Animation.PRESS_JAM

    def _process_release(self) -> None:
        """Handle release phase movement."""
        wr = self.state.receiver

        # For non-press coverage, release is quick
        if self.coverage_type != CoverageType.MAN_PRESS:
            if self.state.tick >= 2:
                wr.route_phase = RoutePhase.STEM
                wr.animation = Animation.ROUTE_STEM
            return

        # Press: check if release delay is over
        release_complete_tick = 1 + wr.release_delay
        if self.state.tick >= release_complete_tick:
            wr.route_phase = RoutePhase.STEM
            wr.animation = Animation.ROUTE_STEM
            self.state.defender.animation = Animation.TRAIL
        else:
            # Still in release battle
            wr.animation = Animation.RELEASE_BURST

    def _process_route(self) -> None:
        """Move WR along route waypoints with acceleration and COD physics."""
        wr = self.state.receiver

        if wr.current_waypoint_idx >= len(wr.route):
            wr.route_phase = RoutePhase.COMPLETE
            return

        waypoint = wr.route[wr.current_waypoint_idx]

        # Adjust for release delay
        adjusted_tick = self.state.tick - wr.release_delay

        # Check for break point
        if waypoint.is_break and not wr.route_phase == RoutePhase.BREAK:
            if adjusted_tick >= waypoint.arrival_tick - 2:
                wr.route_phase = RoutePhase.BREAK
                wr.animation = Animation.ROUTE_BREAK
                self._trigger_db_break_reaction()

        # Calculate direction to target
        target = waypoint.position
        desired_direction = (target - wr.position).normalized()

        # Calculate max speed based on speed attribute (exponential)
        max_speed = WR_BASE_SPEED * (wr.attributes.speed / 85) ** 2

        # Calculate acceleration rate based on acceleration attribute
        accel_rate = 0.08 * (wr.attributes.acceleration / 85) ** 1.5

        # Calculate change of direction penalty
        cod_speed_loss = 0.0
        if wr.current_speed > 0.05:
            current_direction = wr.velocity.normalized()
            # Dot product: 1 = same direction, 0 = perpendicular, -1 = opposite
            dot = current_direction.dot(desired_direction)
            dot = max(-1.0, min(1.0, dot))  # Clamp for numerical stability

            # Angle between directions (0 = same, PI = opposite)
            angle = math.acos(dot)

            # Speed loss based on angle
            # Route running skill reduces speed loss on cuts
            route_skill_factor = (wr.attributes.route_running / 85) ** 1.5

            # At 90 degrees (PI/2), lose significant speed
            # At 180 degrees (PI), lose almost all speed
            # Better route runners retain more speed through cuts
            base_loss = (angle / math.pi)  # 0 to 1
            cod_speed_loss = base_loss * (1.0 - route_skill_factor * 0.4)

            # Apply speed loss from direction change
            wr.current_speed *= (1.0 - cod_speed_loss)

        # Accelerate toward max speed
        if wr.current_speed < max_speed:
            wr.current_speed = min(max_speed, wr.current_speed + accel_rate)

        # During break, cap speed (plant and cut)
        if wr.route_phase == RoutePhase.BREAK:
            break_speed_cap = max_speed * 0.7 * (wr.attributes.route_running / 85)
            wr.current_speed = min(wr.current_speed, break_speed_cap)

        # Update velocity and position
        wr.velocity = desired_direction * wr.current_speed
        wr.position = wr.position + wr.velocity
        wr.facing = desired_direction

        # Check if reached waypoint
        if wr.position.distance_to(target) < 0.5:
            wr.current_waypoint_idx += 1
            if wr.route_phase == RoutePhase.BREAK:
                wr.route_phase = RoutePhase.POST_BREAK
                wr.animation = Animation.ROUTE_RUN

    def _trigger_db_break_reaction(self) -> None:
        """DB needs to react to WR break."""
        db = self.state.defender

        if db.has_reacted_to_break:
            return

        # Calculate reaction delay based on play recognition
        base_delay = 3
        rec_bonus = db.attributes.play_recognition / 40  # 0-2.5 tick bonus
        db.reaction_delay = max(1, int(base_delay - rec_bonus))

        # Record separation at break
        self.state.separation_at_break = self.state.separation

    def _process_db_coverage(self) -> None:
        """Handle DB movement and coverage."""
        db = self.state.defender
        wr = self.state.receiver

        if self.coverage_type in (CoverageType.MAN_PRESS, CoverageType.MAN_OFF):
            self._process_man_coverage()
        else:
            self._process_zone_coverage()

    def _process_man_coverage(self) -> None:
        """DB follows receiver in man coverage with acceleration and COD physics."""
        db = self.state.defender
        wr = self.state.receiver

        # During release, DB may be at LOS
        if wr.route_phase == RoutePhase.RELEASE:
            if self.coverage_type == CoverageType.MAN_PRESS:
                return  # Stay at LOS during jam

        # Target is WR position with slight lag
        target = wr.position

        # Track if this is the first tick of flip_hips (for one-time penalty)
        just_started_flip = False

        # If break happened and DB hasn't reacted yet
        if wr.route_phase in (RoutePhase.BREAK, RoutePhase.POST_BREAK):
            if not db.has_reacted_to_break:
                db.reaction_delay -= 1
                if db.reaction_delay <= 0:
                    db.has_reacted_to_break = True
                    db.animation = Animation.FLIP_HIPS
                    just_started_flip = True
                else:
                    # Keep moving in previous direction (not toward WR)
                    target = Vec2(db.position.x, db.position.y + 0.5)

        # Calculate desired direction to target
        desired_direction = (target - db.position).normalized()

        # Calculate max speed based on attributes - EXPONENTIAL scaling
        # 55 spd = 0.42x, 85 spd = 1.0x, 99 spd = 1.36x
        speed_factor = (db.attributes.speed / 85) ** 2
        coverage_factor = (db.attributes.man_coverage / 85) ** 1.5
        max_speed = DB_BASE_SPEED * speed_factor * coverage_factor

        # Calculate acceleration rate based on acceleration attribute
        accel_rate = 0.07 * (db.attributes.acceleration / 85) ** 1.5

        # One-time speed penalty when first flipping hips
        if just_started_flip:
            # Lose significant speed when planting to change direction
            # Better man coverage = less speed loss
            flip_penalty = 0.4 + (db.attributes.man_coverage / 100) * 0.2  # 0.4-0.6 retention
            db.current_speed *= flip_penalty

        # Calculate change of direction penalty (only when moving)
        # Cap COD loss so DB doesn't completely stop
        if db.current_speed > 0.1 and db.animation != Animation.FLIP_HIPS:
            current_direction = db.velocity.normalized()
            dot = current_direction.dot(desired_direction)
            dot = max(-1.0, min(1.0, dot))

            angle = math.acos(dot)

            # Only apply COD for significant direction changes (> 30 degrees)
            if angle > 0.5:  # ~30 degrees
                coverage_skill_factor = (db.attributes.man_coverage / 85) ** 1.5
                base_loss = (angle / math.pi)
                cod_speed_loss = base_loss * (1.0 - coverage_skill_factor * 0.35)
                # Cap max speed loss per tick at 40%
                cod_speed_loss = min(cod_speed_loss, 0.4)
                db.current_speed *= (1.0 - cod_speed_loss)

        # Accelerate toward max speed
        if db.current_speed < max_speed:
            db.current_speed = min(max_speed, db.current_speed + accel_rate)

        # During flip_hips, cap speed but don't multiply down each tick
        if db.animation == Animation.FLIP_HIPS:
            # Speed cap during hip flip - can accelerate but limited
            flip_max = max_speed * 0.6
            db.current_speed = min(db.current_speed, flip_max)

        # Penalty if DB hasn't reacted to break yet (still moving wrong way)
        if wr.route_phase in (RoutePhase.BREAK, RoutePhase.POST_BREAK) and not db.has_reacted_to_break:
            db.current_speed = min(db.current_speed, max_speed * DB_REACTION_PENALTY)

        # Update velocity and position
        db.velocity = desired_direction * db.current_speed
        db.position = db.position + db.velocity
        db.facing = desired_direction

        # Determine if trailing (WR is ahead of DB)
        is_trailing = db.position.y < wr.position.y

        # Update animation - exit flip_hips after a couple ticks
        if db.animation == Animation.FLIP_HIPS:
            # Stay in flip_hips briefly, then transition to trail/closing
            if db.has_reacted_to_break and db.reaction_delay <= -2:
                db.animation = Animation.TRAIL if is_trailing else Animation.CLOSING
            db.reaction_delay -= 1  # Use negative values to track flip duration
        elif db.animation not in (Animation.PRESS_JAM, Animation.PRESS_BEAT):
            if is_trailing:
                db.animation = Animation.TRAIL
            else:
                db.animation = Animation.CLOSING

    def _process_zone_coverage(self) -> None:
        """DB covers zone area with acceleration and COD physics."""
        db = self.state.defender
        wr = self.state.receiver

        if not db.zone_center:
            return

        # Check if WR is in or approaching zone
        wr_to_zone = wr.position.distance_to(db.zone_center)

        if wr_to_zone < db.zone_radius:
            # WR in zone - break on ball/receiver
            target = wr.position
            db.animation = Animation.CLOSING
        else:
            # Stay in zone
            target = db.zone_center
            db.animation = Animation.ZONE_READ

        # Calculate desired direction to target
        desired_direction = (target - db.position).normalized()

        # Calculate max speed based on attributes - EXPONENTIAL scaling
        speed_factor = (db.attributes.speed / 85) ** 2
        zone_factor = (db.attributes.zone_coverage / 85) ** 1.5
        max_speed = DB_BASE_SPEED * speed_factor * zone_factor * 0.85  # Zone is more conservative

        # Calculate acceleration rate based on acceleration attribute
        accel_rate = 0.07 * (db.attributes.acceleration / 85) ** 1.5

        # Calculate change of direction penalty
        cod_speed_loss = 0.0
        if db.current_speed > 0.05:
            current_direction = db.velocity.normalized()
            dot = current_direction.dot(desired_direction)
            dot = max(-1.0, min(1.0, dot))  # Clamp for numerical stability

            # Angle between directions (0 = same, PI = opposite)
            angle = math.acos(dot)

            # Zone coverage skill affects how well they change direction in zone
            zone_skill_factor = (db.attributes.zone_coverage / 85) ** 1.5

            # Base speed loss from direction change
            base_loss = (angle / math.pi)  # 0 to 1
            cod_speed_loss = base_loss * (1.0 - zone_skill_factor * 0.3)

            # Apply speed loss from direction change
            db.current_speed *= (1.0 - cod_speed_loss)

        # Accelerate toward max speed
        if db.current_speed < max_speed:
            db.current_speed = min(max_speed, db.current_speed + accel_rate)

        # Slow down when already in position (zone read)
        if db.position.distance_to(target) < 1:
            db.current_speed *= 0.5

        # Update velocity and position
        db.velocity = desired_direction * db.current_speed
        db.position = db.position + db.velocity
        db.facing = desired_direction

    def _update_separation(self) -> None:
        """Calculate current separation between WR and DB."""
        separation = self.state.receiver.position.distance_to(
            self.state.defender.position
        )
        self.state.separation = separation

        # Track max separation
        if separation > self.state.max_separation:
            self.state.max_separation = separation

    def _check_completion(self) -> None:
        """Check if simulation is complete."""
        wr = self.state.receiver

        # Complete if route is done
        if wr.route_phase == RoutePhase.COMPLETE:
            self._determine_result()
            return

        # Complete if max ticks reached
        if self.state.tick >= MAX_TICKS:
            self._determine_result()
            return

        # Complete if WR reached final waypoint
        if wr.current_waypoint_idx >= len(wr.route):
            self._determine_result()

    def _determine_result(self) -> None:
        """Determine final result based on separation."""
        self.state.is_complete = True

        max_sep = self.state.max_separation
        final_sep = self.state.separation

        # Result considers both max separation (throw window) and final separation (DB recovery)
        # If DB has completely recovered (< 1 yard), can't be "open" regardless of max
        if final_sep < CONTESTED_SEPARATION:
            # DB recovered - at best contested if there was a window
            if max_sep >= OPEN_SEPARATION:
                self.state.result = "contested"  # Had a window but DB closed
            else:
                self.state.result = "covered"
        elif final_sep < OPEN_SEPARATION:
            # Currently contested - was there ever an open window?
            if max_sep >= OPEN_SEPARATION:
                self.state.result = "contested"  # Window closed
            else:
                self.state.result = "contested"
        else:
            # Currently open (3+ yards separation)
            self.state.result = "open"

    def run_full(self) -> list[dict]:
        """Run complete simulation and return all states."""
        if not self.state:
            self.setup()

        states = [self.state.to_dict()]

        while not self.state.is_complete and self.state.tick < MAX_TICKS:
            self.tick()
            states.append(self.state.to_dict())

        return states
