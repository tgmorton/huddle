"""Defensive schemes - complete coverage deployments.

A scheme defines how all defensive backs align and their coverage
responsibilities. This includes:
- Player positions and alignments
- Coverage type (man or zone) per defender
- Zone assignments for zone players
- Man assignments based on receiver alignment
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Callable

from ..systems.coverage import CoverageType, ZoneType, CoverageScheme


class DefenderPosition(str, Enum):
    """Standard defensive back positions."""
    CB1 = "cb1"         # #1 corner (usually left)
    CB2 = "cb2"         # #2 corner (usually right)
    SLOT_CB = "slot_cb" # Nickel corner
    FS = "fs"           # Free safety
    SS = "ss"           # Strong safety
    LB1 = "lb1"         # Linebacker 1 (could be in coverage)
    LB2 = "lb2"         # Linebacker 2


@dataclass
class DefenderAlignment:
    """Where a defender lines up pre-snap.

    Coordinates are in yards from center (x) and LOS (y).
    Positive x = defender's right (offense's left).
    y is always positive (defensive side of LOS).
    """
    position: DefenderPosition
    x: float  # Yards from center
    y: float  # Yards off LOS (depth)
    technique: str = ""  # e.g., "press", "off", "bail"

    @property
    def is_deep(self) -> bool:
        """Is this a deep alignment (safety depth)?"""
        return self.y >= 8


@dataclass
class DefenderAssignment:
    """A defender's assignment in a coverage scheme.

    Can be man coverage (with receiver_key to match against)
    or zone coverage (with zone_type).
    """
    position: DefenderPosition
    coverage_type: CoverageType
    zone_type: Optional[ZoneType] = None
    receiver_key: Optional[str] = None  # Which receiver to cover in man (e.g., "#1", "slot", "rb")
    technique: str = "off"  # press, off, bail, etc.

    @property
    def is_man(self) -> bool:
        return self.coverage_type == CoverageType.MAN

    @property
    def is_zone(self) -> bool:
        return self.coverage_type == CoverageType.ZONE


@dataclass
class DefensiveScheme:
    """A complete defensive coverage scheme.

    Attributes:
        name: Scheme name (e.g., "Cover 2", "Cover 3 Sky")
        scheme_type: Base scheme classification
        description: What the scheme does and its strengths/weaknesses
        alignments: Where each defender lines up
        assignments: Coverage assignments for each defender
        strengths: What this coverage is good against
        weaknesses: What can beat this coverage
    """
    name: str
    scheme_type: CoverageScheme
    description: str
    alignments: List[DefenderAlignment]
    assignments: List[DefenderAssignment]
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)

    def get_alignment(self, position: DefenderPosition) -> Optional[DefenderAlignment]:
        """Get alignment for a specific position."""
        for align in self.alignments:
            if align.position == position:
                return align
        return None

    def get_assignment(self, position: DefenderPosition) -> Optional[DefenderAssignment]:
        """Get assignment for a specific position."""
        for assign in self.assignments:
            if assign.position == position:
                return assign
        return None

    def describe(self) -> str:
        """Human-readable scheme description."""
        lines = [
            f"=== {self.name} ({self.scheme_type.value}) ===",
            "",
            "Alignments:",
        ]
        for align in self.alignments:
            depth_desc = "deep" if align.is_deep else "shallow"
            lines.append(f"  {align.position.value}: ({align.x:+.0f}, {align.y:.0f}) {align.technique} [{depth_desc}]")

        lines.append("")
        lines.append("Assignments:")
        for assign in self.assignments:
            if assign.is_man:
                lines.append(f"  {assign.position.value}: MAN on {assign.receiver_key}")
            else:
                lines.append(f"  {assign.position.value}: ZONE - {assign.zone_type.value if assign.zone_type else 'none'}")

        lines.append("")
        lines.append(f"Strengths: {', '.join(self.strengths)}")
        lines.append(f"Weaknesses: {', '.join(self.weaknesses)}")
        lines.append("")
        lines.append(f"Description: {self.description}")
        return "\n".join(lines)


# =============================================================================
# Standard Alignments
# =============================================================================

def _two_high_alignments() -> List[DefenderAlignment]:
    """Two-high safety shell (Cover 2, Cover 4)."""
    return [
        DefenderAlignment(DefenderPosition.CB1, x=-24, y=7, technique="off"),
        DefenderAlignment(DefenderPosition.CB2, x=24, y=7, technique="off"),
        DefenderAlignment(DefenderPosition.SLOT_CB, x=-8, y=5, technique="off"),
        DefenderAlignment(DefenderPosition.FS, x=-10, y=12, technique="deep"),
        DefenderAlignment(DefenderPosition.SS, x=10, y=12, technique="deep"),
    ]

def _single_high_alignments() -> List[DefenderAlignment]:
    """Single-high safety shell (Cover 1, Cover 3)."""
    return [
        DefenderAlignment(DefenderPosition.CB1, x=-24, y=7, technique="off"),
        DefenderAlignment(DefenderPosition.CB2, x=24, y=7, technique="off"),
        DefenderAlignment(DefenderPosition.SLOT_CB, x=-8, y=5, technique="off"),
        DefenderAlignment(DefenderPosition.FS, x=0, y=14, technique="deep"),
        DefenderAlignment(DefenderPosition.SS, x=10, y=8, technique="robber"),
    ]

def _press_man_alignments() -> List[DefenderAlignment]:
    """Press man coverage shell (Cover 0)."""
    return [
        DefenderAlignment(DefenderPosition.CB1, x=-24, y=1, technique="press"),
        DefenderAlignment(DefenderPosition.CB2, x=24, y=1, technique="press"),
        DefenderAlignment(DefenderPosition.SLOT_CB, x=-8, y=1, technique="press"),
        DefenderAlignment(DefenderPosition.FS, x=-10, y=10, technique="lurk"),
        DefenderAlignment(DefenderPosition.SS, x=10, y=10, technique="lurk"),
    ]


# =============================================================================
# Scheme Definitions
# =============================================================================

def create_cover_0() -> DefensiveScheme:
    """Cover 0 - Pure man, no deep help.

    All-out blitz or press-man scheme. High risk, high reward.
    One-on-one coverage across the board.
    """
    return DefensiveScheme(
        name="Cover 0",
        scheme_type=CoverageScheme.COVER_0,
        description="Pure man coverage with no deep safety help. "
                    "All defenders in man coverage with press technique. "
                    "Often paired with all-out blitz.",
        alignments=_press_man_alignments(),
        assignments=[
            DefenderAssignment(DefenderPosition.CB1, CoverageType.MAN, receiver_key="#1_left", technique="press"),
            DefenderAssignment(DefenderPosition.CB2, CoverageType.MAN, receiver_key="#1_right", technique="press"),
            DefenderAssignment(DefenderPosition.SLOT_CB, CoverageType.MAN, receiver_key="slot", technique="press"),
            DefenderAssignment(DefenderPosition.FS, CoverageType.MAN, receiver_key="te", technique="trail"),
            DefenderAssignment(DefenderPosition.SS, CoverageType.MAN, receiver_key="rb", technique="trail"),
        ],
        strengths=["quick pressure", "disrupts timing", "aggressive"],
        weaknesses=["deep shots", "mesh/picks", "double moves"],
    )


def create_cover_1() -> DefensiveScheme:
    """Cover 1 - Man coverage with single high safety.

    Man coverage underneath with one safety playing center field.
    Good balance of aggression and protection.
    """
    return DefensiveScheme(
        name="Cover 1",
        scheme_type=CoverageScheme.COVER_1,
        description="Man coverage with single high safety. "
                    "Corners and slot defender play man, free safety helps deep. "
                    "Strong safety can blitz or play robber.",
        alignments=_single_high_alignments(),
        assignments=[
            DefenderAssignment(DefenderPosition.CB1, CoverageType.MAN, receiver_key="#1_left", technique="off"),
            DefenderAssignment(DefenderPosition.CB2, CoverageType.MAN, receiver_key="#1_right", technique="off"),
            DefenderAssignment(DefenderPosition.SLOT_CB, CoverageType.MAN, receiver_key="slot", technique="off"),
            DefenderAssignment(DefenderPosition.FS, CoverageType.ZONE, zone_type=ZoneType.DEEP_THIRD_M),
            DefenderAssignment(DefenderPosition.SS, CoverageType.ZONE, zone_type=ZoneType.MIDDLE),  # Robber
        ],
        strengths=["man coverage", "deep help", "versatile"],
        weaknesses=["crossing routes", "picks", "flood concepts"],
    )


def create_cover_2() -> DefensiveScheme:
    """Cover 2 - Two deep, five under zones.

    Classic zone coverage with two safeties splitting the deep half.
    Five underneath defenders cover flats, hooks, and middle.
    """
    return DefensiveScheme(
        name="Cover 2",
        scheme_type=CoverageScheme.COVER_2,
        description="Two safeties split deep halves, five underneath. "
                    "Corners play flat zones, funnel receivers inside. "
                    "Vulnerable to four verticals and deep middle.",
        alignments=_two_high_alignments(),
        assignments=[
            DefenderAssignment(DefenderPosition.CB1, CoverageType.ZONE, zone_type=ZoneType.FLAT_L, technique="squat"),
            DefenderAssignment(DefenderPosition.CB2, CoverageType.ZONE, zone_type=ZoneType.FLAT_R, technique="squat"),
            DefenderAssignment(DefenderPosition.SLOT_CB, CoverageType.ZONE, zone_type=ZoneType.HOOK_L),
            DefenderAssignment(DefenderPosition.FS, CoverageType.ZONE, zone_type=ZoneType.DEEP_HALF_L),
            DefenderAssignment(DefenderPosition.SS, CoverageType.ZONE, zone_type=ZoneType.DEEP_HALF_R),
        ],
        strengths=["underneath zones", "run support", "disguise"],
        weaknesses=["four verts", "seams", "deep middle"],
    )


def create_cover_3() -> DefensiveScheme:
    """Cover 3 - Three deep, four under zones.

    Single high safety with corners playing deep thirds.
    Good against deep passes, vulnerable to intermediate.
    """
    return DefensiveScheme(
        name="Cover 3",
        scheme_type=CoverageScheme.COVER_3,
        description="Three deep defenders (FS + 2 CBs) split into thirds. "
                    "Four underneath defenders (SS + 3 LBs). "
                    "Strong against deep shots, weak against floods.",
        alignments=_single_high_alignments(),
        assignments=[
            DefenderAssignment(DefenderPosition.CB1, CoverageType.ZONE, zone_type=ZoneType.DEEP_THIRD_L, technique="bail"),
            DefenderAssignment(DefenderPosition.CB2, CoverageType.ZONE, zone_type=ZoneType.DEEP_THIRD_R, technique="bail"),
            DefenderAssignment(DefenderPosition.SLOT_CB, CoverageType.ZONE, zone_type=ZoneType.CURL_FLAT_L),
            DefenderAssignment(DefenderPosition.FS, CoverageType.ZONE, zone_type=ZoneType.DEEP_THIRD_M),
            DefenderAssignment(DefenderPosition.SS, CoverageType.ZONE, zone_type=ZoneType.CURL_FLAT_R),
        ],
        strengths=["deep coverage", "simple", "run support"],
        weaknesses=["flood", "4 verts to seams", "curl-flat"],
    )


def create_cover_4() -> DefensiveScheme:
    """Cover 4 (Quarters) - Four deep, three under zones.

    Both safeties and corners play quarter coverage.
    Great against deep passes, light underneath.
    """
    return DefensiveScheme(
        name="Cover 4 (Quarters)",
        scheme_type=CoverageScheme.COVER_4,
        description="Four defenders split deep into quarters. "
                    "Excellent deep coverage, can match vertical routes. "
                    "Light underneath coverage makes it vulnerable to quick game.",
        alignments=_two_high_alignments(),
        assignments=[
            DefenderAssignment(DefenderPosition.CB1, CoverageType.ZONE, zone_type=ZoneType.DEEP_QUARTER_1, technique="off"),
            DefenderAssignment(DefenderPosition.CB2, CoverageType.ZONE, zone_type=ZoneType.DEEP_QUARTER_4, technique="off"),
            DefenderAssignment(DefenderPosition.SLOT_CB, CoverageType.ZONE, zone_type=ZoneType.HOOK_L),
            DefenderAssignment(DefenderPosition.FS, CoverageType.ZONE, zone_type=ZoneType.DEEP_QUARTER_2),
            DefenderAssignment(DefenderPosition.SS, CoverageType.ZONE, zone_type=ZoneType.DEEP_QUARTER_3),
        ],
        strengths=["deep coverage", "prevents big plays", "match coverage"],
        weaknesses=["quick game", "underneath", "run game"],
    )


def create_cover_2_man() -> DefensiveScheme:
    """Cover 2 Man - Two deep safeties, man under.

    Combines man coverage underneath with two-deep zone.
    Best of both worlds but requires good underneath defenders.
    """
    return DefensiveScheme(
        name="Cover 2 Man",
        scheme_type=CoverageScheme.COVER_2_MAN,
        description="Two safeties in deep halves, underneath defenders in man. "
                    "Combines tight man coverage with deep safety help. "
                    "Requires excellent underneath defenders.",
        alignments=_two_high_alignments(),
        assignments=[
            DefenderAssignment(DefenderPosition.CB1, CoverageType.MAN, receiver_key="#1_left", technique="off"),
            DefenderAssignment(DefenderPosition.CB2, CoverageType.MAN, receiver_key="#1_right", technique="off"),
            DefenderAssignment(DefenderPosition.SLOT_CB, CoverageType.MAN, receiver_key="slot", technique="off"),
            DefenderAssignment(DefenderPosition.FS, CoverageType.ZONE, zone_type=ZoneType.DEEP_HALF_L),
            DefenderAssignment(DefenderPosition.SS, CoverageType.ZONE, zone_type=ZoneType.DEEP_HALF_R),
        ],
        strengths=["tight coverage", "deep help", "balanced"],
        weaknesses=["picks", "rubs", "crossing routes"],
    )


def create_cover_6() -> DefensiveScheme:
    """Cover 6 - Split coverage (Cover 4 weak, Cover 2 strong).

    Hybrid coverage with quarter coverage to weak side,
    Cover 2 to the strong/passing strength side.
    """
    return DefensiveScheme(
        name="Cover 6",
        scheme_type=CoverageScheme.COVER_2,  # Base is cover 2
        description="Split coverage: Cover 4 to weak side, Cover 2 to strong. "
                    "Adapts coverage based on formation strength. "
                    "Good against trips formations.",
        alignments=_two_high_alignments(),
        assignments=[
            DefenderAssignment(DefenderPosition.CB1, CoverageType.ZONE, zone_type=ZoneType.DEEP_QUARTER_1, technique="off"),
            DefenderAssignment(DefenderPosition.CB2, CoverageType.ZONE, zone_type=ZoneType.FLAT_R, technique="squat"),
            DefenderAssignment(DefenderPosition.SLOT_CB, CoverageType.ZONE, zone_type=ZoneType.HOOK_L),
            DefenderAssignment(DefenderPosition.FS, CoverageType.ZONE, zone_type=ZoneType.DEEP_QUARTER_2),
            DefenderAssignment(DefenderPosition.SS, CoverageType.ZONE, zone_type=ZoneType.DEEP_HALF_R),
        ],
        strengths=["trips formations", "adaptable", "run support"],
        weaknesses=["weak side flood", "boundary routes"],
    )


# =============================================================================
# Scheme Library
# =============================================================================

SCHEME_LIBRARY: Dict[str, DefensiveScheme] = {
    "cover_0": create_cover_0(),
    "cover_1": create_cover_1(),
    "cover_2": create_cover_2(),
    "cover_3": create_cover_3(),
    "cover_4": create_cover_4(),
    "cover_2_man": create_cover_2_man(),
    "cover_6": create_cover_6(),
}


def get_scheme(name: str) -> Optional[DefensiveScheme]:
    """Get a defensive scheme by name."""
    return SCHEME_LIBRARY.get(name.lower().replace(" ", "_"))


def list_schemes() -> List[str]:
    """List all available scheme names."""
    return list(SCHEME_LIBRARY.keys())


def schemes_weak_against(concept: str) -> List[DefensiveScheme]:
    """Get schemes that are weak against a specific concept/play."""
    concept = concept.lower()
    return [s for s in SCHEME_LIBRARY.values() if concept in s.weaknesses]


def schemes_strong_against(concept: str) -> List[DefensiveScheme]:
    """Get schemes that are strong against a specific concept/play."""
    concept = concept.lower()
    return [s for s in SCHEME_LIBRARY.values() if concept in s.strengths]
