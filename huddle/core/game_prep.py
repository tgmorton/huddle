"""
Game Preparation System.

Provides temporary bonuses for studying the next opponent.
Bonuses expire after the game is played - must re-prep each week.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID


# =============================================================================
# Constants
# =============================================================================

# Reps needed for full game prep (100% prep level)
MAX_PREP_REPS = 40

# Maximum bonuses at 100% prep level
MAX_SCHEME_BONUS = 0.10      # +10% to play recognition
MAX_EXECUTION_BONUS = 0.05   # +5% to execution


# =============================================================================
# Game Prep Bonus
# =============================================================================

@dataclass
class GamePrepBonus:
    """
    Temporary bonus from studying an opponent.

    Created during practice when allocating time to "Game Prep".
    Applies to the next scheduled game against the specified opponent.
    Expires after the game week passes.
    """

    opponent_id: Optional[UUID]    # UUID of the opponent team
    opponent_name: str             # Display name of opponent
    prep_level: float              # 0.0-1.0 (how much prep done)
    week: int                      # Game week this prep is for
    created_at: datetime = field(default_factory=datetime.now)

    # Calculated bonuses (set based on prep_level)
    scheme_recognition: float = 0.0   # Bonus to play recognition
    execution_bonus: float = 0.0      # Bonus to execution

    def __post_init__(self) -> None:
        """Calculate bonuses based on prep level."""
        self._update_bonuses()

    def _update_bonuses(self) -> None:
        """Recalculate bonuses from current prep level."""
        self.scheme_recognition = self.prep_level * MAX_SCHEME_BONUS
        self.execution_bonus = self.prep_level * MAX_EXECUTION_BONUS

    def add_prep(self, additional_level: float) -> None:
        """
        Add more preparation (with diminishing returns).

        Multiple practice sessions can stack, but returns diminish
        as you approach 100% preparation.

        Args:
            additional_level: Amount of prep to add (0.0-1.0)
        """
        # Diminishing returns: remaining capacity * contribution
        remaining = 1.0 - self.prep_level
        effective_gain = remaining * additional_level
        self.prep_level = min(1.0, self.prep_level + effective_gain)
        self._update_bonuses()

    def get_total_bonus(self) -> float:
        """
        Get combined bonus modifier.

        Returns:
            Multiplier to apply to relevant checks (1.0 = no bonus)
        """
        return 1.0 + (self.scheme_recognition + self.execution_bonus) / 2

    def get_scheme_multiplier(self) -> float:
        """Get multiplier for play recognition/awareness checks."""
        return 1.0 + self.scheme_recognition

    def get_execution_multiplier(self) -> float:
        """Get multiplier for execution/accuracy checks."""
        return 1.0 + self.execution_bonus

    def is_expired(self, current_week: int) -> bool:
        """
        Check if this prep bonus has expired.

        Prep expires after the game week it was intended for.

        Args:
            current_week: Current game week

        Returns:
            True if prep should be cleared
        """
        return current_week > self.week

    def is_valid_for_opponent(self, opponent_id: UUID) -> bool:
        """
        Check if this prep applies to a specific opponent.

        Args:
            opponent_id: UUID of the opponent to check

        Returns:
            True if this prep was for the given opponent
        """
        return self.opponent_id == opponent_id

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "opponent_id": str(self.opponent_id) if self.opponent_id else None,
            "opponent_name": self.opponent_name,
            "prep_level": self.prep_level,
            "week": self.week,
            "created_at": self.created_at.isoformat(),
            "scheme_recognition": self.scheme_recognition,
            "execution_bonus": self.execution_bonus,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GamePrepBonus":
        """Create from dictionary."""
        opponent_id = None
        if data.get("opponent_id"):
            opponent_id = UUID(data["opponent_id"])

        created_at = datetime.now()
        if "created_at" in data:
            try:
                created_at = datetime.fromisoformat(data["created_at"])
            except (ValueError, TypeError):
                pass

        bonus = cls(
            opponent_id=opponent_id,
            opponent_name=data.get("opponent_name", "Unknown"),
            prep_level=data.get("prep_level", 0.0),
            week=data.get("week", 0),
            created_at=created_at,
        )
        # Restore calculated values (or recalculate)
        bonus.scheme_recognition = data.get("scheme_recognition", 0.0)
        bonus.execution_bonus = data.get("execution_bonus", 0.0)
        return bonus


# =============================================================================
# Helper Functions
# =============================================================================

def calculate_prep_level(reps: int) -> float:
    """
    Calculate prep level from number of game prep reps.

    Args:
        reps: Number of reps allocated to game prep

    Returns:
        Prep level from 0.0 to 1.0
    """
    return min(1.0, reps / MAX_PREP_REPS)


def create_game_prep(
    opponent_id: Optional[UUID],
    opponent_name: str,
    week: int,
    reps: int,
) -> GamePrepBonus:
    """
    Create a new game prep bonus.

    Args:
        opponent_id: UUID of the opponent team
        opponent_name: Display name of opponent
        week: Game week this prep is for
        reps: Number of reps allocated to game prep

    Returns:
        New GamePrepBonus instance
    """
    prep_level = calculate_prep_level(reps)
    return GamePrepBonus(
        opponent_id=opponent_id,
        opponent_name=opponent_name,
        prep_level=prep_level,
        week=week,
    )


def apply_prep_bonus(
    existing: Optional[GamePrepBonus],
    opponent_id: Optional[UUID],
    opponent_name: str,
    week: int,
    reps: int,
) -> GamePrepBonus:
    """
    Apply game prep reps, creating or updating a bonus.

    If prep already exists for this week, adds to it with diminishing returns.
    If prep is for a different week/opponent, creates new prep.

    Args:
        existing: Existing game prep bonus (or None)
        opponent_id: UUID of the opponent team
        opponent_name: Display name of opponent
        week: Game week this prep is for
        reps: Number of reps allocated to game prep

    Returns:
        Updated or new GamePrepBonus
    """
    additional_prep = calculate_prep_level(reps)

    if existing and existing.week == week:
        # Add to existing prep for same game
        existing.add_prep(additional_prep)
        return existing
    else:
        # New prep (different week or first prep)
        return GamePrepBonus(
            opponent_id=opponent_id,
            opponent_name=opponent_name,
            prep_level=additional_prep,
            week=week,
        )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "MAX_PREP_REPS",
    "MAX_SCHEME_BONUS",
    "MAX_EXECUTION_BONUS",
    "GamePrepBonus",
    "calculate_prep_level",
    "create_game_prep",
    "apply_prep_bonus",
]
