"""
Blocking assignments and engagement tracking.

Tracks who is blocking whom, including double teams.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum

from .vec2 import Vec2
from .player import Player, PlayerRole


class BlockType(str, Enum):
    """Type of block being executed."""
    SINGLE = "single"           # 1v1 block
    DOUBLE_POST = "double_post" # Double team - absorbing/controlling
    DOUBLE_DRIVE = "double_drive"  # Double team - driving/pushing
    CHIP = "chip"               # Quick help then release
    NONE = "none"               # Not blocking anyone


@dataclass
class BlockAssignment:
    """A blocker's current assignment."""
    blocker_id: str
    target_id: Optional[str]  # Who to block (None = no assignment)
    block_type: BlockType = BlockType.NONE
    partner_id: Optional[str] = None  # Double team partner

    @property
    def is_double_team(self) -> bool:
        return self.block_type in (BlockType.DOUBLE_POST, BlockType.DOUBLE_DRIVE)


@dataclass
class DoubleTeam:
    """A double team engagement."""
    target_id: str           # The DL being doubled
    post_blocker_id: str     # Blocker absorbing force (inside)
    drive_blocker_id: str    # Blocker pushing (outside)

    # Status
    active: bool = True
    ticks_active: int = 0

    # Which side the drive is coming from (left = -1, right = 1)
    drive_direction: float = 1.0


@dataclass
class AssignmentTracker:
    """
    Tracks all blocking assignments in the simulation.

    Handles:
    - 1v1 matchups
    - Double teams
    - Assignment changes (when DL sheds, blocker picks up new target)
    """

    # Current assignments: blocker_id -> assignment
    assignments: Dict[str, BlockAssignment] = field(default_factory=dict)

    # Active double teams: target_id -> DoubleTeam
    double_teams: Dict[str, DoubleTeam] = field(default_factory=dict)

    # Who each DL is engaged with (can be multiple blockers)
    dl_engagements: Dict[str, Set[str]] = field(default_factory=dict)

    def assign_single_block(self, blocker_id: str, target_id: str) -> None:
        """Assign a 1v1 block."""
        self.assignments[blocker_id] = BlockAssignment(
            blocker_id=blocker_id,
            target_id=target_id,
            block_type=BlockType.SINGLE,
        )

        # Track DL engagement
        if target_id not in self.dl_engagements:
            self.dl_engagements[target_id] = set()
        self.dl_engagements[target_id].add(blocker_id)

    def assign_double_team(self, post_id: str, drive_id: str, target_id: str,
                          drive_direction: float = 1.0) -> None:
        """
        Assign a double team.

        Args:
            post_id: Blocker who absorbs/posts (usually aligned on DL)
            drive_id: Blocker who drives (usually adjacent)
            target_id: DL being doubled
            drive_direction: -1 for drive from left, +1 for drive from right
        """
        # Update assignments
        self.assignments[post_id] = BlockAssignment(
            blocker_id=post_id,
            target_id=target_id,
            block_type=BlockType.DOUBLE_POST,
            partner_id=drive_id,
        )
        self.assignments[drive_id] = BlockAssignment(
            blocker_id=drive_id,
            target_id=target_id,
            block_type=BlockType.DOUBLE_DRIVE,
            partner_id=post_id,
        )

        # Create double team tracking
        self.double_teams[target_id] = DoubleTeam(
            target_id=target_id,
            post_blocker_id=post_id,
            drive_blocker_id=drive_id,
            drive_direction=drive_direction,
        )

        # Track DL engagements
        if target_id not in self.dl_engagements:
            self.dl_engagements[target_id] = set()
        self.dl_engagements[target_id].add(post_id)
        self.dl_engagements[target_id].add(drive_id)

    def release_from_double(self, blocker_id: str) -> None:
        """Release a blocker from a double team (e.g., to pick up a linebacker)."""
        if blocker_id not in self.assignments:
            return

        assignment = self.assignments[blocker_id]
        if not assignment.is_double_team:
            return

        target_id = assignment.target_id
        partner_id = assignment.partner_id

        # Remove from double team
        if target_id in self.double_teams:
            del self.double_teams[target_id]

        # Update engagements
        if target_id in self.dl_engagements:
            self.dl_engagements[target_id].discard(blocker_id)

        # Convert partner to single block
        if partner_id and partner_id in self.assignments:
            self.assignments[partner_id] = BlockAssignment(
                blocker_id=partner_id,
                target_id=target_id,
                block_type=BlockType.SINGLE,
            )

        # Clear released blocker's assignment
        self.assignments[blocker_id] = BlockAssignment(
            blocker_id=blocker_id,
            target_id=None,
            block_type=BlockType.NONE,
        )

    def clear_assignment(self, blocker_id: str) -> None:
        """Clear a blocker's assignment (e.g., when DL sheds)."""
        if blocker_id not in self.assignments:
            return

        assignment = self.assignments[blocker_id]
        target_id = assignment.target_id

        # If in double team, release properly
        if assignment.is_double_team:
            self.release_from_double(blocker_id)
        else:
            # Clear engagement tracking
            if target_id and target_id in self.dl_engagements:
                self.dl_engagements[target_id].discard(blocker_id)

            self.assignments[blocker_id] = BlockAssignment(
                blocker_id=blocker_id,
                target_id=None,
                block_type=BlockType.NONE,
            )

    def get_assignment(self, blocker_id: str) -> Optional[BlockAssignment]:
        """Get a blocker's current assignment."""
        return self.assignments.get(blocker_id)

    def get_blockers_on(self, dl_id: str) -> Set[str]:
        """Get all blockers currently engaged with a DL."""
        return self.dl_engagements.get(dl_id, set())

    def is_double_teamed(self, dl_id: str) -> bool:
        """Check if a DL is being double-teamed."""
        return dl_id in self.double_teams and self.double_teams[dl_id].active

    def get_double_team(self, dl_id: str) -> Optional[DoubleTeam]:
        """Get the double team info for a DL."""
        return self.double_teams.get(dl_id)

    def get_unblocked_rushers(self, all_rushers: List[str]) -> List[str]:
        """Get list of rushers with no one blocking them."""
        unblocked = []
        for rusher_id in all_rushers:
            blockers = self.dl_engagements.get(rusher_id, set())
            if not blockers:
                unblocked.append(rusher_id)
        return unblocked
