"""
Play Code Definitions.

Defines all learnable plays in the game as unique identifiers.
Each play has a code, display name, complexity, and list of positions
that need to learn it.
"""

from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet


class PlayCategory(Enum):
    """Categories for play codes."""
    RUN = "run"
    PASS = "pass"
    SPECIAL = "special"
    DEFENSE = "defense"


@dataclass(frozen=True)
class PlayCode:
    """
    A unique play identifier with metadata.

    Attributes:
        code: Unique string identifier (e.g., "RUN_POWER")
        name: Display name (e.g., "Power Run")
        category: RUN, PASS, SPECIAL, or DEFENSE
        complexity: 1-5, affects learning time (1=easy, 5=complex)
        positions_involved: Set of position abbreviations that need to learn it
    """
    code: str
    name: str
    category: PlayCategory
    complexity: int
    positions_involved: FrozenSet[str]

    def __post_init__(self):
        if not 1 <= self.complexity <= 5:
            raise ValueError(f"Complexity must be 1-5, got {self.complexity}")


# =============================================================================
# Position Groups (for convenience)
# =============================================================================

# Offensive line positions
OL_POSITIONS = frozenset({"LT", "LG", "C", "RG", "RT"})

# Skill positions (pass routes)
SKILL_POSITIONS = frozenset({"QB", "WR", "TE", "RB"})

# Pass catchers
PASS_CATCHERS = frozenset({"WR", "TE", "RB"})

# All offense
ALL_OFFENSE = frozenset({"QB", "RB", "FB", "WR", "TE", "LT", "LG", "C", "RG", "RT"})

# All defense
ALL_DEFENSE = frozenset({"DE", "DT", "NT", "MLB", "ILB", "OLB", "CB", "FS", "SS"})


# =============================================================================
# Offensive Plays - Run Game
# =============================================================================

OFFENSIVE_PLAYS: dict[str, PlayCode] = {
    # Inside Run Plays
    "RUN_INSIDE_ZONE": PlayCode(
        code="RUN_INSIDE_ZONE",
        name="Inside Zone",
        category=PlayCategory.RUN,
        complexity=2,
        positions_involved=frozenset({"QB", "RB", "FB"}) | OL_POSITIONS,
    ),
    "RUN_OUTSIDE_ZONE": PlayCode(
        code="RUN_OUTSIDE_ZONE",
        name="Outside Zone",
        category=PlayCategory.RUN,
        complexity=3,
        positions_involved=frozenset({"QB", "RB", "FB"}) | OL_POSITIONS,
    ),
    "RUN_POWER": PlayCode(
        code="RUN_POWER",
        name="Power Run",
        category=PlayCategory.RUN,
        complexity=2,
        positions_involved=frozenset({"QB", "RB", "FB"}) | OL_POSITIONS,
    ),
    "RUN_COUNTER": PlayCode(
        code="RUN_COUNTER",
        name="Counter",
        category=PlayCategory.RUN,
        complexity=4,
        positions_involved=frozenset({"QB", "RB", "FB"}) | OL_POSITIONS,
    ),
    "RUN_DRAW": PlayCode(
        code="RUN_DRAW",
        name="Draw",
        category=PlayCategory.RUN,
        complexity=3,
        positions_involved=frozenset({"QB", "RB"}) | OL_POSITIONS,
    ),
    "RUN_TRAP": PlayCode(
        code="RUN_TRAP",
        name="Trap",
        category=PlayCategory.RUN,
        complexity=3,
        positions_involved=frozenset({"QB", "RB", "FB"}) | OL_POSITIONS,
    ),
    "RUN_SWEEP": PlayCode(
        code="RUN_SWEEP",
        name="Sweep",
        category=PlayCategory.RUN,
        complexity=3,
        positions_involved=frozenset({"QB", "RB"}) | OL_POSITIONS | frozenset({"WR", "TE"}),
    ),
    "RUN_OPTION": PlayCode(
        code="RUN_OPTION",
        name="Option",
        category=PlayCategory.RUN,
        complexity=5,
        positions_involved=frozenset({"QB", "RB", "FB"}) | OL_POSITIONS,
    ),
    "RUN_QB_SNEAK": PlayCode(
        code="RUN_QB_SNEAK",
        name="QB Sneak",
        category=PlayCategory.RUN,
        complexity=1,
        positions_involved=frozenset({"QB"}) | OL_POSITIONS,
    ),

    # =============================================================================
    # Offensive Plays - Pass Game
    # =============================================================================

    # Quick Game (1-2 complexity)
    "PASS_SLANT": PlayCode(
        code="PASS_SLANT",
        name="Slants",
        category=PlayCategory.PASS,
        complexity=2,
        positions_involved=frozenset({"QB", "WR", "TE"}) | OL_POSITIONS,
    ),
    "PASS_QUICK_OUT": PlayCode(
        code="PASS_QUICK_OUT",
        name="Quick Outs",
        category=PlayCategory.PASS,
        complexity=2,
        positions_involved=frozenset({"QB", "WR", "TE"}) | OL_POSITIONS,
    ),
    "PASS_HITCH": PlayCode(
        code="PASS_HITCH",
        name="Hitch Routes",
        category=PlayCategory.PASS,
        complexity=1,
        positions_involved=frozenset({"QB", "WR", "TE"}) | OL_POSITIONS,
    ),

    # Intermediate (3 complexity)
    "PASS_CURL": PlayCode(
        code="PASS_CURL",
        name="Curl Routes",
        category=PlayCategory.PASS,
        complexity=3,
        positions_involved=frozenset({"QB", "WR", "TE"}) | OL_POSITIONS,
    ),
    "PASS_DIG": PlayCode(
        code="PASS_DIG",
        name="Dig Routes",
        category=PlayCategory.PASS,
        complexity=3,
        positions_involved=frozenset({"QB", "WR", "TE"}) | OL_POSITIONS,
    ),
    "PASS_COMEBACK": PlayCode(
        code="PASS_COMEBACK",
        name="Comeback Routes",
        category=PlayCategory.PASS,
        complexity=3,
        positions_involved=frozenset({"QB", "WR", "TE"}) | OL_POSITIONS,
    ),
    "PASS_CROSSER": PlayCode(
        code="PASS_CROSSER",
        name="Crossing Routes",
        category=PlayCategory.PASS,
        complexity=3,
        positions_involved=frozenset({"QB", "WR", "TE"}) | OL_POSITIONS,
    ),

    # Deep Passes (3-4 complexity)
    "PASS_FOUR_VERTS": PlayCode(
        code="PASS_FOUR_VERTS",
        name="Four Verticals",
        category=PlayCategory.PASS,
        complexity=3,
        positions_involved=frozenset({"QB", "WR", "TE"}) | OL_POSITIONS,
    ),
    "PASS_POST": PlayCode(
        code="PASS_POST",
        name="Post Routes",
        category=PlayCategory.PASS,
        complexity=3,
        positions_involved=frozenset({"QB", "WR", "TE"}) | OL_POSITIONS,
    ),
    "PASS_CORNER": PlayCode(
        code="PASS_CORNER",
        name="Corner Routes",
        category=PlayCategory.PASS,
        complexity=3,
        positions_involved=frozenset({"QB", "WR", "TE"}) | OL_POSITIONS,
    ),
    "PASS_DOUBLE_MOVE": PlayCode(
        code="PASS_DOUBLE_MOVE",
        name="Double Moves",
        category=PlayCategory.PASS,
        complexity=4,
        positions_involved=frozenset({"QB", "WR"}) | OL_POSITIONS,
    ),

    # Concepts (4-5 complexity)
    "PASS_MESH": PlayCode(
        code="PASS_MESH",
        name="Mesh Concept",
        category=PlayCategory.PASS,
        complexity=4,
        positions_involved=frozenset({"QB", "WR", "TE"}) | OL_POSITIONS,
    ),
    "PASS_FLOOD": PlayCode(
        code="PASS_FLOOD",
        name="Flood Concept",
        category=PlayCategory.PASS,
        complexity=4,
        positions_involved=frozenset({"QB", "WR", "TE", "RB"}) | OL_POSITIONS,
    ),
    "PASS_SMASH": PlayCode(
        code="PASS_SMASH",
        name="Smash Concept",
        category=PlayCategory.PASS,
        complexity=3,
        positions_involved=frozenset({"QB", "WR", "TE"}) | OL_POSITIONS,
    ),
    "PASS_LEVELS": PlayCode(
        code="PASS_LEVELS",
        name="Levels Concept",
        category=PlayCategory.PASS,
        complexity=4,
        positions_involved=frozenset({"QB", "WR", "TE"}) | OL_POSITIONS,
    ),
    "PASS_SAIL": PlayCode(
        code="PASS_SAIL",
        name="Sail Concept",
        category=PlayCategory.PASS,
        complexity=4,
        positions_involved=frozenset({"QB", "WR", "TE", "RB"}) | OL_POSITIONS,
    ),

    # Screens (3 complexity)
    "PASS_SCREEN_RB": PlayCode(
        code="PASS_SCREEN_RB",
        name="RB Screen",
        category=PlayCategory.PASS,
        complexity=3,
        positions_involved=frozenset({"QB", "RB"}) | OL_POSITIONS,
    ),
    "PASS_SCREEN_WR": PlayCode(
        code="PASS_SCREEN_WR",
        name="WR Screen",
        category=PlayCategory.PASS,
        complexity=3,
        positions_involved=frozenset({"QB", "WR"}) | OL_POSITIONS,
    ),
    "PASS_SCREEN_TE": PlayCode(
        code="PASS_SCREEN_TE",
        name="TE Screen",
        category=PlayCategory.PASS,
        complexity=3,
        positions_involved=frozenset({"QB", "TE"}) | OL_POSITIONS,
    ),

    # Play Action (adds 1 complexity to base play)
    "PASS_PLAY_ACTION": PlayCode(
        code="PASS_PLAY_ACTION",
        name="Play Action",
        category=PlayCategory.PASS,
        complexity=4,
        positions_involved=frozenset({"QB", "RB", "WR", "TE"}) | OL_POSITIONS,
    ),
    "PASS_BOOTLEG": PlayCode(
        code="PASS_BOOTLEG",
        name="Bootleg",
        category=PlayCategory.PASS,
        complexity=4,
        positions_involved=frozenset({"QB", "RB", "WR", "TE"}) | OL_POSITIONS,
    ),
}


# =============================================================================
# Defensive Plays
# =============================================================================

DEFENSIVE_PLAYS: dict[str, PlayCode] = {
    # Zone Coverages
    "COVER_0": PlayCode(
        code="COVER_0",
        name="Cover 0 (Man Blitz)",
        category=PlayCategory.DEFENSE,
        complexity=3,
        positions_involved=ALL_DEFENSE,
    ),
    "COVER_1": PlayCode(
        code="COVER_1",
        name="Cover 1 (Man Free)",
        category=PlayCategory.DEFENSE,
        complexity=3,
        positions_involved=ALL_DEFENSE,
    ),
    "COVER_2": PlayCode(
        code="COVER_2",
        name="Cover 2 Zone",
        category=PlayCategory.DEFENSE,
        complexity=2,
        positions_involved=ALL_DEFENSE,
    ),
    "COVER_2_MAN": PlayCode(
        code="COVER_2_MAN",
        name="Cover 2 Man",
        category=PlayCategory.DEFENSE,
        complexity=3,
        positions_involved=ALL_DEFENSE,
    ),
    "COVER_3": PlayCode(
        code="COVER_3",
        name="Cover 3 Zone",
        category=PlayCategory.DEFENSE,
        complexity=2,
        positions_involved=ALL_DEFENSE,
    ),
    "COVER_4": PlayCode(
        code="COVER_4",
        name="Cover 4 (Quarters)",
        category=PlayCategory.DEFENSE,
        complexity=3,
        positions_involved=ALL_DEFENSE,
    ),
    "COVER_6": PlayCode(
        code="COVER_6",
        name="Cover 6 (Quarter-Quarter-Half)",
        category=PlayCategory.DEFENSE,
        complexity=4,
        positions_involved=ALL_DEFENSE,
    ),

    # Man Coverages
    "MAN_PRESS": PlayCode(
        code="MAN_PRESS",
        name="Press Man",
        category=PlayCategory.DEFENSE,
        complexity=3,
        positions_involved=ALL_DEFENSE,
    ),
    "MAN_OFF": PlayCode(
        code="MAN_OFF",
        name="Off Man",
        category=PlayCategory.DEFENSE,
        complexity=2,
        positions_involved=ALL_DEFENSE,
    ),

    # Blitz Packages
    "BLITZ_ZONE": PlayCode(
        code="BLITZ_ZONE",
        name="Zone Blitz",
        category=PlayCategory.DEFENSE,
        complexity=4,
        positions_involved=ALL_DEFENSE,
    ),
    "BLITZ_FIRE": PlayCode(
        code="BLITZ_FIRE",
        name="Fire Zone",
        category=PlayCategory.DEFENSE,
        complexity=4,
        positions_involved=ALL_DEFENSE,
    ),
    "BLITZ_DOG": PlayCode(
        code="BLITZ_DOG",
        name="Dog Blitz (LB)",
        category=PlayCategory.DEFENSE,
        complexity=3,
        positions_involved=ALL_DEFENSE,
    ),
    "BLITZ_CORNER": PlayCode(
        code="BLITZ_CORNER",
        name="Corner Blitz",
        category=PlayCategory.DEFENSE,
        complexity=4,
        positions_involved=ALL_DEFENSE,
    ),
    "BLITZ_SAFETY": PlayCode(
        code="BLITZ_SAFETY",
        name="Safety Blitz",
        category=PlayCategory.DEFENSE,
        complexity=4,
        positions_involved=ALL_DEFENSE,
    ),
}


# =============================================================================
# Combined Registry
# =============================================================================

ALL_PLAYS: dict[str, PlayCode] = {**OFFENSIVE_PLAYS, **DEFENSIVE_PLAYS}


def get_play(code: str) -> PlayCode | None:
    """Get a play by its code."""
    return ALL_PLAYS.get(code)


def get_plays_for_position(position: str) -> list[PlayCode]:
    """Get all plays that involve a specific position."""
    return [play for play in ALL_PLAYS.values() if position in play.positions_involved]


def get_offensive_plays() -> list[PlayCode]:
    """Get all offensive plays."""
    return list(OFFENSIVE_PLAYS.values())


def get_defensive_plays() -> list[PlayCode]:
    """Get all defensive plays."""
    return list(DEFENSIVE_PLAYS.values())


# =============================================================================
# Default Playbooks by Scheme
# =============================================================================

# Default offensive plays for a balanced/pro-style team
DEFAULT_OFFENSIVE_PLAYBOOK: set[str] = {
    # Core runs
    "RUN_INSIDE_ZONE",
    "RUN_OUTSIDE_ZONE",
    "RUN_POWER",
    "RUN_DRAW",
    # Quick passing
    "PASS_SLANT",
    "PASS_QUICK_OUT",
    "PASS_HITCH",
    # Intermediate
    "PASS_CURL",
    "PASS_DIG",
    "PASS_CROSSER",
    # Deep
    "PASS_FOUR_VERTS",
    "PASS_POST",
    # Concepts
    "PASS_MESH",
    "PASS_FLOOD",
    # Screens
    "PASS_SCREEN_RB",
    # Play action
    "PASS_PLAY_ACTION",
}

# Default defensive plays for a balanced team
DEFAULT_DEFENSIVE_PLAYBOOK: set[str] = {
    "COVER_1",
    "COVER_2",
    "COVER_3",
    "COVER_4",
    "MAN_PRESS",
    "MAN_OFF",
    "BLITZ_ZONE",
    "BLITZ_DOG",
}
