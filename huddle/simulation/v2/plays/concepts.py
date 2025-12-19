"""Play concepts - coordinated route combinations.

A concept is a pass play design that coordinates multiple receivers
to attack specific coverages. Each concept has:
- A name and description
- Receiver alignments (formation)
- Route assignments for each receiver
- Coverage beaters (what defenses it's designed to beat)
- Read progression for the QB
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict

from .routes import RouteType, RouteDefinition, ROUTE_LIBRARY


class Formation(str, Enum):
    """Offensive formations."""
    # Standard formations
    SINGLEBACK = "singleback"          # 1 RB, 1 TE, 3 WR
    SHOTGUN = "shotgun"                # QB in shotgun, 1 RB
    EMPTY = "empty"                    # No RB, 5 receivers
    I_FORM = "i_form"                  # FB + RB stacked

    # Spread formations
    TRIPS_RIGHT = "trips_right"        # 3 WR to right
    TRIPS_LEFT = "trips_left"          # 3 WR to left
    BUNCH_RIGHT = "bunch_right"        # 3 WR bunched right
    BUNCH_LEFT = "bunch_left"          # 3 WR bunched left

    # Heavy formations
    GOAL_LINE = "goal_line"            # Heavy set
    JUMBO = "jumbo"                    # Extra OL


class ReceiverPosition(str, Enum):
    """Standard receiver position labels."""
    X = "x"           # Split end (usually left, on LOS)
    Z = "z"           # Flanker (usually right, off LOS)
    SLOT_L = "slot_l" # Left slot
    SLOT_R = "slot_r" # Right slot
    Y = "y"           # Tight end
    RB = "rb"         # Running back (can release on routes)
    FB = "fb"         # Fullback


@dataclass
class ReceiverAlignment:
    """Where a receiver lines up pre-snap.

    Coordinates are in yards from center (x) and LOS (y).
    Positive x = right side of formation.
    Negative x = left side of formation.
    y = 0 is line of scrimmage.
    """
    position: ReceiverPosition
    x: float  # Yards from center (negative = left)
    y: float  # Yards from LOS (usually 0 or slightly back)
    on_line: bool = True  # On the line of scrimmage?

    @property
    def is_left_side(self) -> bool:
        return self.x < 0


@dataclass
class RouteAssignment:
    """A receiver's route assignment in a play.

    Attributes:
        position: Which receiver position this is for
        route_type: What route to run
        hot_route: Is this a hot route (quick throw vs blitz)?
        read_order: QB's read progression (1 = first read)
        coverage_key: What coverage makes this the primary read
    """
    position: ReceiverPosition
    route_type: RouteType
    hot_route: bool = False
    read_order: int = 1
    coverage_key: Optional[str] = None  # e.g., "cover_2", "man", "zone"

    def get_route(self) -> RouteDefinition:
        """Get the route definition for this assignment."""
        return ROUTE_LIBRARY.get(self.route_type, ROUTE_LIBRARY[RouteType.HITCH])


@dataclass
class PlayConcept:
    """A complete pass play concept.

    Attributes:
        name: Play name (e.g., "Mesh", "Four Verts")
        description: What the play does and how it attacks defenses
        formation: Base formation
        alignments: Where each receiver lines up
        routes: Route assignments for each receiver
        coverage_beaters: What coverages this play is good against
        timing: Quick (1-3 step), intermediate (5 step), deep (7 step)
    """
    name: str
    description: str
    formation: Formation
    alignments: List[ReceiverAlignment]
    routes: List[RouteAssignment]
    coverage_beaters: List[str] = field(default_factory=list)
    timing: str = "intermediate"  # quick, intermediate, deep

    def get_alignment(self, position: ReceiverPosition) -> Optional[ReceiverAlignment]:
        """Get alignment for a specific position."""
        for align in self.alignments:
            if align.position == position:
                return align
        return None

    def get_route_assignment(self, position: ReceiverPosition) -> Optional[RouteAssignment]:
        """Get route assignment for a specific position."""
        for route in self.routes:
            if route.position == position:
                return route
        return None

    def describe(self) -> str:
        """Human-readable play description."""
        lines = [
            f"=== {self.name} ===",
            f"Formation: {self.formation.value}",
            f"Timing: {self.timing}",
            f"Beats: {', '.join(self.coverage_beaters)}",
            "",
            "Routes:",
        ]
        for route in sorted(self.routes, key=lambda r: r.read_order):
            hot = " [HOT]" if route.hot_route else ""
            lines.append(f"  {route.read_order}. {route.position.value}: {route.route_type.value}{hot}")

        lines.append("")
        lines.append(f"Description: {self.description}")
        return "\n".join(lines)


# =============================================================================
# Standard Alignments (reusable)
# =============================================================================

def _trips_right_alignments() -> List[ReceiverAlignment]:
    """Trips formation to the right."""
    return [
        ReceiverAlignment(ReceiverPosition.X, x=-25, y=0, on_line=True),   # X split left
        ReceiverAlignment(ReceiverPosition.SLOT_R, x=8, y=-1, on_line=False),  # Inside slot
        ReceiverAlignment(ReceiverPosition.Z, x=15, y=-1, on_line=False),      # Middle slot
        ReceiverAlignment(ReceiverPosition.Y, x=22, y=0, on_line=True),        # Outside
    ]

def _spread_alignments() -> List[ReceiverAlignment]:
    """2x2 spread formation."""
    return [
        ReceiverAlignment(ReceiverPosition.X, x=-25, y=0, on_line=True),       # X far left
        ReceiverAlignment(ReceiverPosition.SLOT_L, x=-8, y=-1, on_line=False), # Left slot
        ReceiverAlignment(ReceiverPosition.SLOT_R, x=8, y=-1, on_line=False),  # Right slot
        ReceiverAlignment(ReceiverPosition.Z, x=25, y=0, on_line=True),        # Z far right
    ]

def _bunch_right_alignments() -> List[ReceiverAlignment]:
    """Bunch formation to the right."""
    return [
        ReceiverAlignment(ReceiverPosition.X, x=-25, y=0, on_line=True),   # X split left
        ReceiverAlignment(ReceiverPosition.Y, x=6, y=0, on_line=True),     # Point (on line)
        ReceiverAlignment(ReceiverPosition.SLOT_R, x=8, y=-2, on_line=False),  # Wing
        ReceiverAlignment(ReceiverPosition.Z, x=10, y=-1, on_line=False),      # Back
    ]


# =============================================================================
# Play Concepts Library
# =============================================================================

def create_four_verts() -> PlayConcept:
    """Four Verticals - attack deep zones with 4 go routes.

    Classic Cover 2 beater. Forces safeties to choose which
    receiver to help on. Slot receivers split the safeties.
    """
    return PlayConcept(
        name="Four Verts",
        description="Four receivers run vertical routes, stressing deep coverage. "
                    "Outside receivers run go routes, slots run seams between safeties. "
                    "QB reads safety leverage - throw away from help.",
        formation=Formation.SHOTGUN,
        alignments=_spread_alignments(),
        routes=[
            RouteAssignment(ReceiverPosition.X, RouteType.GO, read_order=2),
            RouteAssignment(ReceiverPosition.SLOT_L, RouteType.SEAM, read_order=1,
                          coverage_key="cover_2"),
            RouteAssignment(ReceiverPosition.SLOT_R, RouteType.SEAM, read_order=1,
                          coverage_key="cover_2"),
            RouteAssignment(ReceiverPosition.Z, RouteType.GO, read_order=2),
        ],
        coverage_beaters=["cover_2", "cover_4"],
        timing="deep",
    )


def create_mesh() -> PlayConcept:
    """Mesh Concept - crossing routes create natural picks.

    Two receivers run shallow crossing routes in opposite directions,
    creating a "rub" or pick that's hard to cover in man coverage.
    """
    return PlayConcept(
        name="Mesh",
        description="Two receivers cross underneath at 5-6 yards, creating picks "
                    "against man coverage. Outside receivers run clear-out routes. "
                    "QB reads inside-out: mesh crossers first, then corners.",
        formation=Formation.SHOTGUN,
        alignments=_spread_alignments(),
        routes=[
            RouteAssignment(ReceiverPosition.X, RouteType.CORNER, read_order=3),
            RouteAssignment(ReceiverPosition.SLOT_L, RouteType.DRAG, read_order=1,
                          hot_route=True, coverage_key="man"),
            RouteAssignment(ReceiverPosition.SLOT_R, RouteType.DRAG, read_order=2,
                          hot_route=True, coverage_key="man"),
            RouteAssignment(ReceiverPosition.Z, RouteType.CORNER, read_order=3),
        ],
        coverage_beaters=["man", "cover_0", "cover_1"],
        timing="quick",
    )


def create_smash() -> PlayConcept:
    """Smash Concept - high-low the corner.

    Outside receiver runs a hitch, inside receiver runs a corner route.
    Creates a high-low read on the corner defender.
    """
    return PlayConcept(
        name="Smash",
        description="Corner route over a hitch creates high-low read on the CB. "
                    "If CB sits on hitch, throw corner. If CB bails, throw hitch. "
                    "Great against Cover 2 and Cover 4.",
        formation=Formation.SHOTGUN,
        alignments=_spread_alignments(),
        routes=[
            RouteAssignment(ReceiverPosition.X, RouteType.HITCH, read_order=2),
            RouteAssignment(ReceiverPosition.SLOT_L, RouteType.CORNER, read_order=1,
                          coverage_key="cover_2"),
            RouteAssignment(ReceiverPosition.SLOT_R, RouteType.CORNER, read_order=1,
                          coverage_key="cover_2"),
            RouteAssignment(ReceiverPosition.Z, RouteType.HITCH, read_order=2),
        ],
        coverage_beaters=["cover_2", "cover_4"],
        timing="intermediate",
    )


def create_flood() -> PlayConcept:
    """Flood Concept - overload one side with 3 receivers.

    Three receivers to one side at different depths (flat, intermediate, deep)
    to stress zone coverage horizontally.
    """
    return PlayConcept(
        name="Flood",
        description="Three-level flood to one side: flat, out, and corner routes. "
                    "Stresses zone coverage by putting 3 receivers into 2 zones. "
                    "QB reads high to low based on safety rotation.",
        formation=Formation.TRIPS_RIGHT,
        alignments=_trips_right_alignments(),
        routes=[
            RouteAssignment(ReceiverPosition.X, RouteType.POST, read_order=4),  # Backside clear
            RouteAssignment(ReceiverPosition.SLOT_R, RouteType.FLAT, read_order=3, hot_route=True),
            RouteAssignment(ReceiverPosition.Z, RouteType.OUT, read_order=2),
            RouteAssignment(ReceiverPosition.Y, RouteType.CORNER, read_order=1,
                          coverage_key="cover_3"),
        ],
        coverage_beaters=["cover_3", "cover_1"],
        timing="intermediate",
    )


def create_stick() -> PlayConcept:
    """Stick Concept - quick 3-level read.

    Simple quick-game concept with flat, stick (6yd hitch), and corner.
    Fast developing, good against zone and man.
    """
    return PlayConcept(
        name="Stick",
        description="Quick 3-step concept: flat for quick outlet, stick route at 6 yards, "
                    "corner route deep. Read flat defender - if he widens, throw stick. "
                    "If he sits, throw flat.",
        formation=Formation.SHOTGUN,
        alignments=_spread_alignments(),
        routes=[
            RouteAssignment(ReceiverPosition.X, RouteType.SLANT, read_order=3),
            RouteAssignment(ReceiverPosition.SLOT_L, RouteType.HITCH, read_order=1,
                          coverage_key="zone"),  # The "stick"
            RouteAssignment(ReceiverPosition.SLOT_R, RouteType.FLAT, read_order=2, hot_route=True),
            RouteAssignment(ReceiverPosition.Z, RouteType.CORNER, read_order=4),
        ],
        coverage_beaters=["cover_3", "cover_2", "zone"],
        timing="quick",
    )


def create_slant_flat() -> PlayConcept:
    """Slant-Flat - simple two-man concept.

    Quick slant with a flat route underneath. Creates horizontal stress
    on the flat defender.
    """
    return PlayConcept(
        name="Slant-Flat",
        description="Quick slant with flat route creates a simple 2-man horizontal stretch. "
                    "Read the flat defender: if he widens to flat, throw slant. "
                    "If he jumps slant, throw flat.",
        formation=Formation.SHOTGUN,
        alignments=_spread_alignments(),
        routes=[
            RouteAssignment(ReceiverPosition.X, RouteType.GO, read_order=4),  # Clear out
            RouteAssignment(ReceiverPosition.SLOT_L, RouteType.SLANT, read_order=1, hot_route=True),
            RouteAssignment(ReceiverPosition.SLOT_R, RouteType.FLAT, read_order=2, hot_route=True),
            RouteAssignment(ReceiverPosition.Z, RouteType.GO, read_order=4),  # Clear out
        ],
        coverage_beaters=["cover_3", "cover_2", "man"],
        timing="quick",
    )


def create_curl_flat() -> PlayConcept:
    """Curl-Flat - intermediate timing concept.

    Curl route at 10-12 yards with flat underneath. Similar read to slant-flat
    but deeper developing.
    """
    return PlayConcept(
        name="Curl-Flat",
        description="Outside receiver runs curl at 12 yards, inside runs flat. "
                    "Creates the same horizontal stretch as slant-flat but deeper. "
                    "Good against soft zones.",
        formation=Formation.SHOTGUN,
        alignments=_spread_alignments(),
        routes=[
            RouteAssignment(ReceiverPosition.X, RouteType.CURL, read_order=1),
            RouteAssignment(ReceiverPosition.SLOT_L, RouteType.FLAT, read_order=2, hot_route=True),
            RouteAssignment(ReceiverPosition.SLOT_R, RouteType.FLAT, read_order=2, hot_route=True),
            RouteAssignment(ReceiverPosition.Z, RouteType.CURL, read_order=1),
        ],
        coverage_beaters=["cover_3", "zone"],
        timing="intermediate",
    )


def create_post_wheel() -> PlayConcept:
    """Post-Wheel - deep shot concept.

    Deep post inside, wheel route outside. Attacks Cover 3 by
    putting the safety in conflict.
    """
    return PlayConcept(
        name="Post-Wheel",
        description="Deep post inside with wheel route outside. Single-high safety "
                    "must choose which route to help on. RB or slot runs wheel, "
                    "X receiver runs post.",
        formation=Formation.SHOTGUN,
        alignments=_spread_alignments(),
        routes=[
            RouteAssignment(ReceiverPosition.X, RouteType.POST, read_order=1,
                          coverage_key="cover_3"),
            RouteAssignment(ReceiverPosition.SLOT_L, RouteType.DRAG, read_order=3),
            RouteAssignment(ReceiverPosition.SLOT_R, RouteType.WHEEL, read_order=2,
                          coverage_key="cover_3"),
            RouteAssignment(ReceiverPosition.Z, RouteType.GO, read_order=4),
        ],
        coverage_beaters=["cover_3", "cover_1"],
        timing="deep",
    )


def create_drive() -> PlayConcept:
    """Drive Concept - crossing routes at different levels.

    Dig (in) route at 12-15 yards with drag underneath at 5 yards.
    Creates vertical stretch on zone defenders.
    """
    return PlayConcept(
        name="Drive",
        description="In route at 12-15 yards with shallow drag underneath. "
                    "Vertical stretch on hook/curl defenders. Read high to low: "
                    "if underneath coverage opens, hit the dig. If closed, check drag.",
        formation=Formation.SHOTGUN,
        alignments=_spread_alignments(),
        routes=[
            RouteAssignment(ReceiverPosition.X, RouteType.IN, read_order=1),  # The dig
            RouteAssignment(ReceiverPosition.SLOT_L, RouteType.DRAG, read_order=2, hot_route=True),
            RouteAssignment(ReceiverPosition.SLOT_R, RouteType.FLAT, read_order=3),
            RouteAssignment(ReceiverPosition.Z, RouteType.CURL, read_order=4),
        ],
        coverage_beaters=["cover_2", "cover_3", "zone"],
        timing="intermediate",
    )


def create_spacing() -> PlayConcept:
    """Spacing Concept - 5 receivers spread horizontally.

    All receivers at the same depth (~5 yards), spread across the field.
    Impossible to cover all 5 gaps in zone.
    """
    return PlayConcept(
        name="Spacing",
        description="Five receivers at 5-6 yards spread horizontally across the field. "
                    "Creates impossible coverage math for zone - more receivers than defenders. "
                    "QB reads where the void is and delivers quickly.",
        formation=Formation.EMPTY,
        alignments=[
            ReceiverAlignment(ReceiverPosition.X, x=-25, y=0, on_line=True),
            ReceiverAlignment(ReceiverPosition.SLOT_L, x=-10, y=-1, on_line=False),
            ReceiverAlignment(ReceiverPosition.Y, x=0, y=-1, on_line=False),  # Center
            ReceiverAlignment(ReceiverPosition.SLOT_R, x=10, y=-1, on_line=False),
            ReceiverAlignment(ReceiverPosition.Z, x=25, y=0, on_line=True),
        ],
        routes=[
            RouteAssignment(ReceiverPosition.X, RouteType.HITCH, read_order=3),
            RouteAssignment(ReceiverPosition.SLOT_L, RouteType.HITCH, read_order=2),
            RouteAssignment(ReceiverPosition.Y, RouteType.HITCH, read_order=1),  # Center of field
            RouteAssignment(ReceiverPosition.SLOT_R, RouteType.HITCH, read_order=2),
            RouteAssignment(ReceiverPosition.Z, RouteType.HITCH, read_order=3),
        ],
        coverage_beaters=["zone", "cover_2", "cover_3"],
        timing="quick",
    )


# =============================================================================
# Concept Library
# =============================================================================

CONCEPT_LIBRARY: Dict[str, PlayConcept] = {
    "four_verts": create_four_verts(),
    "mesh": create_mesh(),
    "smash": create_smash(),
    "flood": create_flood(),
    "stick": create_stick(),
    "slant_flat": create_slant_flat(),
    "curl_flat": create_curl_flat(),
    "post_wheel": create_post_wheel(),
    "drive": create_drive(),
    "spacing": create_spacing(),
}


def get_concept(name: str) -> Optional[PlayConcept]:
    """Get a play concept by name."""
    return CONCEPT_LIBRARY.get(name.lower())


def list_concepts() -> List[str]:
    """List all available concept names."""
    return list(CONCEPT_LIBRARY.keys())


def concepts_for_coverage(coverage: str) -> List[PlayConcept]:
    """Get concepts that beat a specific coverage."""
    coverage = coverage.lower()
    return [c for c in CONCEPT_LIBRARY.values() if coverage in c.coverage_beaters]
