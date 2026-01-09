"""Run play concepts - coordinated running plays.

A run concept defines:
- Formation and personnel
- Blocking scheme (zone, gap/power, counter)
- Ball carrier path and aiming point
- Assignments for each position
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict

from ..core.vec2 import Vec2


class RunScheme(str, Enum):
    """Type of run blocking scheme."""
    INSIDE_ZONE = "inside_zone"   # Zone steps, combo to backside
    OUTSIDE_ZONE = "outside_zone"  # Stretch, reach blocks
    POWER = "power"               # Gap scheme, pulling guard
    COUNTER = "counter"           # Misdirection, pulling linemen
    DIVE = "dive"                 # Quick hitting A/B gap
    DRAW = "draw"                 # Delayed handoff, pass set first
    TRAP = "trap"                 # Pull and kick out defender
    TOSS = "toss"                 # Pitch to outside


class Gap(str, Enum):
    """Gaps in the offensive line."""
    # Left side
    C_LEFT = "c_left"     # Outside left tackle
    B_LEFT = "b_left"     # Between LT and LG
    A_LEFT = "a_left"     # Between LG and C

    # Right side
    A_RIGHT = "a_right"   # Between C and RG
    B_RIGHT = "b_right"   # Between RG and RT
    C_RIGHT = "c_right"   # Outside right tackle


class BlockAssignment(str, Enum):
    """Types of blocking assignments."""
    # Zone blocking
    ZONE_STEP = "zone_step"       # Take lateral step, block playside
    COMBO = "combo"               # Double team DL, one climbs to LB
    REACH = "reach"               # Reach block playside defender
    CUTOFF = "cutoff"             # Cut off backside pursuit

    # Gap/Power blocking
    DOWN = "down"                 # Block down on inside defender
    KICK_OUT = "kick_out"         # Kick out end man on LOS
    PULL_LEAD = "pull_lead"       # Pull and lead through hole
    PULL_WRAP = "pull_wrap"       # Pull and wrap around

    # Other
    PASS_SET = "pass_set"         # Fake pass protection (draw)
    CLIMB = "climb"               # Release to second level
    BASE = "base"                 # Base man-on-man block


@dataclass
class OLAssignment:
    """Blocking assignment for an offensive lineman."""
    position: str              # LT, LG, C, RG, RT
    assignment: BlockAssignment
    target_gap: Optional[Gap] = None
    combo_partner: Optional[str] = None  # Position to combo with
    climb_to: Optional[str] = None       # LB to climb to (MIKE, WILL, SAM)
    pull_direction: Optional[str] = None  # "left" or "right"


@dataclass
class BackfieldAssignment:
    """Assignment for a backfield player (RB, FB)."""
    position: str              # RB, FB
    role: str                  # "ball_carrier", "lead_blocker", "fake", "pass_pro"
    path: List[Vec2] = field(default_factory=list)  # Waypoints relative to snap
    aiming_point: Optional[Gap] = None


@dataclass
class RunConcept:
    """A complete run play concept."""
    name: str
    description: str
    scheme: RunScheme
    play_side: str             # "left", "right", or "balanced"
    aiming_point: Gap          # Initial target gap

    # Assignments
    ol_assignments: List[OLAssignment]
    backfield_assignments: List[BackfieldAssignment]

    # Timing
    mesh_depth: float = 4.0    # Yards behind LOS for handoff
    handoff_timing: float = 0.6  # Seconds after snap

    # Read keys (for option plays)
    read_key: Optional[str] = None  # Defender to read for option

    def get_ol_assignment(self, position: str) -> Optional[OLAssignment]:
        """Get assignment for an OL position."""
        for assign in self.ol_assignments:
            if assign.position == position:
                return assign
        return None

    def get_backfield_assignment(self, position: str) -> Optional[BackfieldAssignment]:
        """Get assignment for a backfield position."""
        for assign in self.backfield_assignments:
            if assign.position == position:
                return assign
        return None


# =============================================================================
# Run Concept Definitions
# =============================================================================

def create_inside_zone_right() -> RunConcept:
    """Inside Zone Right - base zone run to the right.

    OL takes zone steps right, creates combo blocks on DL,
    climbs to linebackers. RB reads the blocks and finds the hole.
    """
    return RunConcept(
        name="Inside Zone Right",
        description="Base inside zone to the right. OL zone steps playside, "
                    "combos to 2nd level. RB reads front side A gap, can bend "
                    "backside if front fills.",
        scheme=RunScheme.INSIDE_ZONE,
        play_side="right",
        aiming_point=Gap.A_RIGHT,
        ol_assignments=[
            OLAssignment("LT", BlockAssignment.CUTOFF),
            OLAssignment("LG", BlockAssignment.COMBO, combo_partner="C", climb_to="MIKE"),
            OLAssignment("C", BlockAssignment.COMBO, combo_partner="LG"),
            OLAssignment("RG", BlockAssignment.ZONE_STEP, target_gap=Gap.A_RIGHT),
            OLAssignment("RT", BlockAssignment.ZONE_STEP, target_gap=Gap.B_RIGHT),
        ],
        backfield_assignments=[
            BackfieldAssignment(
                "RB",
                role="ball_carrier",
                # RB starts at (-0.5, -4.5), path goes toward A gap (x ≈ 0.75)
                path=[Vec2(0, -3), Vec2(0.5, -1), Vec2(1, 2)],
                aiming_point=Gap.A_RIGHT,
            ),
        ],
        mesh_depth=3.5,
        handoff_timing=0.4,
    )


def create_inside_zone_left() -> RunConcept:
    """Inside Zone Left - mirror of inside zone right."""
    return RunConcept(
        name="Inside Zone Left",
        description="Base inside zone to the left. OL zone steps playside, "
                    "combos to 2nd level. RB reads front side A gap.",
        scheme=RunScheme.INSIDE_ZONE,
        play_side="left",
        aiming_point=Gap.A_LEFT,
        ol_assignments=[
            OLAssignment("LT", BlockAssignment.ZONE_STEP, target_gap=Gap.B_LEFT),
            OLAssignment("LG", BlockAssignment.ZONE_STEP, target_gap=Gap.A_LEFT),
            OLAssignment("C", BlockAssignment.COMBO, combo_partner="RG"),
            OLAssignment("RG", BlockAssignment.COMBO, combo_partner="C", climb_to="MIKE"),
            OLAssignment("RT", BlockAssignment.CUTOFF),
        ],
        backfield_assignments=[
            BackfieldAssignment(
                "RB",
                role="ball_carrier",
                # RB starts at (-0.5, -4.5), path goes toward A gap left (x ≈ -0.75)
                path=[Vec2(-0.5, -3), Vec2(-1, -1), Vec2(-1.5, 2)],
                aiming_point=Gap.A_LEFT,
            ),
        ],
        mesh_depth=3.5,
        handoff_timing=0.4,
    )


def create_outside_zone_right() -> RunConcept:
    """Outside Zone Right (Stretch) - get to the edge.

    OL reach blocks to stretch the defense horizontally.
    RB aims for C gap but can cut back if defense overflows.
    """
    return RunConcept(
        name="Outside Zone Right",
        description="Stretch play to the right. OL reach blocks, trying to "
                    "get to outside shoulder. RB presses C gap, can cut back "
                    "if defense overruns.",
        scheme=RunScheme.OUTSIDE_ZONE,
        play_side="right",
        aiming_point=Gap.C_RIGHT,
        ol_assignments=[
            OLAssignment("LT", BlockAssignment.CUTOFF),
            OLAssignment("LG", BlockAssignment.CUTOFF),
            OLAssignment("C", BlockAssignment.REACH),
            OLAssignment("RG", BlockAssignment.REACH),
            OLAssignment("RT", BlockAssignment.REACH, target_gap=Gap.C_RIGHT),
        ],
        backfield_assignments=[
            BackfieldAssignment(
                "RB",
                role="ball_carrier",
                # Stretch to C gap right (x ≈ 3.5), tight spacing
                path=[Vec2(1, -3), Vec2(2.5, -1), Vec2(4, 1), Vec2(5, 3)],
                aiming_point=Gap.C_RIGHT,
            ),
        ],
        mesh_depth=3.5,
        handoff_timing=0.5,
    )


def create_outside_zone_left() -> RunConcept:
    """Outside Zone Left (Stretch) - mirror."""
    return RunConcept(
        name="Outside Zone Left",
        description="Stretch play to the left. OL reach blocks, RB presses "
                    "C gap, can cut back.",
        scheme=RunScheme.OUTSIDE_ZONE,
        play_side="left",
        aiming_point=Gap.C_LEFT,
        ol_assignments=[
            OLAssignment("LT", BlockAssignment.REACH, target_gap=Gap.C_LEFT),
            OLAssignment("LG", BlockAssignment.REACH),
            OLAssignment("C", BlockAssignment.REACH),
            OLAssignment("RG", BlockAssignment.CUTOFF),
            OLAssignment("RT", BlockAssignment.CUTOFF),
        ],
        backfield_assignments=[
            BackfieldAssignment(
                "RB",
                role="ball_carrier",
                # Stretch to C gap left (x ≈ -3.5), tight spacing
                path=[Vec2(-1, -3), Vec2(-2.5, -1), Vec2(-4, 1), Vec2(-5, 3)],
                aiming_point=Gap.C_LEFT,
            ),
        ],
        mesh_depth=3.5,
        handoff_timing=0.5,
    )


def create_power_right() -> RunConcept:
    """Power Right - gap scheme with pulling guard.

    Playside OL blocks down, backside guard pulls to kick out
    the end man on LOS (EMOL). FB leads through the hole.
    """
    return RunConcept(
        name="Power Right",
        description="Gap scheme to the right. Playside OL blocks down, "
                    "backside guard pulls to kick out EMOL. FB leads through B gap. "
                    "Physical, downhill run.",
        scheme=RunScheme.POWER,
        play_side="right",
        aiming_point=Gap.B_RIGHT,
        ol_assignments=[
            OLAssignment("LT", BlockAssignment.CUTOFF),
            OLAssignment("LG", BlockAssignment.PULL_LEAD, pull_direction="right"),
            OLAssignment("C", BlockAssignment.BASE),
            OLAssignment("RG", BlockAssignment.DOWN),
            OLAssignment("RT", BlockAssignment.DOWN),
        ],
        backfield_assignments=[
            BackfieldAssignment(
                "FB",
                role="lead_blocker",
                # FB at (0.5, -3), leads to B gap right (x ≈ 2.25)
                path=[Vec2(1.5, -1.5), Vec2(2, 0), Vec2(2.5, 2)],
                aiming_point=Gap.B_RIGHT,
            ),
            BackfieldAssignment(
                "RB",
                role="ball_carrier",
                # RB at (-0.5, -4.5), follows FB through B gap
                path=[Vec2(0, -3), Vec2(1.5, -1), Vec2(2.5, 1)],
                aiming_point=Gap.B_RIGHT,
            ),
        ],
        mesh_depth=3.5,
        handoff_timing=0.5,
    )


def create_power_left() -> RunConcept:
    """Power Left - mirror of power right."""
    return RunConcept(
        name="Power Left",
        description="Gap scheme to the left. Backside guard pulls to kick out.",
        scheme=RunScheme.POWER,
        play_side="left",
        aiming_point=Gap.B_LEFT,
        ol_assignments=[
            OLAssignment("LT", BlockAssignment.DOWN),
            OLAssignment("LG", BlockAssignment.DOWN),
            OLAssignment("C", BlockAssignment.BASE),
            OLAssignment("RG", BlockAssignment.PULL_LEAD, pull_direction="left"),
            OLAssignment("RT", BlockAssignment.CUTOFF),
        ],
        backfield_assignments=[
            BackfieldAssignment(
                "FB",
                role="lead_blocker",
                # FB leads to B gap left (x ≈ -2.25)
                path=[Vec2(-1.5, -1.5), Vec2(-2, 0), Vec2(-2.5, 2)],
                aiming_point=Gap.B_LEFT,
            ),
            BackfieldAssignment(
                "RB",
                role="ball_carrier",
                # RB follows FB through B gap left
                path=[Vec2(-0.5, -3), Vec2(-1.5, -1), Vec2(-2.5, 1)],
                aiming_point=Gap.B_LEFT,
            ),
        ],
        mesh_depth=3.5,
        handoff_timing=0.5,
    )


def create_counter_right() -> RunConcept:
    """Counter Right - misdirection run.

    RB takes initial step left (counter step), then cuts back right.
    Backside guard and tackle pull to the play side.
    """
    return RunConcept(
        name="Counter Right",
        description="Misdirection to the right. RB counter steps left, then "
                    "cuts back right. Backside guard pulls to kick out, "
                    "backside tackle pulls to lead. Slow developing but explosive.",
        scheme=RunScheme.COUNTER,
        play_side="right",
        aiming_point=Gap.B_RIGHT,
        ol_assignments=[
            OLAssignment("LT", BlockAssignment.PULL_WRAP, pull_direction="right"),
            OLAssignment("LG", BlockAssignment.PULL_LEAD, pull_direction="right"),
            OLAssignment("C", BlockAssignment.BASE),
            OLAssignment("RG", BlockAssignment.DOWN),
            OLAssignment("RT", BlockAssignment.DOWN),
        ],
        backfield_assignments=[
            BackfieldAssignment(
                "RB",
                role="ball_carrier",
                # Counter step left, then cut back right to B gap (x ≈ 2.25)
                path=[Vec2(-1, -3.5), Vec2(-1, -3), Vec2(1.5, -1), Vec2(2.5, 1)],
                aiming_point=Gap.B_RIGHT,
            ),
        ],
        mesh_depth=4.0,
        handoff_timing=0.6,
    )


def create_dive_right() -> RunConcept:
    """Dive Right - quick hitting A gap run.

    Fast handoff, RB hits the hole immediately. OL fires off the ball.
    Good short yardage play.
    """
    return RunConcept(
        name="Dive Right",
        description="Quick hitting dive to the A gap. Fast mesh, RB hits "
                    "the hole immediately. Good for short yardage.",
        scheme=RunScheme.DIVE,
        play_side="right",
        aiming_point=Gap.A_RIGHT,
        ol_assignments=[
            OLAssignment("LT", BlockAssignment.BASE),
            OLAssignment("LG", BlockAssignment.BASE),
            OLAssignment("C", BlockAssignment.COMBO, combo_partner="RG"),
            OLAssignment("RG", BlockAssignment.COMBO, combo_partner="C"),
            OLAssignment("RT", BlockAssignment.BASE),
        ],
        backfield_assignments=[
            BackfieldAssignment(
                "RB",
                role="ball_carrier",
                # Quick dive to A gap right (x ≈ 0.75)
                path=[Vec2(0.5, -2), Vec2(0.75, 0), Vec2(1, 3)],
                aiming_point=Gap.A_RIGHT,
            ),
        ],
        mesh_depth=2.5,  # Short mesh for quick hitter
        handoff_timing=0.3,  # Quick handoff
    )


def create_draw() -> RunConcept:
    """Draw - delayed handoff after pass setup.

    OL pass sets initially, then transitions to run blocking.
    RB waits, then takes delayed handoff. Catches defense in pass rush.
    """
    return RunConcept(
        name="Draw",
        description="Delayed run. OL shows pass protection, then blocks. "
                    "RB waits for defense to commit to pass rush before "
                    "taking handoff. Good against aggressive pass rushers.",
        scheme=RunScheme.DRAW,
        play_side="balanced",
        aiming_point=Gap.A_RIGHT,
        ol_assignments=[
            OLAssignment("LT", BlockAssignment.PASS_SET),  # Pass set first
            OLAssignment("LG", BlockAssignment.PASS_SET),
            OLAssignment("C", BlockAssignment.PASS_SET),
            OLAssignment("RG", BlockAssignment.PASS_SET),
            OLAssignment("RT", BlockAssignment.PASS_SET),
        ],
        backfield_assignments=[
            BackfieldAssignment(
                "RB",
                role="ball_carrier",
                # RB at (-0.5, -4.5), shows pass pro then takes delayed handoff
                path=[Vec2(-0.5, -4), Vec2(0, -3), Vec2(0.5, -1), Vec2(0.75, 2)],
                aiming_point=Gap.A_RIGHT,
            ),
        ],
        mesh_depth=4.0,
        handoff_timing=0.9,  # Delayed
    )


def create_toss_right() -> RunConcept:
    """Toss Right - pitch to the outside.

    QB pitches to RB heading to the perimeter. OL pulls to lead.
    Designed to get outside quickly.
    """
    return RunConcept(
        name="Toss Right",
        description="Pitch play to the outside. RB catches pitch heading "
                    "toward sideline. Pulling linemen lead the way. "
                    "Speed play to get the edge.",
        scheme=RunScheme.TOSS,
        play_side="right",
        aiming_point=Gap.C_RIGHT,
        ol_assignments=[
            OLAssignment("LT", BlockAssignment.CUTOFF),
            OLAssignment("LG", BlockAssignment.PULL_LEAD, pull_direction="right"),
            OLAssignment("C", BlockAssignment.PULL_LEAD, pull_direction="right"),
            OLAssignment("RG", BlockAssignment.REACH),
            OLAssignment("RT", BlockAssignment.REACH),
        ],
        backfield_assignments=[
            BackfieldAssignment(
                "RB",
                role="ball_carrier",
                # RB at (-0.5, -4.5), catches pitch heading to edge (past RT at x=3)
                path=[Vec2(2, -3), Vec2(4, -1), Vec2(5.5, 1), Vec2(7, 4)],
                aiming_point=Gap.C_RIGHT,
            ),
        ],
        mesh_depth=4.0,
        handoff_timing=0.3,  # Quick pitch
    )


# =============================================================================
# Run Concept Library
# =============================================================================

RUN_CONCEPT_LIBRARY: Dict[str, RunConcept] = {
    "inside_zone_right": create_inside_zone_right(),
    "inside_zone_left": create_inside_zone_left(),
    "outside_zone_right": create_outside_zone_right(),
    "outside_zone_left": create_outside_zone_left(),
    "power_right": create_power_right(),
    "power_left": create_power_left(),
    "counter_right": create_counter_right(),
    "dive_right": create_dive_right(),
    "draw": create_draw(),
    "toss_right": create_toss_right(),
}


def get_run_concept(name: str) -> Optional[RunConcept]:
    """Get a run concept by name.

    Tries exact match first, then appends _right suffix for partial names.
    E.g., "inside_zone" -> "inside_zone_right"
    """
    name_lower = name.lower()

    # Try exact match
    concept = RUN_CONCEPT_LIBRARY.get(name_lower)
    if concept:
        return concept

    # Try with _right suffix (default direction)
    if not name_lower.endswith(("_left", "_right")):
        concept = RUN_CONCEPT_LIBRARY.get(f"{name_lower}_right")
        if concept:
            return concept

    return None


def is_run_concept_name(name: str) -> bool:
    """Check if a name corresponds to a run concept.

    Useful for auto-detecting run plays from concept names.
    """
    return get_run_concept(name) is not None


def list_run_concepts() -> List[str]:
    """List all available run concept names."""
    return list(RUN_CONCEPT_LIBRARY.keys())


def get_run_concepts_by_scheme(scheme: RunScheme) -> List[RunConcept]:
    """Get all run concepts of a specific scheme type."""
    return [c for c in RUN_CONCEPT_LIBRARY.values() if c.scheme == scheme]
