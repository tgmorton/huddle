"""
Team Playbook.

Defines which plays a team can run. Players only need to learn
plays that are in their team's active playbook.
"""

from dataclasses import dataclass, field
from typing import Set, Optional
from uuid import UUID

from huddle.core.playbook.play_codes import (
    ALL_PLAYS,
    OFFENSIVE_PLAYS,
    DEFENSIVE_PLAYS,
    DEFAULT_OFFENSIVE_PLAYBOOK,
    DEFAULT_DEFENSIVE_PLAYBOOK,
    PlayCode,
    PlayCategory,
)


@dataclass
class Playbook:
    """
    A team's active playbook.

    Contains the set of offensive and defensive plays the team
    can run. Players need to learn plays in the playbook to
    execute them effectively.

    Attributes:
        team_id: The team this playbook belongs to
        offensive_plays: Set of offensive play codes
        defensive_plays: Set of defensive play codes
        offensive_scheme: Team's offensive scheme identity
        defensive_scheme: Team's defensive scheme identity
    """
    team_id: UUID
    offensive_plays: Set[str] = field(default_factory=set)
    defensive_plays: Set[str] = field(default_factory=set)
    offensive_scheme: str = "PRO_STYLE"
    defensive_scheme: str = "DEFENSE_4_3"

    @classmethod
    def default(cls, team_id: UUID) -> "Playbook":
        """
        Create a default playbook with standard plays.

        This gives teams a balanced starting playbook that
        covers the basics without being overwhelming.
        """
        return cls(
            team_id=team_id,
            offensive_plays=DEFAULT_OFFENSIVE_PLAYBOOK.copy(),
            defensive_plays=DEFAULT_DEFENSIVE_PLAYBOOK.copy(),
        )

    @classmethod
    def empty(cls, team_id: UUID) -> "Playbook":
        """Create an empty playbook (for new schemes/rebuilds)."""
        return cls(team_id=team_id)

    @property
    def all_plays(self) -> Set[str]:
        """Get all plays in the playbook."""
        return self.offensive_plays | self.defensive_plays

    @property
    def offensive_play_count(self) -> int:
        """Number of offensive plays."""
        return len(self.offensive_plays)

    @property
    def defensive_play_count(self) -> int:
        """Number of defensive plays."""
        return len(self.defensive_plays)

    @property
    def total_play_count(self) -> int:
        """Total number of plays."""
        return len(self.all_plays)

    def has_play(self, play_code: str) -> bool:
        """Check if a play is in the playbook."""
        return play_code in self.all_plays

    def get_play(self, play_code: str) -> Optional[PlayCode]:
        """Get play definition if it's in the playbook."""
        if play_code in self.all_plays:
            return ALL_PLAYS.get(play_code)
        return None

    def install_play(self, play_code: str) -> bool:
        """
        Add a play to the playbook.

        Returns True if play was added, False if invalid or already present.
        """
        play = ALL_PLAYS.get(play_code)
        if not play:
            return False

        if play.category == PlayCategory.DEFENSE:
            if play_code in self.defensive_plays:
                return False
            self.defensive_plays.add(play_code)
        else:
            if play_code in self.offensive_plays:
                return False
            self.offensive_plays.add(play_code)

        return True

    def remove_play(self, play_code: str) -> bool:
        """
        Remove a play from the playbook.

        Returns True if play was removed, False if not present.
        """
        if play_code in self.offensive_plays:
            self.offensive_plays.remove(play_code)
            return True
        if play_code in self.defensive_plays:
            self.defensive_plays.remove(play_code)
            return True
        return False

    def get_run_plays(self) -> Set[str]:
        """Get all run plays in the offensive playbook."""
        return {
            code for code in self.offensive_plays
            if ALL_PLAYS.get(code) and ALL_PLAYS[code].category == PlayCategory.RUN
        }

    def get_pass_plays(self) -> Set[str]:
        """Get all pass plays in the offensive playbook."""
        return {
            code for code in self.offensive_plays
            if ALL_PLAYS.get(code) and ALL_PLAYS[code].category == PlayCategory.PASS
        }

    def get_plays_for_position(self, position: str) -> Set[str]:
        """Get all plays that involve a specific position."""
        return {
            code for code in self.all_plays
            if ALL_PLAYS.get(code) and position in ALL_PLAYS[code].positions_involved
        }

    def get_average_complexity(self) -> float:
        """Get average complexity of all plays in playbook."""
        if not self.all_plays:
            return 0.0

        total = sum(
            ALL_PLAYS[code].complexity
            for code in self.all_plays
            if code in ALL_PLAYS
        )
        return total / len(self.all_plays)

    def get_complexity_distribution(self) -> dict[int, int]:
        """Get count of plays at each complexity level."""
        dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for code in self.all_plays:
            play = ALL_PLAYS.get(code)
            if play:
                dist[play.complexity] += 1
        return dist

    def validate(self) -> list[str]:
        """
        Validate the playbook.

        Returns list of any invalid play codes.
        """
        invalid = []
        for code in self.offensive_plays:
            if code not in OFFENSIVE_PLAYS:
                invalid.append(code)
        for code in self.defensive_plays:
            if code not in DEFENSIVE_PLAYS:
                invalid.append(code)
        return invalid

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "team_id": str(self.team_id),
            "offensive_plays": list(self.offensive_plays),
            "defensive_plays": list(self.defensive_plays),
            "offensive_scheme": self.offensive_scheme,
            "defensive_scheme": self.defensive_scheme,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Playbook":
        """Create from dictionary."""
        return cls(
            team_id=UUID(data["team_id"]),
            offensive_plays=set(data.get("offensive_plays", [])),
            defensive_plays=set(data.get("defensive_plays", [])),
            offensive_scheme=data.get("offensive_scheme", "PRO_STYLE"),
            defensive_scheme=data.get("defensive_scheme", "DEFENSE_4_3"),
        )

    def __str__(self) -> str:
        return (
            f"Playbook(offense={self.offensive_play_count} plays, "
            f"defense={self.defensive_play_count} plays)"
        )
