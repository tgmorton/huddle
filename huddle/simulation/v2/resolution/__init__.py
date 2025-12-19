"""Resolution layer for v2 simulation.

Resolves physical encounters: tackles, moves, blocks.
"""

from .tackle import TackleResolver, TackleAttempt, TackleResult
from .move import MoveResolver, MoveAttempt, MoveResult, MoveOutcome, MoveType

__all__ = [
    "TackleResolver",
    "TackleAttempt",
    "TackleResult",
    "MoveResolver",
    "MoveAttempt",
    "MoveResult",
    "MoveOutcome",
    "MoveType",
]
