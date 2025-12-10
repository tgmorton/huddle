"""Team route running simulation - multiple WRs vs DBs.

Supports:
- Multiple receivers (3-5 WR formations)
- Coverage schemes (Cover 0, 1, 2, 3, 4, Man)
- Route concepts (4 verts, mesh, smash, flood, etc.)
- Zone and man coverage interactions
"""

from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

# Use shared Vec2 directly
from .shared import Vec2

from .route_sim import (
    RouteWaypoint,
    RouteType,
    RoutePhase,
    Animation,
    ReceiverAttributes,
    DBAttributes,
    ReleaseResult,
    create_route,
    create_out_route,
    create_slant_route,
    create_go_route,
    create_curl_route,
    create_in_route,
    create_corner_route,
    create_post_route,
    create_hitch_route,
    create_flat_route,
    create_comeback_route,
)


# =============================================================================
# Enums
# =============================================================================

class Formation(str, Enum):
    """Offensive formations."""
    TRIPS_RIGHT = "trips_right"      # 3 WR to right
    TRIPS_LEFT = "trips_left"        # 3 WR to left
    SPREAD = "spread"                # 2x2 with slot
    EMPTY = "empty"                  # 5 WR, no RB
    DOUBLES = "doubles"              # 2 WR each side


class CoverageScheme(str, Enum):
    """Defensive coverage schemes."""
    COVER_0 = "cover_0"    # Pure man, 0 deep safeties (blitz)
    COVER_1 = "cover_1"    # Man with single high safety
    COVER_2 = "cover_2"    # 2 deep safeties, 5 under zones
    COVER_3 = "cover_3"    # 3 deep zones, 4 under
    COVER_4 = "cover_4"    # 4 deep quarters
    COVER_2_MAN = "cover_2_man"  # 2 deep safeties, man under


class RouteConcept(str, Enum):
    """Pre-designed route combinations."""
    FOUR_VERTS = "four_verts"     # All go routes
    MESH = "mesh"                  # Crossing routes
    SMASH = "smash"               # Corner + hitch
    FLOOD = "flood"               # 3 levels to one side
    LEVELS = "levels"             # In routes at different depths
    SLANTS = "slants"             # All slants
    CURLS = "curls"               # Curl/flat combo
    CUSTOM = "custom"             # User-defined routes


class ReceiverPosition(str, Enum):
    """Receiver alignment positions."""
    X = "x"           # Split end (usually left)
    Z = "z"           # Flanker (usually right)
    SLOT_L = "slot_l" # Left slot
    SLOT_R = "slot_r" # Right slot
    TE = "te"         # Tight end


class DefenderPosition(str, Enum):
    """Defensive back positions."""
    CB1 = "cb1"       # Corner 1 (usually vs X)
    CB2 = "cb2"       # Corner 2 (usually vs Z)
    NICKEL = "nickel" # Slot corner
    FS = "fs"         # Free safety
    SS = "ss"         # Strong safety


class ZoneType(str, Enum):
    """Zone coverage areas."""
    DEEP_THIRD_L = "deep_third_l"
    DEEP_THIRD_M = "deep_third_m"
    DEEP_THIRD_R = "deep_third_r"
    DEEP_HALF_L = "deep_half_l"
    DEEP_HALF_R = "deep_half_r"
    DEEP_QUARTER_1 = "deep_quarter_1"
    DEEP_QUARTER_2 = "deep_quarter_2"
    DEEP_QUARTER_3 = "deep_quarter_3"
    DEEP_QUARTER_4 = "deep_quarter_4"
    FLAT_L = "flat_l"
    FLAT_R = "flat_r"
    HOOK_L = "hook_l"
    HOOK_R = "hook_r"
    CURL_FLAT_L = "curl_flat_l"
    CURL_FLAT_R = "curl_flat_r"
    MIDDLE = "middle"


# =============================================================================
# Zone Definitions - boundaries define responsibility areas
# =============================================================================

@dataclass
class ZoneBoundary:
    """Zone boundary definition - defenders cover this area."""
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    # Anchor point - where to position when no threat
    anchor: Vec2
    # Is this a deep zone (affects backpedal behavior)
    is_deep: bool = False

    def contains(self, pos: Vec2) -> bool:
        """Check if position is in this zone."""
        return (self.min_x <= pos.x <= self.max_x and
                self.min_y <= pos.y <= self.max_y)

    def distance_to_boundary(self, pos: Vec2) -> float:
        """How far is a position from entering this zone."""
        dx = max(self.min_x - pos.x, 0, pos.x - self.max_x)
        dy = max(self.min_y - pos.y, 0, pos.y - self.max_y)
        return math.sqrt(dx * dx + dy * dy)


# Zone boundaries - realistic coverage areas
# Deep anchors are shallower (10-14 yards) to read the play before dropping
ZONE_BOUNDARIES: dict[ZoneType, ZoneBoundary] = {
    # Deep thirds (Cover 3) - wide and deep
    ZoneType.DEEP_THIRD_L: ZoneBoundary(
        min_x=-30, max_x=-8, min_y=10, max_y=50,
        anchor=Vec2(-16, 12), is_deep=True
    ),
    ZoneType.DEEP_THIRD_M: ZoneBoundary(
        min_x=-10, max_x=10, min_y=12, max_y=50,
        anchor=Vec2(0, 14), is_deep=True
    ),
    ZoneType.DEEP_THIRD_R: ZoneBoundary(
        min_x=8, max_x=30, min_y=10, max_y=50,
        anchor=Vec2(16, 12), is_deep=True
    ),
    # Deep halves (Cover 2) - two deep safeties
    ZoneType.DEEP_HALF_L: ZoneBoundary(
        min_x=-30, max_x=0, min_y=10, max_y=50,
        anchor=Vec2(-12, 12), is_deep=True
    ),
    ZoneType.DEEP_HALF_R: ZoneBoundary(
        min_x=0, max_x=30, min_y=10, max_y=50,
        anchor=Vec2(12, 12), is_deep=True
    ),
    # Quarters (Cover 4)
    ZoneType.DEEP_QUARTER_1: ZoneBoundary(
        min_x=-30, max_x=-10, min_y=8, max_y=50,
        anchor=Vec2(-16, 10), is_deep=True
    ),
    ZoneType.DEEP_QUARTER_2: ZoneBoundary(
        min_x=-12, max_x=0, min_y=10, max_y=50,
        anchor=Vec2(-6, 12), is_deep=True
    ),
    ZoneType.DEEP_QUARTER_3: ZoneBoundary(
        min_x=0, max_x=12, min_y=10, max_y=50,
        anchor=Vec2(6, 12), is_deep=True
    ),
    ZoneType.DEEP_QUARTER_4: ZoneBoundary(
        min_x=10, max_x=30, min_y=8, max_y=50,
        anchor=Vec2(16, 10), is_deep=True
    ),
    # Flat zones - sidelines, short
    ZoneType.FLAT_L: ZoneBoundary(
        min_x=-30, max_x=-8, min_y=-2, max_y=8,
        anchor=Vec2(-14, 4), is_deep=False
    ),
    ZoneType.FLAT_R: ZoneBoundary(
        min_x=8, max_x=30, min_y=-2, max_y=8,
        anchor=Vec2(14, 4), is_deep=False
    ),
    # Hook zones - inside, medium depth
    ZoneType.HOOK_L: ZoneBoundary(
        min_x=-12, max_x=-2, min_y=5, max_y=14,
        anchor=Vec2(-6, 8), is_deep=False
    ),
    ZoneType.HOOK_R: ZoneBoundary(
        min_x=2, max_x=12, min_y=5, max_y=14,
        anchor=Vec2(6, 8), is_deep=False
    ),
    # Curl/flat zones - outside, underneath
    ZoneType.CURL_FLAT_L: ZoneBoundary(
        min_x=-25, max_x=-5, min_y=0, max_y=12,
        anchor=Vec2(-12, 6), is_deep=False
    ),
    ZoneType.CURL_FLAT_R: ZoneBoundary(
        min_x=5, max_x=25, min_y=0, max_y=12,
        anchor=Vec2(12, 6), is_deep=False
    ),
    # Middle zone
    ZoneType.MIDDLE: ZoneBoundary(
        min_x=-8, max_x=8, min_y=8, max_y=16,
        anchor=Vec2(0, 10), is_deep=False
    ),
}

# Legacy compatibility - centers for visualization
ZONE_CENTERS: dict[ZoneType, Vec2] = {
    zone_type: boundary.anchor
    for zone_type, boundary in ZONE_BOUNDARIES.items()
}

ZONE_RADIUS: dict[ZoneType, float] = {
    # Calculate approximate radius from boundary size
    zone_type: max(
        (boundary.max_x - boundary.min_x) / 2,
        (boundary.max_y - boundary.min_y) / 2
    ) * 0.6  # Reduced for visualization
    for zone_type, boundary in ZONE_BOUNDARIES.items()
}


# =============================================================================
# Dataclasses
# =============================================================================

@dataclass
class TeamReceiver:
    """Receiver in team context."""
    id: str
    position: Vec2
    alignment: ReceiverPosition
    route: list[RouteWaypoint]
    route_type: RouteType
    attributes: ReceiverAttributes = field(default_factory=ReceiverAttributes)

    # Route state
    current_waypoint_idx: int = 0
    route_phase: RoutePhase = RoutePhase.PRE_SNAP
    release_result: Optional[ReleaseResult] = None
    release_delay: int = 0

    # Physics
    velocity: Vec2 = field(default_factory=lambda: Vec2(0, 0))
    current_speed: float = 0.0

    # Visual
    animation: Animation = Animation.STANCE
    facing: Vec2 = field(default_factory=lambda: Vec2(0, 1))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "position": self.position.to_dict(),
            "alignment": self.alignment.value,
            "route": [w.to_dict() for w in self.route],
            "route_type": self.route_type.value,
            "attributes": self.attributes.to_dict(),
            "current_waypoint_idx": self.current_waypoint_idx,
            "route_phase": self.route_phase.value,
            "animation": self.animation.value,
            "facing": self.facing.to_dict(),
        }


@dataclass
class TeamDefender:
    """Defensive back in team context."""
    id: str
    position: Vec2
    alignment: DefenderPosition
    attributes: DBAttributes = field(default_factory=DBAttributes)

    # Coverage assignment
    man_assignment: Optional[str] = None  # Receiver ID for man coverage
    zone_assignment: Optional[ZoneType] = None  # Zone for zone coverage
    zone_center: Optional[Vec2] = None
    zone_radius: float = 10.0

    # Coverage state
    is_in_man: bool = False
    reaction_delay: int = 0
    has_reacted_to_break: bool = False

    # Zone coverage state
    zone_target_id: Optional[str] = None  # Receiver currently tracking in zone
    is_backpedaling: bool = True  # Deep zone backpedal phase
    has_triggered: bool = False  # Broke on a receiver

    # Predictive tracking - DB anticipates where WR is going
    anticipated_position: Optional[Vec2] = None  # Where DB thinks WR will be
    last_read_velocity: Vec2 = field(default_factory=lambda: Vec2(0, 0))  # WR velocity DB is projecting from
    pre_break_velocity: Optional[Vec2] = None  # Frozen velocity from before the break
    read_confidence: float = 1.0  # How confident DB is in their read (0-1)
    ticks_since_read_update: int = 0  # How stale is the read

    # Physics
    velocity: Vec2 = field(default_factory=lambda: Vec2(0, 0))
    current_speed: float = 0.0

    # Visual
    animation: Animation = Animation.STANCE
    facing: Vec2 = field(default_factory=lambda: Vec2(0, -1))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "position": self.position.to_dict(),
            "alignment": self.alignment.value,
            "attributes": self.attributes.to_dict(),
            "man_assignment": self.man_assignment,
            "zone_assignment": self.zone_assignment.value if self.zone_assignment else None,
            "is_in_man": self.is_in_man,
            "animation": self.animation.value,
            "facing": self.facing.to_dict(),
        }


@dataclass
class MatchupResult:
    """Result of a single WR vs DB matchup."""
    receiver_id: str
    defender_id: str
    separation: float
    max_separation: float
    result: str  # "open", "contested", "covered"

    def to_dict(self) -> dict:
        return {
            "receiver_id": self.receiver_id,
            "defender_id": self.defender_id,
            "separation": round(self.separation, 2),
            "max_separation": round(self.max_separation, 2),
            "result": self.result,
        }


@dataclass
class TeamRouteSimState:
    """Complete state of team route simulation."""
    receivers: list[TeamReceiver]
    defenders: list[TeamDefender]
    formation: Formation
    coverage: CoverageScheme
    concept: RouteConcept

    # Tracking
    matchups: dict[str, MatchupResult] = field(default_factory=dict)  # receiver_id -> result
    tick: int = 0
    is_complete: bool = False

    def to_dict(self) -> dict:
        return {
            "receivers": [r.to_dict() for r in self.receivers],
            "defenders": [d.to_dict() for d in self.defenders],
            "formation": self.formation.value,
            "coverage": self.coverage.value,
            "concept": self.concept.value,
            "matchups": {k: v.to_dict() for k, v in self.matchups.items()},
            "tick": self.tick,
            "is_complete": self.is_complete,
        }


# =============================================================================
# Formation Alignments
# =============================================================================

def get_receiver_alignments(formation: Formation) -> dict[ReceiverPosition, Vec2]:
    """Get receiver starting positions for a formation."""
    if formation == Formation.TRIPS_RIGHT:
        return {
            ReceiverPosition.X: Vec2(-22, 0),      # Split end left
            ReceiverPosition.SLOT_R: Vec2(5, 0),   # Inside slot
            ReceiverPosition.Z: Vec2(12, 0),       # Middle slot
            ReceiverPosition.TE: Vec2(20, 0),      # Outside
        }
    elif formation == Formation.TRIPS_LEFT:
        return {
            ReceiverPosition.X: Vec2(-20, 0),      # Outside left
            ReceiverPosition.SLOT_L: Vec2(-12, 0), # Middle slot left
            ReceiverPosition.Z: Vec2(-5, 0),       # Inside slot left
            ReceiverPosition.TE: Vec2(22, 0),      # Split end right
        }
    elif formation == Formation.SPREAD:
        return {
            ReceiverPosition.X: Vec2(-22, 0),      # Wide left
            ReceiverPosition.SLOT_L: Vec2(-8, 0),  # Slot left
            ReceiverPosition.SLOT_R: Vec2(8, 0),   # Slot right
            ReceiverPosition.Z: Vec2(22, 0),       # Wide right
        }
    elif formation == Formation.EMPTY:
        return {
            ReceiverPosition.X: Vec2(-25, 0),
            ReceiverPosition.SLOT_L: Vec2(-10, 0),
            ReceiverPosition.TE: Vec2(0, 0),       # TE in middle
            ReceiverPosition.SLOT_R: Vec2(10, 0),
            ReceiverPosition.Z: Vec2(25, 0),
        }
    else:  # DOUBLES
        return {
            ReceiverPosition.X: Vec2(-22, 0),
            ReceiverPosition.SLOT_L: Vec2(-8, 0),
            ReceiverPosition.SLOT_R: Vec2(8, 0),
            ReceiverPosition.Z: Vec2(22, 0),
        }


# =============================================================================
# Coverage Assignments
# =============================================================================

def get_coverage_assignments(
    coverage: CoverageScheme,
    receivers: list[TeamReceiver],
) -> dict[DefenderPosition, tuple[Optional[str], Optional[ZoneType]]]:
    """Get defender assignments (man_target_id, zone_type) for coverage."""

    # Find receivers by position
    rcvr_by_pos = {r.alignment: r for r in receivers}

    if coverage == CoverageScheme.COVER_0:
        # Pure man, no safety help
        return {
            DefenderPosition.CB1: (rcvr_by_pos.get(ReceiverPosition.X, receivers[0]).id if receivers else None, None),
            DefenderPosition.CB2: (rcvr_by_pos.get(ReceiverPosition.Z, receivers[-1] if receivers else None).id if receivers else None, None),
            DefenderPosition.NICKEL: (rcvr_by_pos.get(ReceiverPosition.SLOT_R, receivers[1] if len(receivers) > 1 else None).id if len(receivers) > 1 else None, None),
            DefenderPosition.SS: (rcvr_by_pos.get(ReceiverPosition.SLOT_L, receivers[2] if len(receivers) > 2 else None).id if len(receivers) > 2 else None, None),
            DefenderPosition.FS: (rcvr_by_pos.get(ReceiverPosition.TE, receivers[3] if len(receivers) > 3 else None).id if len(receivers) > 3 else None, None),
        }

    elif coverage == CoverageScheme.COVER_1:
        # Man with single high safety
        x_id = rcvr_by_pos.get(ReceiverPosition.X).id if ReceiverPosition.X in rcvr_by_pos else None
        z_id = rcvr_by_pos.get(ReceiverPosition.Z).id if ReceiverPosition.Z in rcvr_by_pos else None
        slot_r_id = rcvr_by_pos.get(ReceiverPosition.SLOT_R).id if ReceiverPosition.SLOT_R in rcvr_by_pos else None
        slot_l_id = rcvr_by_pos.get(ReceiverPosition.SLOT_L).id if ReceiverPosition.SLOT_L in rcvr_by_pos else None

        return {
            DefenderPosition.CB1: (x_id, None),
            DefenderPosition.CB2: (z_id, None),
            DefenderPosition.NICKEL: (slot_r_id or slot_l_id, None),
            DefenderPosition.SS: (slot_l_id if slot_r_id else None, None),
            DefenderPosition.FS: (None, ZoneType.DEEP_THIRD_M),  # Single high
        }

    elif coverage == CoverageScheme.COVER_2:
        # 2 deep safeties, corners play flats
        return {
            DefenderPosition.CB1: (None, ZoneType.FLAT_L),
            DefenderPosition.CB2: (None, ZoneType.FLAT_R),
            DefenderPosition.NICKEL: (None, ZoneType.HOOK_R),
            DefenderPosition.SS: (None, ZoneType.DEEP_HALF_L),
            DefenderPosition.FS: (None, ZoneType.DEEP_HALF_R),
        }

    elif coverage == CoverageScheme.COVER_3:
        # 3 deep zones, 4 under
        # CBs play deep thirds but read from 7-8 yards
        # SS/Nickel play curl-flat (underneath)
        return {
            DefenderPosition.CB1: (None, ZoneType.DEEP_THIRD_L),
            DefenderPosition.CB2: (None, ZoneType.DEEP_THIRD_R),
            DefenderPosition.NICKEL: (None, ZoneType.CURL_FLAT_R),
            DefenderPosition.SS: (None, ZoneType.CURL_FLAT_L),
            DefenderPosition.FS: (None, ZoneType.DEEP_THIRD_M),
        }

    elif coverage == CoverageScheme.COVER_4:
        # Quarters - 4 deep
        return {
            DefenderPosition.CB1: (None, ZoneType.DEEP_QUARTER_1),
            DefenderPosition.CB2: (None, ZoneType.DEEP_QUARTER_4),
            DefenderPosition.NICKEL: (None, ZoneType.HOOK_R),
            DefenderPosition.SS: (None, ZoneType.DEEP_QUARTER_2),
            DefenderPosition.FS: (None, ZoneType.DEEP_QUARTER_3),
        }

    else:  # COVER_2_MAN
        # 2 deep safeties, man underneath
        x_id = rcvr_by_pos.get(ReceiverPosition.X).id if ReceiverPosition.X in rcvr_by_pos else None
        z_id = rcvr_by_pos.get(ReceiverPosition.Z).id if ReceiverPosition.Z in rcvr_by_pos else None
        slot_r_id = rcvr_by_pos.get(ReceiverPosition.SLOT_R).id if ReceiverPosition.SLOT_R in rcvr_by_pos else None

        return {
            DefenderPosition.CB1: (x_id, None),
            DefenderPosition.CB2: (z_id, None),
            DefenderPosition.NICKEL: (slot_r_id, None),
            DefenderPosition.SS: (None, ZoneType.DEEP_HALF_L),
            DefenderPosition.FS: (None, ZoneType.DEEP_HALF_R),
        }


def get_defender_start_positions(
    coverage: CoverageScheme,
    receivers: list[TeamReceiver],
) -> dict[DefenderPosition, Vec2]:
    """Get defender starting positions based on coverage and receiver alignment."""
    rcvr_by_pos = {r.alignment: r for r in receivers}

    # Base positions - closer to LOS, realistic pre-snap alignment
    positions = {
        DefenderPosition.CB1: Vec2(-22, 6),
        DefenderPosition.CB2: Vec2(22, 6),
        DefenderPosition.NICKEL: Vec2(8, 5),
        DefenderPosition.SS: Vec2(-8, 8),
        DefenderPosition.FS: Vec2(0, 12),
    }

    # Adjust based on coverage
    if coverage in (CoverageScheme.COVER_0, CoverageScheme.COVER_1, CoverageScheme.COVER_2_MAN):
        # Man coverage - align over receivers, close
        if ReceiverPosition.X in rcvr_by_pos:
            positions[DefenderPosition.CB1] = rcvr_by_pos[ReceiverPosition.X].position + Vec2(0, 5)
        if ReceiverPosition.Z in rcvr_by_pos:
            positions[DefenderPosition.CB2] = rcvr_by_pos[ReceiverPosition.Z].position + Vec2(0, 5)
        if ReceiverPosition.SLOT_R in rcvr_by_pos:
            positions[DefenderPosition.NICKEL] = rcvr_by_pos[ReceiverPosition.SLOT_R].position + Vec2(0, 4)
        if ReceiverPosition.SLOT_L in rcvr_by_pos:
            positions[DefenderPosition.SS] = rcvr_by_pos[ReceiverPosition.SLOT_L].position + Vec2(0, 4)
        # Cover 1 FS plays deep middle
        if coverage == CoverageScheme.COVER_1:
            positions[DefenderPosition.FS] = Vec2(0, 14)

    elif coverage == CoverageScheme.COVER_2:
        # Cover 2 - corners jam at LOS in flats, safeties deep halves
        # CBs align outside the #1 receiver, ready to funnel inside
        if ReceiverPosition.X in rcvr_by_pos:
            positions[DefenderPosition.CB1] = Vec2(rcvr_by_pos[ReceiverPosition.X].position.x - 2, 3)
        else:
            positions[DefenderPosition.CB1] = Vec2(-18, 3)
        if ReceiverPosition.Z in rcvr_by_pos:
            positions[DefenderPosition.CB2] = Vec2(rcvr_by_pos[ReceiverPosition.Z].position.x + 2, 3)
        else:
            positions[DefenderPosition.CB2] = Vec2(18, 3)
        # Nickel in hook zone
        positions[DefenderPosition.NICKEL] = Vec2(5, 6)
        # Safeties at 12-14 yards
        positions[DefenderPosition.SS] = Vec2(-12, 13)
        positions[DefenderPosition.FS] = Vec2(12, 13)

    elif coverage == CoverageScheme.COVER_3:
        # Cover 3 - corners at 7-8 yards off, will backpedal to deep third
        # Align inside shade to funnel receivers outside
        if ReceiverPosition.X in rcvr_by_pos:
            positions[DefenderPosition.CB1] = Vec2(rcvr_by_pos[ReceiverPosition.X].position.x + 2, 7)
        else:
            positions[DefenderPosition.CB1] = Vec2(-20, 7)
        if ReceiverPosition.Z in rcvr_by_pos:
            positions[DefenderPosition.CB2] = Vec2(rcvr_by_pos[ReceiverPosition.Z].position.x - 2, 7)
        else:
            positions[DefenderPosition.CB2] = Vec2(20, 7)
        # SS and Nickel play curl-flat, closer to LOS
        positions[DefenderPosition.SS] = Vec2(-10, 5)
        positions[DefenderPosition.NICKEL] = Vec2(10, 5)
        # FS plays deep middle third
        positions[DefenderPosition.FS] = Vec2(0, 14)

    elif coverage == CoverageScheme.COVER_4:
        # Quarters - all 4 DBs at medium depth, read receivers
        if ReceiverPosition.X in rcvr_by_pos:
            positions[DefenderPosition.CB1] = Vec2(rcvr_by_pos[ReceiverPosition.X].position.x, 7)
        else:
            positions[DefenderPosition.CB1] = Vec2(-20, 7)
        if ReceiverPosition.Z in rcvr_by_pos:
            positions[DefenderPosition.CB2] = Vec2(rcvr_by_pos[ReceiverPosition.Z].position.x, 7)
        else:
            positions[DefenderPosition.CB2] = Vec2(20, 7)
        # Safeties at 10-12 yards, inside the slots
        positions[DefenderPosition.SS] = Vec2(-7, 10)
        positions[DefenderPosition.FS] = Vec2(7, 10)
        # Nickel in hook zone
        positions[DefenderPosition.NICKEL] = Vec2(4, 6)

    return positions


# =============================================================================
# Route Concepts
# =============================================================================

def get_routes_for_concept(
    concept: RouteConcept,
    formation: Formation,
) -> dict[ReceiverPosition, RouteType]:
    """Get route assignments for a play concept."""

    if concept == RouteConcept.FOUR_VERTS:
        return {
            ReceiverPosition.X: RouteType.GO,
            ReceiverPosition.SLOT_L: RouteType.GO,
            ReceiverPosition.SLOT_R: RouteType.GO,
            ReceiverPosition.Z: RouteType.GO,
            ReceiverPosition.TE: RouteType.GO,
        }

    elif concept == RouteConcept.MESH:
        return {
            ReceiverPosition.X: RouteType.IN,
            ReceiverPosition.SLOT_L: RouteType.SLANT,
            ReceiverPosition.SLOT_R: RouteType.SLANT,
            ReceiverPosition.Z: RouteType.IN,
            ReceiverPosition.TE: RouteType.FLAT,
        }

    elif concept == RouteConcept.SMASH:
        # Corner + hitch combo
        return {
            ReceiverPosition.X: RouteType.CORNER,
            ReceiverPosition.SLOT_L: RouteType.HITCH,
            ReceiverPosition.SLOT_R: RouteType.HITCH,
            ReceiverPosition.Z: RouteType.CORNER,
            ReceiverPosition.TE: RouteType.FLAT,
        }

    elif concept == RouteConcept.FLOOD:
        # Three levels to one side
        if formation in (Formation.TRIPS_RIGHT, Formation.SPREAD):
            return {
                ReceiverPosition.X: RouteType.POST,
                ReceiverPosition.SLOT_L: RouteType.GO,
                ReceiverPosition.SLOT_R: RouteType.OUT,
                ReceiverPosition.Z: RouteType.CORNER,
                ReceiverPosition.TE: RouteType.FLAT,
            }
        else:
            return {
                ReceiverPosition.X: RouteType.CORNER,
                ReceiverPosition.SLOT_L: RouteType.OUT,
                ReceiverPosition.SLOT_R: RouteType.GO,
                ReceiverPosition.Z: RouteType.POST,
                ReceiverPosition.TE: RouteType.FLAT,
            }

    elif concept == RouteConcept.LEVELS:
        return {
            ReceiverPosition.X: RouteType.IN,
            ReceiverPosition.SLOT_L: RouteType.IN,
            ReceiverPosition.SLOT_R: RouteType.SLANT,
            ReceiverPosition.Z: RouteType.IN,
            ReceiverPosition.TE: RouteType.FLAT,
        }

    elif concept == RouteConcept.SLANTS:
        return {
            ReceiverPosition.X: RouteType.SLANT,
            ReceiverPosition.SLOT_L: RouteType.SLANT,
            ReceiverPosition.SLOT_R: RouteType.SLANT,
            ReceiverPosition.Z: RouteType.SLANT,
            ReceiverPosition.TE: RouteType.FLAT,
        }

    elif concept == RouteConcept.CURLS:
        return {
            ReceiverPosition.X: RouteType.CURL,
            ReceiverPosition.SLOT_L: RouteType.FLAT,
            ReceiverPosition.SLOT_R: RouteType.FLAT,
            ReceiverPosition.Z: RouteType.CURL,
            ReceiverPosition.TE: RouteType.CURL,
        }

    else:  # CUSTOM - default to basic routes
        return {
            ReceiverPosition.X: RouteType.OUT,
            ReceiverPosition.SLOT_L: RouteType.SLANT,
            ReceiverPosition.SLOT_R: RouteType.SLANT,
            ReceiverPosition.Z: RouteType.OUT,
            ReceiverPosition.TE: RouteType.FLAT,
        }


def create_offset_route(route_type: RouteType, start_x: float) -> list[RouteWaypoint]:
    """Create a route with x-offset for receiver's alignment.

    Routes are mirrored for receivers on the right side of the field:
    - Left side (negative x): routes go as designed (out = left, in = right)
    - Right side (positive x): routes mirror horizontally (out = right, in = left)
    """
    base_route = create_route(route_type)
    is_right_side = start_x > 0

    # Routes that need mirroring based on side of field
    # OUT goes away from center, IN goes toward center
    # SLANT goes toward center, CORNER goes away
    result = []
    for wp in base_route:
        if is_right_side:
            # Mirror x coordinate for right-side receivers
            new_x = -wp.position.x + start_x
        else:
            new_x = wp.position.x + start_x

        result.append(RouteWaypoint(
            position=Vec2(new_x, wp.position.y),
            arrival_tick=wp.arrival_tick,
            is_break=wp.is_break,
        ))

    return result


# =============================================================================
# Simulator Constants
# =============================================================================

MAX_TICKS = 50
WR_BASE_SPEED = 0.45
DB_BASE_SPEED = 0.45
DB_REACTION_PENALTY = 0.85
OPEN_SEPARATION = 3.0
CONTESTED_SEPARATION = 1.0

# Predictive tracking constants
BASE_LOOKAHEAD_TICKS = 6  # How far ahead DB projects by default
MAX_LOOKAHEAD_TICKS = 12  # Maximum projection distance
READ_UPDATE_THRESHOLD = 0.15  # Velocity change needed to trigger read update
STALE_READ_PENALTY = 0.1  # Confidence loss per tick of stale read


# =============================================================================
# Team Route Simulator
# =============================================================================

class TeamRouteSimulator:
    """Simulates full receiver corps vs DB corps."""

    def __init__(
        self,
        formation: Formation = Formation.SPREAD,
        coverage: CoverageScheme = CoverageScheme.COVER_3,
        concept: RouteConcept = RouteConcept.FOUR_VERTS,
        wr_attributes: Optional[dict[ReceiverPosition, ReceiverAttributes]] = None,
        db_attributes: Optional[dict[DefenderPosition, DBAttributes]] = None,
    ):
        self.formation = formation
        self.coverage = coverage
        self.concept = concept
        self.wr_attributes = wr_attributes or {}
        self.db_attributes = db_attributes or {}
        self.state: Optional[TeamRouteSimState] = None

        # Track max separation per receiver
        self._max_separations: dict[str, float] = {}

    def setup(self) -> None:
        """Initialize simulation."""
        # Create receivers based on formation
        alignments = get_receiver_alignments(self.formation)
        routes = get_routes_for_concept(self.concept, self.formation)

        receivers = []
        for pos, start_pos in alignments.items():
            route_type = routes.get(pos, RouteType.GO)
            route = create_offset_route(route_type, start_pos.x)

            attrs = self.wr_attributes.get(pos, ReceiverAttributes())

            rcvr = TeamReceiver(
                id=str(uuid.uuid4()),
                position=Vec2(start_pos.x, start_pos.y),
                alignment=pos,
                route=route,
                route_type=route_type,
                attributes=attrs,
            )
            receivers.append(rcvr)

        # Create defenders based on coverage
        assignments = get_coverage_assignments(self.coverage, receivers)
        positions = get_defender_start_positions(self.coverage, receivers)

        defenders = []
        for def_pos, start_pos in positions.items():
            man_target, zone_type = assignments.get(def_pos, (None, None))

            attrs = self.db_attributes.get(def_pos, DBAttributes())

            zone_center = None
            zone_radius = 10.0
            if zone_type:
                zone_center = ZONE_CENTERS.get(zone_type)
                zone_radius = ZONE_RADIUS.get(zone_type, 10.0)

            defender = TeamDefender(
                id=str(uuid.uuid4()),
                position=Vec2(start_pos.x, start_pos.y),
                alignment=def_pos,
                attributes=attrs,
                man_assignment=man_target,
                zone_assignment=zone_type,
                zone_center=zone_center,
                zone_radius=zone_radius,
                is_in_man=man_target is not None,
            )
            defenders.append(defender)

        # Initialize matchups tracking
        matchups = {}
        for rcvr in receivers:
            matchups[rcvr.id] = MatchupResult(
                receiver_id=rcvr.id,
                defender_id="",
                separation=0.0,
                max_separation=0.0,
                result="in_progress",
            )
            self._max_separations[rcvr.id] = 0.0

        self.state = TeamRouteSimState(
            receivers=receivers,
            defenders=defenders,
            formation=self.formation,
            coverage=self.coverage,
            concept=self.concept,
            matchups=matchups,
        )

    def reset(self) -> None:
        """Reset simulation."""
        self._max_separations = {}
        self.setup()

    def tick(self) -> TeamRouteSimState:
        """Advance simulation by one tick."""
        if not self.state or self.state.is_complete:
            return self.state

        self.state.tick += 1

        # Process each receiver
        for rcvr in self.state.receivers:
            self._process_receiver(rcvr)

        # Process each defender
        for defender in self.state.defenders:
            self._process_defender(defender)

        # Update separations and matchups
        self._update_matchups()

        # Check completion
        self._check_completion()

        return self.state

    def _process_receiver(self, rcvr: TeamReceiver) -> None:
        """Move receiver along route."""
        # Phase transitions
        if self.state.tick == 1:
            rcvr.route_phase = RoutePhase.RELEASE

        if rcvr.route_phase == RoutePhase.RELEASE:
            if self.state.tick >= 2:
                rcvr.route_phase = RoutePhase.STEM
                rcvr.animation = Animation.ROUTE_STEM
            return

        if rcvr.current_waypoint_idx >= len(rcvr.route):
            rcvr.route_phase = RoutePhase.COMPLETE
            return

        waypoint = rcvr.route[rcvr.current_waypoint_idx]

        # Check for break
        if waypoint.is_break and rcvr.route_phase != RoutePhase.BREAK:
            if self.state.tick >= waypoint.arrival_tick - 2:
                rcvr.route_phase = RoutePhase.BREAK
                rcvr.animation = Animation.ROUTE_BREAK

        # Calculate movement
        target = waypoint.position
        desired_direction = (target - rcvr.position).normalized()

        # Speed with acceleration and COD
        max_speed = WR_BASE_SPEED * (rcvr.attributes.speed / 85) ** 2
        accel_rate = 0.08 * (rcvr.attributes.acceleration / 85) ** 1.5

        # COD penalty
        if rcvr.current_speed > 0.1:
            current_dir = rcvr.velocity.normalized()
            dot = current_dir.dot(desired_direction)
            dot = max(-1.0, min(1.0, dot))
            angle = math.acos(dot)

            if angle > 0.5:
                route_skill = (rcvr.attributes.route_running / 85) ** 1.5
                base_loss = angle / math.pi
                cod_loss = min(0.4, base_loss * (1.0 - route_skill * 0.4))
                rcvr.current_speed *= (1.0 - cod_loss)

        # Accelerate
        if rcvr.current_speed < max_speed:
            rcvr.current_speed = min(max_speed, rcvr.current_speed + accel_rate)

        # Break speed cap
        if rcvr.route_phase == RoutePhase.BREAK:
            break_cap = max_speed * 0.7 * (rcvr.attributes.route_running / 85)
            rcvr.current_speed = min(rcvr.current_speed, break_cap)

        # Update position
        rcvr.velocity = desired_direction * rcvr.current_speed
        rcvr.position = rcvr.position + rcvr.velocity
        rcvr.facing = desired_direction

        # Check waypoint reached
        if rcvr.position.distance_to(target) < 0.5:
            rcvr.current_waypoint_idx += 1
            if rcvr.route_phase == RoutePhase.BREAK:
                rcvr.route_phase = RoutePhase.POST_BREAK
                rcvr.animation = Animation.ROUTE_RUN

    def _process_defender(self, defender: TeamDefender) -> None:
        """Move defender based on coverage assignment."""
        if defender.is_in_man and defender.man_assignment:
            self._process_man_defender(defender)
        elif defender.zone_assignment:
            self._process_zone_defender(defender)

    def _process_man_defender(self, defender: TeamDefender) -> None:
        """DB follows assigned receiver using predictive tracking.

        Instead of tracking where the WR is, the DB tracks where they
        ANTICIPATE the WR will be based on current velocity. This creates
        realistic behavior where route breaks throw off the DB's read.

        Key concept: The DB projects ahead based on WR velocity. When WR
        breaks, DB continues projecting in the OLD direction until they
        can react and "flip their hips" to the new direction.
        """
        # Find target receiver
        target_rcvr = None
        for rcvr in self.state.receivers:
            if rcvr.id == defender.man_assignment:
                target_rcvr = rcvr
                break

        if not target_rcvr:
            return

        # === PREDICTIVE TRACKING ===

        # Calculate lookahead based on play recognition
        play_rec_factor = defender.attributes.play_recognition / 100
        distance_to_wr = defender.position.distance_to(target_rcvr.position)

        # Better play recognition = project further ahead (better anticipation)
        base_lookahead = BASE_LOOKAHEAD_TICKS + (play_rec_factor * 4)
        # When very close, reduce lookahead (react to what's in front of you)
        # But keep minimum lookahead to create separation on breaks
        if distance_to_wr < 1.5:
            base_lookahead *= 0.5
        elif distance_to_wr < 3:
            base_lookahead *= 0.7
        lookahead_ticks = max(3, min(MAX_LOOKAHEAD_TICKS, base_lookahead))

        # === HANDLE BREAK PHASE ===
        just_started_flip = False

        if target_rcvr.route_phase == RoutePhase.BREAK:
            if not defender.has_reacted_to_break and defender.reaction_delay == 0:
                # Break just started! Set reaction delay
                # Higher play recognition = shorter delay
                base_delay = 5  # Base 5 ticks to react
                delay_reduction = play_rec_factor * 2  # Up to 2 ticks faster
                defender.reaction_delay = max(3, int(base_delay - delay_reduction))
                # Freeze the PRE-BREAK velocity for projection
                # This is the key to creating separation - DB projects where WR WAS going
                if defender.pre_break_velocity is None:
                    defender.pre_break_velocity = Vec2(
                        defender.last_read_velocity.x,
                        defender.last_read_velocity.y
                    )
                defender.read_confidence = 1.0  # Confidently projecting WRONG direction

            if not defender.has_reacted_to_break:
                defender.reaction_delay -= 1
                # During reaction delay, use frozen pre-break velocity
                # This makes DB project in wrong direction, creating separation
                if defender.pre_break_velocity:
                    defender.last_read_velocity = defender.pre_break_velocity

                if defender.reaction_delay <= 0:
                    defender.has_reacted_to_break = True
                    defender.animation = Animation.FLIP_HIPS
                    just_started_flip = True
                    # Now update read with ACTUAL new velocity
                    defender.last_read_velocity = Vec2(target_rcvr.velocity.x, target_rcvr.velocity.y)
                    defender.pre_break_velocity = None  # Clear frozen velocity
                    defender.read_confidence = 0.5  # Less confident initially after flip

        elif target_rcvr.route_phase == RoutePhase.POST_BREAK:
            # Recovering from break
            if defender.has_reacted_to_break:
                # Gradually rebuild confidence
                defender.read_confidence = min(1.0, defender.read_confidence + 0.1)
                # Update velocity read
                defender.last_read_velocity = Vec2(target_rcvr.velocity.x, target_rcvr.velocity.y)
                defender.pre_break_velocity = None
        else:
            # Normal tracking (STEM phase) - continuously update read
            # Also continuously save velocity for pre-break reference
            if target_rcvr.velocity.length() > 0.05:
                defender.last_read_velocity = Vec2(target_rcvr.velocity.x, target_rcvr.velocity.y)
            defender.read_confidence = 1.0
            defender.pre_break_velocity = None  # Clear any stale pre-break velocity

        # === PROJECT ANTICIPATED POSITION ===
        # DB projects where WR will be based on THEIR READ of velocity
        # During break, this is the OLD velocity, which is wrong!
        projected_pos = target_rcvr.position + defender.last_read_velocity * lookahead_ticks

        # Blend projection with actual position based on confidence and distance
        # Higher confidence = trust projection more
        # During breaks with pre_break_velocity, use FULL projection (this is the key!)
        # This makes DB continue running in wrong direction
        if defender.pre_break_velocity is not None:
            # During break reaction delay - commit to the wrong projection
            projection_weight = 1.0  # Full commitment to wrong direction
        else:
            projection_weight = defender.read_confidence
            # When close and NOT in break, can reduce projection
            if distance_to_wr < 2:
                projection_weight *= 0.6

        anticipated = Vec2(
            target_rcvr.position.x * (1 - projection_weight) + projected_pos.x * projection_weight,
            target_rcvr.position.y * (1 - projection_weight) + projected_pos.y * projection_weight,
        )
        defender.anticipated_position = anticipated

        # === DETERMINE TARGET ===
        target = anticipated

        desired_direction = (target - defender.position).normalized()

        # Speed calculation
        speed_factor = (defender.attributes.speed / 85) ** 2
        coverage_factor = (defender.attributes.man_coverage / 85) ** 1.5
        max_speed = DB_BASE_SPEED * speed_factor * coverage_factor
        accel_rate = 0.07 * (defender.attributes.acceleration / 85) ** 1.5

        # One-time flip penalty
        if just_started_flip:
            flip_penalty = 0.4 + (defender.attributes.man_coverage / 100) * 0.2
            defender.current_speed *= flip_penalty

        # COD (skip during flip)
        if defender.current_speed > 0.1 and defender.animation != Animation.FLIP_HIPS:
            current_dir = defender.velocity.normalized()
            dot = current_dir.dot(desired_direction)
            dot = max(-1.0, min(1.0, dot))
            angle = math.acos(dot)

            if angle > 0.5:
                skill_factor = (defender.attributes.man_coverage / 85) ** 1.5
                base_loss = angle / math.pi
                cod_loss = min(0.4, base_loss * (1.0 - skill_factor * 0.35))
                defender.current_speed *= (1.0 - cod_loss)

        # Accelerate
        if defender.current_speed < max_speed:
            defender.current_speed = min(max_speed, defender.current_speed + accel_rate)

        # Flip hips speed cap
        if defender.animation == Animation.FLIP_HIPS:
            defender.current_speed = min(defender.current_speed, max_speed * 0.6)

        # Pre-reaction penalty
        if target_rcvr.route_phase in (RoutePhase.BREAK, RoutePhase.POST_BREAK) and not defender.has_reacted_to_break:
            defender.current_speed = min(defender.current_speed, max_speed * DB_REACTION_PENALTY)

        # Update position
        defender.velocity = desired_direction * defender.current_speed
        defender.position = defender.position + defender.velocity
        defender.facing = desired_direction

        # Animation transitions
        is_trailing = defender.position.y < target_rcvr.position.y
        if defender.animation == Animation.FLIP_HIPS:
            if defender.has_reacted_to_break and defender.reaction_delay <= -2:
                defender.animation = Animation.TRAIL if is_trailing else Animation.CLOSING
            defender.reaction_delay -= 1
        elif defender.animation not in (Animation.PRESS_JAM, Animation.PRESS_BEAT):
            defender.animation = Animation.TRAIL if is_trailing else Animation.CLOSING

    def _process_zone_defender(self, defender: TeamDefender) -> None:
        """Smart zone coverage - pattern read, break on threats, wall off."""
        if not defender.zone_assignment:
            return

        zone = ZONE_BOUNDARIES.get(defender.zone_assignment)
        if not zone:
            return

        # Find the best receiver to cover in this zone
        target_rcvr, threat_level = self._find_zone_threat(defender, zone)

        # Determine target position and behavior
        target = self._get_zone_target_position(defender, zone, target_rcvr, threat_level)

        # Calculate movement
        desired_direction = (target - defender.position).normalized()

        # Speed calculation - faster when triggered on a receiver
        speed_factor = (defender.attributes.speed / 85) ** 2
        zone_factor = (defender.attributes.zone_coverage / 85) ** 1.5

        if defender.has_triggered and target_rcvr:
            # Breaking on receiver - full speed
            max_speed = DB_BASE_SPEED * speed_factor * zone_factor
        elif defender.is_backpedaling and zone.is_deep:
            # Backpedal - slower
            max_speed = DB_BASE_SPEED * speed_factor * 0.6
        else:
            # Reading/shuffling in zone
            max_speed = DB_BASE_SPEED * speed_factor * zone_factor * 0.75

        accel_rate = 0.07 * (defender.attributes.acceleration / 85) ** 1.5

        # COD penalty (reduced when triggered)
        if defender.current_speed > 0.1:
            current_dir = defender.velocity.normalized()
            dot = current_dir.dot(desired_direction)
            dot = max(-1.0, min(1.0, dot))
            angle = math.acos(dot)

            if angle > 0.5:
                skill_factor = (defender.attributes.zone_coverage / 85) ** 1.5
                base_loss = angle / math.pi
                # Less COD penalty when triggered (commitment)
                cod_mult = 0.2 if defender.has_triggered else 0.35
                cod_loss = min(0.4, base_loss * (1.0 - skill_factor * cod_mult))
                defender.current_speed *= (1.0 - cod_loss)

        # Accelerate
        if defender.current_speed < max_speed:
            defender.current_speed = min(max_speed, defender.current_speed + accel_rate)

        # Slow when near anchor and no threat
        if not defender.has_triggered and defender.position.distance_to(zone.anchor) < 2:
            defender.current_speed *= 0.5

        # Update position
        defender.velocity = desired_direction * defender.current_speed
        defender.position = defender.position + defender.velocity
        defender.facing = desired_direction

        # Update animation
        if defender.has_triggered:
            defender.animation = Animation.CLOSING
        elif defender.is_backpedaling:
            defender.animation = Animation.BACKPEDAL
        else:
            defender.animation = Animation.ZONE_READ

    def _find_zone_threat(
        self, defender: TeamDefender, zone: ZoneBoundary
    ) -> tuple[Optional[TeamReceiver], str]:
        """Find the most dangerous receiver threatening this zone.

        Returns (receiver, threat_level) where threat_level is:
        - 'in_zone': Receiver is inside the zone boundaries
        - 'approaching': Receiver is heading toward the zone
        - 'none': No significant threat
        """
        best_rcvr = None
        best_threat = 'none'
        best_score = -float('inf')

        for rcvr in self.state.receivers:
            # Check if receiver is in zone
            in_zone = zone.contains(rcvr.position)

            # Check if receiver is approaching zone
            approaching = False
            dist_to_zone = zone.distance_to_boundary(rcvr.position)
            if dist_to_zone < 10:  # Within 10 yards of zone
                # Check if moving toward zone
                if rcvr.velocity.y > 0.1:  # Moving downfield
                    # Is zone ahead of receiver?
                    if rcvr.position.y < zone.max_y:
                        approaching = True
                # For horizontal movement, check x direction
                if abs(rcvr.velocity.x) > 0.1:
                    if (rcvr.velocity.x > 0 and rcvr.position.x < zone.max_x) or \
                       (rcvr.velocity.x < 0 and rcvr.position.x > zone.min_x):
                        approaching = True

            if not in_zone and not approaching:
                continue

            # Score this receiver as a threat
            score = 0

            if in_zone:
                score += 100  # Strong priority for receivers in zone
                # Bonus for being close to zone center
                dist_to_center = rcvr.position.distance_to(zone.anchor)
                score += max(0, 10 - dist_to_center)

            elif approaching:
                score += 50
                # Closer = more urgent
                score += max(0, 10 - dist_to_zone) * 3

            # Vertical routes more dangerous for deep zones
            if zone.is_deep and rcvr.velocity.y > 0.2:
                score += 20

            # Prefer receiver defender is already tracking
            if defender.zone_target_id == rcvr.id:
                score += 25

            # CRITICAL: For deep zone defenders, prioritize receivers on their side
            # This simulates the CB reading "#1 to my side" not all receivers
            if zone.is_deep:
                # How close is this receiver to the defender's starting x position?
                x_proximity = abs(rcvr.position.x - defender.position.x)
                # Receivers near the defender get big bonus (up to +30)
                score += max(0, 30 - x_proximity * 2)

                # Penalize receivers on the opposite side of the zone
                zone_center_x = (zone.min_x + zone.max_x) / 2
                if (defender.position.x > zone_center_x and rcvr.position.x < zone_center_x) or \
                   (defender.position.x < zone_center_x and rcvr.position.x > zone_center_x):
                    score -= 40  # Heavy penalty for wrong-side receivers

            if score > best_score:
                best_score = score
                best_rcvr = rcvr
                best_threat = 'in_zone' if in_zone else 'approaching'

        return best_rcvr, best_threat

    def _get_zone_target_position(
        self,
        defender: TeamDefender,
        zone: ZoneBoundary,
        target_rcvr: Optional[TeamReceiver],
        threat_level: str,
    ) -> Vec2:
        """Determine where the zone defender should move using predictive tracking."""

        if target_rcvr and threat_level == 'in_zone':
            # Receiver is in our zone - break on them!
            defender.has_triggered = True
            defender.zone_target_id = target_rcvr.id
            defender.is_backpedaling = False

            # === PREDICTIVE TRACKING FOR ZONE ===
            # Project where receiver will be based on velocity
            play_rec_factor = defender.attributes.play_recognition / 100
            lookahead = BASE_LOOKAHEAD_TICKS * (0.5 + play_rec_factor * 0.5)

            anticipated = target_rcvr.position + target_rcvr.velocity * lookahead
            defender.anticipated_position = anticipated

            # For deep zones with vertical routes - match receiver's path
            if zone.is_deep and target_rcvr.velocity.y > 0.25:
                # Run with vertical receiver - match their anticipated x
                target_x = anticipated.x
                target_y = max(defender.position.y, anticipated.y)
                return Vec2(target_x, target_y)

            # For other routes - target anticipated position
            return anticipated

        elif target_rcvr and threat_level == 'approaching':
            # Receiver approaching - prepare to cover using anticipation
            defender.zone_target_id = target_rcvr.id
            defender.is_backpedaling = False

            # Calculate anticipated position
            play_rec_factor = defender.attributes.play_recognition / 100
            lookahead = BASE_LOOKAHEAD_TICKS * (0.5 + play_rec_factor * 0.5)
            anticipated = target_rcvr.position + target_rcvr.velocity * lookahead
            defender.anticipated_position = anticipated

            # For deep zones - handle vertical threats specially
            if zone.is_deep and target_rcvr.velocity.y > 0.25:
                target_x = anticipated.x
                target_y = max(defender.position.y, anticipated.y)
                return Vec2(
                    max(zone.min_x, min(zone.max_x, target_x)),
                    target_y
                )

            # Position to intercept based on anticipated trajectory
            intercept_x = max(zone.min_x, min(zone.max_x, anticipated.x))
            intercept_y = max(zone.min_y, min(zone.max_y, anticipated.y))

            return Vec2(intercept_x, intercept_y)

        else:
            # No threat - stay in zone
            defender.zone_target_id = None
            defender.has_triggered = False
            defender.anticipated_position = None

            # Deep zones: backpedal to anchor position
            if zone.is_deep:
                if defender.position.y < zone.anchor.y - 2:
                    defender.is_backpedaling = True
                else:
                    defender.is_backpedaling = False

                return zone.anchor

            # Under zones: stay at anchor, read
            return zone.anchor

    def _update_matchups(self) -> None:
        """Update separation tracking for each receiver."""
        for rcvr in self.state.receivers:
            # Find closest defender
            closest_defender = None
            min_dist = float('inf')

            for defender in self.state.defenders:
                dist = rcvr.position.distance_to(defender.position)
                if dist < min_dist:
                    min_dist = dist
                    closest_defender = defender

            # Update matchup
            if closest_defender and rcvr.id in self.state.matchups:
                matchup = self.state.matchups[rcvr.id]
                matchup.defender_id = closest_defender.id
                matchup.separation = min_dist

                # Track max
                if min_dist > self._max_separations.get(rcvr.id, 0):
                    self._max_separations[rcvr.id] = min_dist
                matchup.max_separation = self._max_separations.get(rcvr.id, 0)

    def _check_completion(self) -> None:
        """Check if simulation is complete."""
        all_complete = all(
            rcvr.route_phase == RoutePhase.COMPLETE or rcvr.current_waypoint_idx >= len(rcvr.route)
            for rcvr in self.state.receivers
        )

        if all_complete or self.state.tick >= MAX_TICKS:
            self.state.is_complete = True
            self._determine_results()

    def _determine_results(self) -> None:
        """Determine final results for each matchup."""
        for rcvr_id, matchup in self.state.matchups.items():
            max_sep = matchup.max_separation
            final_sep = matchup.separation

            if final_sep < CONTESTED_SEPARATION:
                if max_sep >= OPEN_SEPARATION:
                    matchup.result = "contested"
                else:
                    matchup.result = "covered"
            elif final_sep < OPEN_SEPARATION:
                matchup.result = "contested"
            else:
                matchup.result = "open"

    def run_full(self) -> list[dict]:
        """Run complete simulation."""
        if not self.state:
            self.setup()

        states = [self.state.to_dict()]

        while not self.state.is_complete and self.state.tick < MAX_TICKS:
            self.tick()
            states.append(self.state.to_dict())

        return states
