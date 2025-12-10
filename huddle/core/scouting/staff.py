"""
Scouting staff system.

Manages scouts and their impact on scouting accuracy.
Better scouts produce more accurate projections and reveal
hidden traits more reliably.
"""

from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID, uuid4
from enum import Enum
import random

from huddle.core.scouting.stages import ScoutingLevel


class ScoutSpecialty(Enum):
    """
    Scout specialization areas.

    Scouts with matching specialties get accuracy bonuses.
    """
    # Position group specialties
    QUARTERBACKS = "quarterbacks"
    SKILL_POSITIONS = "skill_positions"  # RB, WR, TE
    OFFENSIVE_LINE = "offensive_line"
    DEFENSIVE_LINE = "defensive_line"
    LINEBACKERS = "linebackers"
    SECONDARY = "secondary"

    # Regional specialties (for college scouting)
    SOUTHEAST = "southeast"  # SEC
    MIDWEST = "midwest"  # Big Ten
    WEST_COAST = "west_coast"  # Pac-12
    SOUTHWEST = "southwest"  # Big 12
    NORTHEAST = "northeast"  # ACC, Big East

    # General
    GENERAL = "general"


# Which positions each specialty covers
SPECIALTY_POSITIONS: dict[ScoutSpecialty, list[str]] = {
    ScoutSpecialty.QUARTERBACKS: ["QB"],
    ScoutSpecialty.SKILL_POSITIONS: ["RB", "FB", "WR", "TE"],
    ScoutSpecialty.OFFENSIVE_LINE: ["LT", "LG", "C", "RG", "RT"],
    ScoutSpecialty.DEFENSIVE_LINE: ["DE", "DT", "NT"],
    ScoutSpecialty.LINEBACKERS: ["MLB", "OLB", "ILB"],
    ScoutSpecialty.SECONDARY: ["CB", "FS", "SS"],
    ScoutSpecialty.GENERAL: [],  # Covers all but no bonus
}


@dataclass
class Scout:
    """
    A member of the scouting staff.

    Each scout has a skill level and specialty that affects
    their accuracy when evaluating players.
    """
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    level: ScoutingLevel = ScoutingLevel.AVERAGE
    specialty: ScoutSpecialty = ScoutSpecialty.GENERAL
    experience_years: int = 0

    # Hidden "true" skill (affects actual accuracy)
    # Player only sees the level, not the exact skill
    _skill: int = 50  # 1-99 scale

    @property
    def skill(self) -> int:
        """Scout's actual skill rating."""
        return self._skill

    def get_accuracy_for_position(self, position: str) -> ScoutingLevel:
        """
        Get effective accuracy level for a specific position.

        Scouts get a bonus when evaluating their specialty.
        """
        # Check if position matches specialty
        specialty_positions = SPECIALTY_POSITIONS.get(self.specialty, [])

        if position in specialty_positions:
            # Specialty bonus - treat as one level higher
            level_order = [
                ScoutingLevel.ROOKIE,
                ScoutingLevel.AVERAGE,
                ScoutingLevel.EXPERIENCED,
                ScoutingLevel.ELITE,
            ]
            current_idx = level_order.index(self.level)
            upgraded_idx = min(current_idx + 1, len(level_order) - 1)
            return level_order[upgraded_idx]

        return self.level

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "level": self.level.value,
            "specialty": self.specialty.value,
            "experience_years": self.experience_years,
            "_skill": self._skill,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Scout":
        return cls(
            id=UUID(data["id"]) if "id" in data else uuid4(),
            name=data.get("name", ""),
            level=ScoutingLevel(data.get("level", "average")),
            specialty=ScoutSpecialty(data.get("specialty", "general")),
            experience_years=data.get("experience_years", 0),
            _skill=data.get("_skill", 50),
        )

    @classmethod
    def generate_random(cls, name: str = "") -> "Scout":
        """Generate a random scout."""
        skill = random.randint(30, 90)

        # Determine level from skill
        if skill >= 80:
            level = ScoutingLevel.ELITE
        elif skill >= 65:
            level = ScoutingLevel.EXPERIENCED
        elif skill >= 45:
            level = ScoutingLevel.AVERAGE
        else:
            level = ScoutingLevel.ROOKIE

        return cls(
            name=name or _generate_scout_name(),
            level=level,
            specialty=random.choice(list(ScoutSpecialty)),
            experience_years=random.randint(0, 25),
            _skill=skill,
        )


@dataclass
class ScoutingDepartment:
    """
    A team's scouting department.

    Manages all scouts and their assignments.
    """
    scouts: list[Scout] = field(default_factory=list)
    budget: int = 100  # Scouting budget points per season
    budget_spent: int = 0

    @property
    def remaining_budget(self) -> int:
        return self.budget - self.budget_spent

    @property
    def average_skill(self) -> float:
        """Average skill of all scouts."""
        if not self.scouts:
            return 50.0
        return sum(s.skill for s in self.scouts) / len(self.scouts)

    @property
    def best_scout(self) -> Optional[Scout]:
        """Get the highest-skilled scout."""
        if not self.scouts:
            return None
        return max(self.scouts, key=lambda s: s.skill)

    def get_scout_for_position(self, position: str) -> Scout:
        """
        Get the best scout for evaluating a specific position.

        Considers specialty bonuses.
        """
        if not self.scouts:
            # Return a default average scout
            return Scout(level=ScoutingLevel.AVERAGE)

        best = None
        best_score = -1

        for scout in self.scouts:
            # Base score from skill
            score = scout.skill

            # Bonus for specialty match
            specialty_positions = SPECIALTY_POSITIONS.get(scout.specialty, [])
            if position in specialty_positions:
                score += 15

            if score > best_score:
                best_score = score
                best = scout

        return best or self.scouts[0]

    def spend_budget(self, amount: int) -> bool:
        """
        Spend scouting budget.

        Returns True if successful, False if insufficient funds.
        """
        if amount > self.remaining_budget:
            return False
        self.budget_spent += amount
        return True

    def reset_budget(self) -> None:
        """Reset budget for new season."""
        self.budget_spent = 0

    def add_scout(self, scout: Scout) -> None:
        """Add a scout to the department."""
        self.scouts.append(scout)

    def remove_scout(self, scout_id: UUID) -> Optional[Scout]:
        """Remove a scout by ID."""
        for i, scout in enumerate(self.scouts):
            if scout.id == scout_id:
                return self.scouts.pop(i)
        return None

    def to_dict(self) -> dict:
        return {
            "scouts": [s.to_dict() for s in self.scouts],
            "budget": self.budget,
            "budget_spent": self.budget_spent,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScoutingDepartment":
        return cls(
            scouts=[Scout.from_dict(s) for s in data.get("scouts", [])],
            budget=data.get("budget", 100),
            budget_spent=data.get("budget_spent", 0),
        )

    @classmethod
    def generate_default(cls) -> "ScoutingDepartment":
        """Generate a default scouting department with basic staff."""
        dept = cls()

        # Add 3-5 scouts with various specialties
        num_scouts = random.randint(3, 5)
        for _ in range(num_scouts):
            dept.add_scout(Scout.generate_random())

        return dept


# Name generation helpers
_FIRST_NAMES = [
    "Mike", "John", "Dave", "Tom", "Steve", "Bill", "Bob", "Jim",
    "Chris", "Matt", "Dan", "Joe", "Mark", "Paul", "Pete", "Greg",
    "Tony", "Frank", "Rick", "Gary", "Ron", "Jeff", "Brian", "Kevin",
]

_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Davis", "Miller",
    "Wilson", "Moore", "Taylor", "Anderson", "Thomas", "Jackson", "White",
    "Harris", "Martin", "Thompson", "Garcia", "Martinez", "Robinson",
    "Clark", "Rodriguez", "Lewis", "Lee", "Walker", "Hall", "Allen",
]


def _generate_scout_name() -> str:
    """Generate a random scout name."""
    return f"{random.choice(_FIRST_NAMES)} {random.choice(_LAST_NAMES)}"
