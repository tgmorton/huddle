"""
Philosophy-Based Player Evaluation System.

Inspired by NFL Head Coach 09, this module implements team-specific player
evaluation where each team calculates OVR differently based on their
positional philosophies.

Key concept: A player's OVR is NOT universal - each team sees a different
value based on what kind of players they're looking for.

Example: A 90 SPD, 75 TRK running back might be:
- 88 OVR to a team with "Speed Back" philosophy
- 82 OVR to a team with "Power Back" philosophy
"""

from huddle.core.philosophy.positions import (
    # QB Philosophies
    QBPhilosophy,
    # RB Philosophies
    RBPhilosophy,
    # WR Philosophies
    WRPhilosophy,
    # TE Philosophies
    TEPhilosophy,
    # OL Philosophies
    OLPhilosophy,
    # DL Philosophies
    DLPhilosophy,
    # LB Philosophies
    LBPhilosophy,
    # CB Philosophies
    CBPhilosophy,
    # FS Philosophies
    FSPhilosophy,
    # SS Philosophies
    SSPhilosophy,
)

from huddle.core.philosophy.evaluation import (
    TeamPhilosophies,
    calculate_philosophy_overall,
    get_philosophy_weights,
    PHILOSOPHY_ATTRIBUTE_WEIGHTS,
)

__all__ = [
    # Position Philosophy Enums
    "QBPhilosophy",
    "RBPhilosophy",
    "WRPhilosophy",
    "TEPhilosophy",
    "OLPhilosophy",
    "DLPhilosophy",
    "LBPhilosophy",
    "CBPhilosophy",
    "FSPhilosophy",
    "SSPhilosophy",
    # Evaluation
    "TeamPhilosophies",
    "calculate_philosophy_overall",
    "get_philosophy_weights",
    "PHILOSOPHY_ATTRIBUTE_WEIGHTS",
]
