"""
Draft Board - User's personal draft prospect rankings.

Tracks which prospects the user has added to their board,
their rank order, and tier assignments.
"""

from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID


@dataclass
class BoardEntry:
    """A single prospect on the user's draft board."""

    prospect_id: UUID
    rank: int  # 1-based position on board
    tier: int = 3  # 1=Elite, 2=Great, 3=Good, 4=Solid, 5=Flier
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "prospect_id": str(self.prospect_id),
            "rank": self.rank,
            "tier": self.tier,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BoardEntry":
        return cls(
            prospect_id=UUID(data["prospect_id"]),
            rank=data["rank"],
            tier=data.get("tier", 3),
            notes=data.get("notes", ""),
        )


@dataclass
class DraftBoard:
    """
    User's draft board - personal rankings of prospects.

    The board is ordered by rank (1 = top prospect).
    Users can assign tiers independently of rank for grouping.
    """

    entries: list[BoardEntry] = field(default_factory=list)

    def add_prospect(self, prospect_id: UUID, tier: int = 3) -> BoardEntry:
        """Add a prospect to the end of the board."""
        # Check if already on board
        if self.has_prospect(prospect_id):
            raise ValueError(f"Prospect {prospect_id} already on board")

        # Add at end
        rank = len(self.entries) + 1
        entry = BoardEntry(prospect_id=prospect_id, rank=rank, tier=tier)
        self.entries.append(entry)
        return entry

    def remove_prospect(self, prospect_id: UUID) -> bool:
        """Remove a prospect from the board. Returns True if found."""
        for i, entry in enumerate(self.entries):
            if entry.prospect_id == prospect_id:
                self.entries.pop(i)
                # Reorder remaining entries
                self._reindex()
                return True
        return False

    def has_prospect(self, prospect_id: UUID) -> bool:
        """Check if a prospect is on the board."""
        return any(e.prospect_id == prospect_id for e in self.entries)

    def get_entry(self, prospect_id: UUID) -> Optional[BoardEntry]:
        """Get the board entry for a prospect."""
        for entry in self.entries:
            if entry.prospect_id == prospect_id:
                return entry
        return None

    def set_tier(self, prospect_id: UUID, tier: int) -> bool:
        """Set the tier for a prospect. Returns True if found."""
        entry = self.get_entry(prospect_id)
        if entry:
            entry.tier = max(1, min(5, tier))  # Clamp to 1-5
            return True
        return False

    def set_notes(self, prospect_id: UUID, notes: str) -> bool:
        """Set notes for a prospect. Returns True if found."""
        entry = self.get_entry(prospect_id)
        if entry:
            entry.notes = notes
            return True
        return False

    def reorder(self, prospect_id: UUID, new_rank: int) -> bool:
        """
        Move a prospect to a new rank position.
        All other prospects shift accordingly.
        Returns True if found and moved.
        """
        # Find current position
        current_idx = None
        for i, entry in enumerate(self.entries):
            if entry.prospect_id == prospect_id:
                current_idx = i
                break

        if current_idx is None:
            return False

        # Clamp new rank
        new_rank = max(1, min(len(self.entries), new_rank))
        new_idx = new_rank - 1

        if new_idx == current_idx:
            return True  # No change needed

        # Remove and reinsert
        entry = self.entries.pop(current_idx)
        self.entries.insert(new_idx, entry)
        self._reindex()
        return True

    def move_before(self, prospect_id: UUID, before_prospect_id: UUID) -> bool:
        """Move prospect to position just before another prospect."""
        # Find positions
        moving_idx = None
        target_idx = None
        for i, entry in enumerate(self.entries):
            if entry.prospect_id == prospect_id:
                moving_idx = i
            if entry.prospect_id == before_prospect_id:
                target_idx = i

        if moving_idx is None or target_idx is None:
            return False

        if moving_idx == target_idx:
            return True

        # Remove the moving entry
        entry = self.entries.pop(moving_idx)

        # Adjust target index if we removed before it
        if moving_idx < target_idx:
            target_idx -= 1

        # Insert before target
        self.entries.insert(target_idx, entry)
        self._reindex()
        return True

    def _reindex(self) -> None:
        """Update rank values to match list order."""
        for i, entry in enumerate(self.entries):
            entry.rank = i + 1

    def get_by_tier(self, tier: int) -> list[BoardEntry]:
        """Get all entries for a specific tier, in rank order."""
        return [e for e in self.entries if e.tier == tier]

    def clear(self) -> None:
        """Remove all prospects from the board."""
        self.entries.clear()

    @property
    def count(self) -> int:
        """Number of prospects on the board."""
        return len(self.entries)

    def to_dict(self) -> dict:
        return {
            "entries": [e.to_dict() for e in self.entries],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DraftBoard":
        return cls(
            entries=[BoardEntry.from_dict(e) for e in data.get("entries", [])],
        )
