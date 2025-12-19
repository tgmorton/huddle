"""
Play Knowledge Tracking.

Tracks per-player, per-play mastery levels using the HC09-style
UNLEARNED → LEARNED → MASTERED progression system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Optional
from uuid import UUID


class MasteryLevel(Enum):
    """
    Mastery tiers matching HC09.

    UNLEARNED: Player doesn't know the play - high chance of mistakes
    LEARNED: Player knows the play - normal execution
    MASTERED: Player has instinctive knowledge - bonus to execution
    """
    UNLEARNED = "unlearned"
    LEARNED = "learned"
    MASTERED = "mastered"

    def __lt__(self, other: "MasteryLevel") -> bool:
        order = [MasteryLevel.UNLEARNED, MasteryLevel.LEARNED, MasteryLevel.MASTERED]
        return order.index(self) < order.index(other)

    def __le__(self, other: "MasteryLevel") -> bool:
        return self == other or self < other


# Execution modifiers by mastery level
MASTERY_MODIFIERS: Dict[MasteryLevel, float] = {
    MasteryLevel.UNLEARNED: 0.85,  # -15% to relevant attributes
    MasteryLevel.LEARNED: 1.0,     # Normal execution
    MasteryLevel.MASTERED: 1.10,   # +10% to relevant attributes
}


@dataclass
class PlayMastery:
    """
    Knowledge state for a single play.

    Tracks the player's mastery level and progress toward the next tier.
    Progress is 0.0-1.0 within each tier; when it reaches 1.0, the player
    advances to the next tier.

    Attributes:
        play_code: The play identifier (e.g., "RUN_POWER")
        level: Current mastery tier
        progress: Progress toward next tier (0.0-1.0)
        reps: Total practice reps accumulated
        last_practiced: When this play was last practiced
        game_reps: Times this play was called in games (slows decay)
    """
    play_code: str
    level: MasteryLevel = MasteryLevel.UNLEARNED
    progress: float = 0.0
    reps: int = 0
    last_practiced: Optional[datetime] = None
    game_reps: int = 0

    def get_execution_modifier(self) -> float:
        """
        Get the attribute modifier for play execution.

        Returns:
            Multiplier for relevant attributes (0.85, 1.0, or 1.1)
        """
        return MASTERY_MODIFIERS[self.level]

    @property
    def is_learned(self) -> bool:
        """Check if player has at least learned the play."""
        return self.level in (MasteryLevel.LEARNED, MasteryLevel.MASTERED)

    @property
    def is_mastered(self) -> bool:
        """Check if player has mastered the play."""
        return self.level == MasteryLevel.MASTERED

    @property
    def display_progress(self) -> str:
        """Human-readable progress display."""
        if self.level == MasteryLevel.MASTERED:
            return "MASTERED"
        elif self.level == MasteryLevel.LEARNED:
            return f"Learned ({int(self.progress * 100)}% to Master)"
        else:
            return f"Unlearned ({int(self.progress * 100)}% to Learn)"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "play_code": self.play_code,
            "level": self.level.value,
            "progress": self.progress,
            "reps": self.reps,
            "last_practiced": self.last_practiced.isoformat() if self.last_practiced else None,
            "game_reps": self.game_reps,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlayMastery":
        """Create from dictionary."""
        last_practiced = None
        if data.get("last_practiced"):
            last_practiced = datetime.fromisoformat(data["last_practiced"])

        return cls(
            play_code=data["play_code"],
            level=MasteryLevel(data.get("level", "unlearned")),
            progress=data.get("progress", 0.0),
            reps=data.get("reps", 0),
            last_practiced=last_practiced,
            game_reps=data.get("game_reps", 0),
        )


@dataclass
class PlayerPlayKnowledge:
    """
    All play knowledge for a single player.

    Tracks mastery state for every play the player has encountered.
    Players only need to track plays relevant to their position.

    Attributes:
        player_id: The player's unique identifier
        plays: Dict mapping play_code to PlayMastery
    """
    player_id: UUID
    plays: Dict[str, PlayMastery] = field(default_factory=dict)

    def get_mastery(self, play_code: str) -> PlayMastery:
        """
        Get mastery for a play, creating if needed.

        New plays start at UNLEARNED with 0 progress.
        """
        if play_code not in self.plays:
            self.plays[play_code] = PlayMastery(play_code=play_code)
        return self.plays[play_code]

    def get_execution_modifier(self, play_code: str) -> float:
        """
        Get execution modifier for a specific play.

        Returns 1.0 (neutral) for unknown plays.
        """
        if play_code not in self.plays:
            # Unknown play = treat as unlearned
            return MASTERY_MODIFIERS[MasteryLevel.UNLEARNED]
        return self.plays[play_code].get_execution_modifier()

    def get_mastery_level(self, play_code: str) -> MasteryLevel:
        """Get the mastery level for a play."""
        return self.get_mastery(play_code).level

    def knows_play(self, play_code: str) -> bool:
        """Check if player has at least learned the play."""
        if play_code not in self.plays:
            return False
        return self.plays[play_code].is_learned

    def has_mastered(self, play_code: str) -> bool:
        """Check if player has mastered the play."""
        if play_code not in self.plays:
            return False
        return self.plays[play_code].is_mastered

    def get_learned_plays(self) -> list[str]:
        """Get list of play codes the player has learned."""
        return [
            code for code, mastery in self.plays.items()
            if mastery.is_learned
        ]

    def get_mastered_plays(self) -> list[str]:
        """Get list of play codes the player has mastered."""
        return [
            code for code, mastery in self.plays.items()
            if mastery.is_mastered
        ]

    def get_playbook_readiness(self, playbook_codes: set[str]) -> float:
        """
        Calculate readiness percentage for a set of plays.

        Returns the percentage of plays that are at least learned.
        """
        if not playbook_codes:
            return 1.0

        learned_count = sum(
            1 for code in playbook_codes
            if self.knows_play(code)
        )
        return learned_count / len(playbook_codes)

    def get_average_modifier(self, play_codes: set[str]) -> float:
        """
        Get average execution modifier across a set of plays.

        Useful for calculating overall offensive/defensive readiness.
        """
        if not play_codes:
            return 1.0

        total = sum(self.get_execution_modifier(code) for code in play_codes)
        return total / len(play_codes)

    def count_by_level(self) -> Dict[MasteryLevel, int]:
        """Count plays at each mastery level."""
        counts = {level: 0 for level in MasteryLevel}
        for mastery in self.plays.values():
            counts[mastery.level] += 1
        return counts

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "player_id": str(self.player_id),
            "plays": {code: mastery.to_dict() for code, mastery in self.plays.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerPlayKnowledge":
        """Create from dictionary."""
        plays = {}
        for code, mastery_data in data.get("plays", {}).items():
            plays[code] = PlayMastery.from_dict(mastery_data)

        return cls(
            player_id=UUID(data["player_id"]),
            plays=plays,
        )

    def __str__(self) -> str:
        counts = self.count_by_level()
        return (
            f"PlayerPlayKnowledge("
            f"unlearned={counts[MasteryLevel.UNLEARNED]}, "
            f"learned={counts[MasteryLevel.LEARNED]}, "
            f"mastered={counts[MasteryLevel.MASTERED]})"
        )
