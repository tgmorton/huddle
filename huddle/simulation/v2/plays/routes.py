"""Route definitions.

Atomic route definitions that can be composed into plays.
Routes are defined as waypoints relative to the receiver's alignment.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from ..core.vec2 import Vec2


class RouteType(str, Enum):
    """Standard route types."""
    # Quick routes (0-5 yards)
    HITCH = "hitch"
    SLANT = "slant"
    FLAT = "flat"
    QUICK_OUT = "quick_out"
    BUBBLE = "bubble"

    # Intermediate (5-15 yards)
    CURL = "curl"
    COMEBACK = "comeback"
    DIG = "dig"
    OUT = "out"
    IN = "in"
    DRAG = "drag"
    CROSS = "cross"
    WHIP = "whip"

    # Deep (15+ yards)
    GO = "go"
    POST = "post"
    CORNER = "corner"
    FADE = "fade"
    STREAK = "streak"
    SEAM = "seam"

    # Special
    WHEEL = "wheel"
    SCREEN = "screen"
    OPTION = "option"
    DOUBLE_MOVE = "double_move"


class RoutePhase(str, Enum):
    """Phase of route execution."""
    PRE_SNAP = "pre_snap"
    RELEASE = "release"
    STEM = "stem"
    BREAK = "break"
    POST_BREAK = "post_break"
    COMPLETE = "complete"


@dataclass
class RouteWaypoint:
    """A waypoint in a route.

    Position is relative to the receiver's starting alignment.
    +X = toward center of field (inside for outside receiver)
    +Y = downfield

    Note: X direction may need to be flipped based on receiver side.

    Attributes:
        offset: Position offset from alignment
        is_break: Is this the primary break point?
        speed_factor: Speed multiplier (1.0 = max, 0.5 = jog)
        phase: What phase this waypoint represents
        look_for_ball: Should receiver look for ball at this point?
    """
    offset: Vec2
    is_break: bool = False
    speed_factor: float = 1.0
    phase: RoutePhase = RoutePhase.STEM
    look_for_ball: bool = False
    description: str = ""

    @property
    def depth(self) -> float:
        """Depth downfield from LOS."""
        return self.offset.y

    @property
    def lateral(self) -> float:
        """Lateral movement from alignment."""
        return self.offset.x


@dataclass
class RouteDefinition:
    """A complete route definition.

    Routes are defined with waypoints relative to alignment.
    The receiver starts at (0, 0) and follows the waypoints.

    Attributes:
        name: Route name
        route_type: Standard route type
        waypoints: List of waypoints to follow
        break_depth: Primary break point depth
        total_depth: Maximum route depth
        route_side: "inside", "outside", or "vertical"
        settles: If True, receiver stops at end of route (curl, hitch). If False, continues in direction.
    """
    name: str
    route_type: RouteType
    waypoints: List[RouteWaypoint]

    # Metadata
    break_depth: float = 0.0
    total_depth: float = 0.0
    route_side: str = "vertical"  # inside, outside, vertical
    is_quick_route: bool = False
    settles: bool = False  # True for curl/hitch, False for slant/go/etc
    timing_notes: str = ""

    def __post_init__(self):
        # Calculate depths if not set
        if self.waypoints:
            if self.break_depth == 0:
                breaks = [w for w in self.waypoints if w.is_break]
                if breaks:
                    self.break_depth = breaks[0].offset.y

            if self.total_depth == 0:
                self.total_depth = max(w.offset.y for w in self.waypoints)

    def describe(self) -> str:
        """Human-readable description."""
        lines = [f"{self.name} ({self.route_type.value})"]
        lines.append(f"  Break at {self.break_depth:.0f} yards, total {self.total_depth:.0f} yards")
        lines.append(f"  Direction: {self.route_side}")
        lines.append("  Waypoints:")
        for i, wp in enumerate(self.waypoints):
            marker = " [BREAK]" if wp.is_break else ""
            ball = " (look for ball)" if wp.look_for_ball else ""
            lines.append(f"    {i+1}. {wp.offset} - {wp.phase.value}{marker}{ball}")
            if wp.description:
                lines.append(f"       {wp.description}")
        if self.timing_notes:
            lines.append(f"  Timing: {self.timing_notes}")
        return "\n".join(lines)

    def mirror(self) -> RouteDefinition:
        """Return mirrored route (flip X coordinates)."""
        mirrored_waypoints = [
            RouteWaypoint(
                offset=Vec2(-w.offset.x, w.offset.y),
                is_break=w.is_break,
                speed_factor=w.speed_factor,
                phase=w.phase,
                look_for_ball=w.look_for_ball,
                description=w.description,
            )
            for w in self.waypoints
        ]

        # Flip route side
        if self.route_side == "inside":
            new_side = "outside"
        elif self.route_side == "outside":
            new_side = "inside"
        else:
            new_side = self.route_side

        return RouteDefinition(
            name=self.name,
            route_type=self.route_type,
            waypoints=mirrored_waypoints,
            break_depth=self.break_depth,
            total_depth=self.total_depth,
            route_side=new_side,
            is_quick_route=self.is_quick_route,
            settles=self.settles,
            timing_notes=self.timing_notes,
        )


# =============================================================================
# Route Library
# =============================================================================

def _create_go() -> RouteDefinition:
    """Vertical/Go route - straight up the field."""
    return RouteDefinition(
        name="Go",
        route_type=RouteType.GO,
        waypoints=[
            RouteWaypoint(Vec2(0, 3), phase=RoutePhase.RELEASE, description="Release vertical"),
            RouteWaypoint(Vec2(0, 10), phase=RoutePhase.STEM, description="Stem vertical"),
            RouteWaypoint(Vec2(0, 20), is_break=False, phase=RoutePhase.POST_BREAK, look_for_ball=True, description="Look for ball"),
            RouteWaypoint(Vec2(0, 40), phase=RoutePhase.COMPLETE, description="Continue vertical"),
        ],
        route_side="vertical",
        timing_notes="Long-developing, need time",
    )


def _create_slant() -> RouteDefinition:
    """Slant - quick inside break."""
    return RouteDefinition(
        name="Slant",
        route_type=RouteType.SLANT,
        waypoints=[
            RouteWaypoint(Vec2(0, 1), phase=RoutePhase.RELEASE, description="Quick release"),
            RouteWaypoint(Vec2(0, 3), phase=RoutePhase.STEM, description="Threaten vertical"),
            RouteWaypoint(Vec2(4, 5), is_break=True, phase=RoutePhase.BREAK, look_for_ball=True, description="Break inside"),
            RouteWaypoint(Vec2(12, 10), phase=RoutePhase.POST_BREAK, description="Continue across"),
        ],
        route_side="inside",
        is_quick_route=True,
        timing_notes="Quick timing, 3-step drop",
    )


def _create_hitch() -> RouteDefinition:
    """Hitch/Hook - run 5 yards and turn back."""
    return RouteDefinition(
        name="Hitch",
        route_type=RouteType.HITCH,
        waypoints=[
            RouteWaypoint(Vec2(0, 2), phase=RoutePhase.RELEASE, description="Release"),
            RouteWaypoint(Vec2(0, 5), phase=RoutePhase.STEM, description="Drive to 5"),
            RouteWaypoint(Vec2(0, 5), is_break=True, speed_factor=0.0, phase=RoutePhase.BREAK, look_for_ball=True, description="Stop and turn"),
            RouteWaypoint(Vec2(0, 4), phase=RoutePhase.POST_BREAK, description="Settle back to ball"),
        ],
        route_side="vertical",
        is_quick_route=True,
        settles=True,  # Receiver stops at end of route
        timing_notes="Quick timing, turn at 5",
    )


def _create_curl() -> RouteDefinition:
    """Curl - deeper hitch with curl back."""
    return RouteDefinition(
        name="Curl",
        route_type=RouteType.CURL,
        waypoints=[
            RouteWaypoint(Vec2(0, 3), phase=RoutePhase.RELEASE, description="Release vertical"),
            RouteWaypoint(Vec2(0, 10), phase=RoutePhase.STEM, description="Stem to 10"),
            RouteWaypoint(Vec2(2, 12), is_break=True, phase=RoutePhase.BREAK, description="Curl back inside"),
            RouteWaypoint(Vec2(3, 10), speed_factor=0.3, phase=RoutePhase.POST_BREAK, look_for_ball=True, description="Settle in window"),
        ],
        route_side="inside",
        settles=True,  # Receiver stops at end of route
        timing_notes="Find soft spot in zone",
    )


def _create_out() -> RouteDefinition:
    """Out route - break to sideline."""
    return RouteDefinition(
        name="Out",
        route_type=RouteType.OUT,
        waypoints=[
            RouteWaypoint(Vec2(0, 3), phase=RoutePhase.RELEASE, description="Release vertical"),
            RouteWaypoint(Vec2(0, 10), phase=RoutePhase.STEM, description="Stem to depth"),
            RouteWaypoint(Vec2(-5, 12), is_break=True, phase=RoutePhase.BREAK, description="Hard out break"),
            RouteWaypoint(Vec2(-10, 12), phase=RoutePhase.POST_BREAK, look_for_ball=True, description="Toward sideline"),
        ],
        route_side="outside",
        timing_notes="Must sit in hole vs zone, run away vs man",
    )


def _create_in() -> RouteDefinition:
    """In/Dig route - break inside."""
    return RouteDefinition(
        name="In",
        route_type=RouteType.IN,
        waypoints=[
            RouteWaypoint(Vec2(0, 3), phase=RoutePhase.RELEASE, description="Release vertical"),
            RouteWaypoint(Vec2(0, 12), phase=RoutePhase.STEM, description="Stem to depth"),
            RouteWaypoint(Vec2(5, 12), is_break=True, phase=RoutePhase.BREAK, description="In break"),
            RouteWaypoint(Vec2(15, 12), phase=RoutePhase.POST_BREAK, look_for_ball=True, description="Cross the field"),
        ],
        route_side="inside",
        timing_notes="Cross face of linebackers",
    )


def _create_post() -> RouteDefinition:
    """Post route - break toward goalpost."""
    return RouteDefinition(
        name="Post",
        route_type=RouteType.POST,
        waypoints=[
            RouteWaypoint(Vec2(0, 3), phase=RoutePhase.RELEASE, description="Release"),
            RouteWaypoint(Vec2(0, 12), phase=RoutePhase.STEM, description="Stem vertical"),
            RouteWaypoint(Vec2(3, 15), is_break=True, phase=RoutePhase.BREAK, description="Post break"),
            RouteWaypoint(Vec2(8, 25), phase=RoutePhase.POST_BREAK, look_for_ball=True, description="Angle to post"),
            RouteWaypoint(Vec2(12, 35), phase=RoutePhase.COMPLETE, description="Continue to end zone"),
        ],
        route_side="inside",
        timing_notes="Big play, need protection",
    )


def _create_corner() -> RouteDefinition:
    """Corner route - break toward pylon."""
    return RouteDefinition(
        name="Corner",
        route_type=RouteType.CORNER,
        waypoints=[
            RouteWaypoint(Vec2(0, 3), phase=RoutePhase.RELEASE, description="Release"),
            RouteWaypoint(Vec2(0, 12), phase=RoutePhase.STEM, description="Stem vertical"),
            RouteWaypoint(Vec2(-3, 15), is_break=True, phase=RoutePhase.BREAK, description="Corner break"),
            RouteWaypoint(Vec2(-8, 22), phase=RoutePhase.POST_BREAK, look_for_ball=True, description="To corner"),
            RouteWaypoint(Vec2(-12, 30), phase=RoutePhase.COMPLETE, description="Fade to pylon"),
        ],
        route_side="outside",
        timing_notes="Throw before safety can close",
    )


def _create_comeback() -> RouteDefinition:
    """Comeback - deep stem, come back to sideline."""
    return RouteDefinition(
        name="Comeback",
        route_type=RouteType.COMEBACK,
        waypoints=[
            RouteWaypoint(Vec2(0, 3), phase=RoutePhase.RELEASE, description="Release"),
            RouteWaypoint(Vec2(0, 15), phase=RoutePhase.STEM, description="Push vertical"),
            RouteWaypoint(Vec2(-3, 16), is_break=True, phase=RoutePhase.BREAK, description="Plant and come back"),
            RouteWaypoint(Vec2(-5, 12), phase=RoutePhase.POST_BREAK, look_for_ball=True, description="Come back to ball"),
        ],
        route_side="outside",
        settles=True,  # Receiver stops at end of route
        timing_notes="Ball should be in air as receiver breaks",
    )


def _create_drag() -> RouteDefinition:
    """Drag - shallow cross."""
    return RouteDefinition(
        name="Drag",
        route_type=RouteType.DRAG,
        waypoints=[
            # Start angling toward break immediately - no straight release
            # This prevents the "shifty" direction change at waypoint 1
            RouteWaypoint(Vec2(3, 3), is_break=True, phase=RoutePhase.BREAK, description="Get to 3 yards"),
            RouteWaypoint(Vec2(10, 4), phase=RoutePhase.POST_BREAK, look_for_ball=True, description="Drag across"),
            RouteWaypoint(Vec2(20, 5), phase=RoutePhase.COMPLETE, description="Continue across"),
        ],
        route_side="inside",
        is_quick_route=True,
        timing_notes="Stay shallow, find holes in zone",
    )


def _create_flat() -> RouteDefinition:
    """Flat route - quick to flat area."""
    return RouteDefinition(
        name="Flat",
        route_type=RouteType.FLAT,
        waypoints=[
            RouteWaypoint(Vec2(-2, 1), phase=RoutePhase.RELEASE, description="Release outside"),
            RouteWaypoint(Vec2(-5, 2), is_break=True, phase=RoutePhase.BREAK, description="To flat"),
            RouteWaypoint(Vec2(-8, 2), phase=RoutePhase.POST_BREAK, look_for_ball=True, description="Settle in flat"),
        ],
        route_side="outside",
        is_quick_route=True,
        timing_notes="Get out quickly, expect ball fast",
    )


def _create_wheel() -> RouteDefinition:
    """Wheel route - out then up the sideline."""
    return RouteDefinition(
        name="Wheel",
        route_type=RouteType.WHEEL,
        waypoints=[
            RouteWaypoint(Vec2(0, 1), phase=RoutePhase.RELEASE, description="Release"),
            RouteWaypoint(Vec2(-4, 2), phase=RoutePhase.STEM, description="Swing to flat"),
            RouteWaypoint(Vec2(-6, 5), is_break=True, phase=RoutePhase.BREAK, description="Turn upfield"),
            RouteWaypoint(Vec2(-7, 15), phase=RoutePhase.POST_BREAK, look_for_ball=True, description="Up sideline"),
            RouteWaypoint(Vec2(-7, 30), phase=RoutePhase.COMPLETE, description="Continue vertical"),
        ],
        route_side="outside",
        timing_notes="Late-developing, often catches LB out of position",
    )


def _create_seam() -> RouteDefinition:
    """Seam route - up the hash."""
    return RouteDefinition(
        name="Seam",
        route_type=RouteType.SEAM,
        waypoints=[
            RouteWaypoint(Vec2(0, 3), phase=RoutePhase.RELEASE, description="Release"),
            RouteWaypoint(Vec2(0, 10), phase=RoutePhase.STEM, description="Press vertical"),
            RouteWaypoint(Vec2(0, 18), is_break=False, phase=RoutePhase.POST_BREAK, look_for_ball=True, description="Find hole in coverage"),
            RouteWaypoint(Vec2(0, 30), phase=RoutePhase.COMPLETE, description="Continue vertical"),
        ],
        route_side="vertical",
        timing_notes="Split safeties, find soft spot",
    )


# Pre-built route library
ROUTE_LIBRARY: dict[RouteType, RouteDefinition] = {
    RouteType.GO: _create_go(),
    RouteType.SLANT: _create_slant(),
    RouteType.HITCH: _create_hitch(),
    RouteType.CURL: _create_curl(),
    RouteType.OUT: _create_out(),
    RouteType.IN: _create_in(),
    RouteType.POST: _create_post(),
    RouteType.CORNER: _create_corner(),
    RouteType.COMEBACK: _create_comeback(),
    RouteType.DRAG: _create_drag(),
    RouteType.FLAT: _create_flat(),
    RouteType.WHEEL: _create_wheel(),
    RouteType.SEAM: _create_seam(),
}


def get_route(route_type: RouteType) -> RouteDefinition:
    """Get a route definition from the library."""
    return ROUTE_LIBRARY.get(route_type, ROUTE_LIBRARY[RouteType.HITCH])
