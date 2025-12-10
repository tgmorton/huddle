"""Position definitions for football players."""

from enum import Enum, auto


class PositionGroup(Enum):
    """High-level position groupings."""

    OFFENSE = auto()
    DEFENSE = auto()
    SPECIAL_TEAMS = auto()


class Position(Enum):
    """Individual player positions."""

    # Offense - Skill positions
    QB = "QB"  # Quarterback
    RB = "RB"  # Running Back
    FB = "FB"  # Fullback
    WR = "WR"  # Wide Receiver
    TE = "TE"  # Tight End

    # Offense - Line
    LT = "LT"  # Left Tackle
    LG = "LG"  # Left Guard
    C = "C"  # Center
    RG = "RG"  # Right Guard
    RT = "RT"  # Right Tackle

    # Defense - Line
    DE = "DE"  # Defensive End
    DT = "DT"  # Defensive Tackle
    NT = "NT"  # Nose Tackle

    # Defense - Linebackers
    MLB = "MLB"  # Middle Linebacker
    OLB = "OLB"  # Outside Linebacker
    ILB = "ILB"  # Inside Linebacker

    # Defense - Secondary
    CB = "CB"  # Cornerback
    FS = "FS"  # Free Safety
    SS = "SS"  # Strong Safety

    # Special Teams
    K = "K"  # Kicker
    P = "P"  # Punter
    LS = "LS"  # Long Snapper

    @property
    def group(self) -> PositionGroup:
        """Get the position group for this position."""
        offense = {
            Position.QB,
            Position.RB,
            Position.FB,
            Position.WR,
            Position.TE,
            Position.LT,
            Position.LG,
            Position.C,
            Position.RG,
            Position.RT,
        }
        defense = {
            Position.DE,
            Position.DT,
            Position.NT,
            Position.MLB,
            Position.OLB,
            Position.ILB,
            Position.CB,
            Position.FS,
            Position.SS,
        }
        if self in offense:
            return PositionGroup.OFFENSE
        if self in defense:
            return PositionGroup.DEFENSE
        return PositionGroup.SPECIAL_TEAMS

    @property
    def is_skill_position(self) -> bool:
        """Check if this is an offensive skill position."""
        return self in {Position.QB, Position.RB, Position.FB, Position.WR, Position.TE}

    @property
    def is_lineman(self) -> bool:
        """Check if this is a lineman position (offense or defense)."""
        return self in {
            Position.LT,
            Position.LG,
            Position.C,
            Position.RG,
            Position.RT,
            Position.DE,
            Position.DT,
            Position.NT,
        }


# Depth chart slot definitions - maps slot names to positions
OFFENSE_DEPTH_SLOTS = {
    "QB1": Position.QB,
    "RB1": Position.RB,
    "RB2": Position.RB,
    "FB1": Position.FB,
    "WR1": Position.WR,
    "WR2": Position.WR,
    "WR3": Position.WR,
    "TE1": Position.TE,
    "TE2": Position.TE,
    "LT1": Position.LT,
    "LG1": Position.LG,
    "C1": Position.C,
    "RG1": Position.RG,
    "RT1": Position.RT,
}

DEFENSE_DEPTH_SLOTS = {
    "DE1": Position.DE,
    "DE2": Position.DE,
    "DT1": Position.DT,
    "DT2": Position.DT,
    "MLB1": Position.MLB,
    "OLB1": Position.OLB,
    "OLB2": Position.OLB,
    "CB1": Position.CB,
    "CB2": Position.CB,
    "FS1": Position.FS,
    "SS1": Position.SS,
}

SPECIAL_TEAMS_DEPTH_SLOTS = {
    "K1": Position.K,
    "P1": Position.P,
    "LS1": Position.LS,
}
