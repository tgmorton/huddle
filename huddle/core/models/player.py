"""Player model."""

from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID, uuid4

from huddle.core.attributes import PlayerAttributes
from huddle.core.enums import Position


@dataclass
class Player:
    """
    Represents an individual football player.

    Players have attributes that affect their performance in simulation.
    The overall rating is calculated based on position-weighted attributes.
    """

    id: UUID = field(default_factory=uuid4)
    first_name: str = ""
    last_name: str = ""
    position: Position = Position.QB
    attributes: PlayerAttributes = field(default_factory=PlayerAttributes)

    # Physical info
    age: int = 22
    height_inches: int = 72  # 6'0"
    weight_lbs: int = 200
    jersey_number: int = 0

    # Jersey number preferences (in order of preference)
    # When joining a team, player tries to get these numbers
    preferred_jersey_numbers: list[int] = field(default_factory=list)

    # Career info
    experience_years: int = 0  # Total NFL experience
    years_on_team: int = 0  # Tenure with current team (affects jersey priority)

    # Optional metadata for different management levels
    college: Optional[str] = None
    draft_year: Optional[int] = None
    draft_round: Optional[int] = None
    draft_pick: Optional[int] = None

    # Contract info (for pro level)
    contract_years: Optional[int] = None
    contract_year_remaining: Optional[int] = None  # Years left on current deal
    salary: Optional[int] = None  # Annual salary (in thousands)
    signing_bonus: Optional[int] = None  # Total signing bonus
    signing_bonus_remaining: Optional[int] = None  # Prorated bonus remaining (for dead money)

    @property
    def overall(self) -> int:
        """Calculate overall rating based on position."""
        return self.attributes.calculate_overall(self.position.value)

    @property
    def potential(self) -> int:
        """Player's potential ceiling rating."""
        return self.attributes.get("potential", self.overall)

    @property
    def full_name(self) -> str:
        """Full name of the player."""
        return f"{self.first_name} {self.last_name}"

    @property
    def display_name(self) -> str:
        """Short display name (e.g., 'T. Brady')."""
        if self.first_name:
            return f"{self.first_name[0]}. {self.last_name}"
        return self.last_name

    @property
    def height_display(self) -> str:
        """Height in feet and inches (e.g., 6'2\")."""
        feet = self.height_inches // 12
        inches = self.height_inches % 12
        return f"{feet}'{inches}\""

    @property
    def is_rookie(self) -> bool:
        """Check if player is a rookie (0 years experience)."""
        return self.experience_years == 0

    @property
    def is_veteran(self) -> bool:
        """Check if player is a veteran (4+ years experience)."""
        return self.experience_years >= 4

    @property
    def is_franchise_player(self) -> bool:
        """Check if player has been with team long-term (5+ years)."""
        return self.years_on_team >= 5

    def get_attribute(self, attr_name: str) -> int:
        """Get a specific attribute value."""
        return self.attributes.get(attr_name)

    def set_attribute(self, attr_name: str, value: int) -> None:
        """Set a specific attribute value."""
        self.attributes.set(attr_name, value)

    def get_preferred_number(self, taken_numbers: set[int]) -> int:
        """
        Get the best available jersey number for this player.

        Args:
            taken_numbers: Set of jersey numbers already taken on the team

        Returns:
            Best available number from preferences, or a valid random number
        """
        # Try preferred numbers first
        for num in self.preferred_jersey_numbers:
            if num not in taken_numbers:
                return num

        # Fall back to position-appropriate random number
        return self._get_fallback_number(taken_numbers)

    def _get_fallback_number(self, taken_numbers: set[int]) -> int:
        """Get a random valid number for this position that isn't taken."""
        import random

        # Position-appropriate ranges (NFL rules)
        ranges = {
            Position.QB: [(1, 19)],
            Position.RB: [(20, 49)],
            Position.FB: [(30, 49)],
            Position.WR: [(10, 19), (80, 89)],
            Position.TE: [(80, 89), (40, 49)],
            Position.LT: [(70, 79), (60, 69)],
            Position.LG: [(60, 79)],
            Position.C: [(50, 79)],
            Position.RG: [(60, 79)],
            Position.RT: [(70, 79), (60, 69)],
            Position.DE: [(90, 99), (50, 59)],
            Position.DT: [(90, 99), (70, 79)],
            Position.NT: [(90, 99), (70, 79)],
            Position.MLB: [(50, 59), (90, 99)],
            Position.ILB: [(50, 59), (90, 99)],
            Position.OLB: [(50, 59), (90, 99)],
            Position.CB: [(20, 39)],
            Position.FS: [(20, 49)],
            Position.SS: [(20, 49)],
            Position.K: [(1, 19)],
            Position.P: [(1, 19)],
            Position.LS: [(40, 59)],
        }

        pos_ranges = ranges.get(self.position, [(1, 99)])

        # Build list of available numbers
        available = []
        for low, high in pos_ranges:
            for num in range(low, high + 1):
                if num not in taken_numbers:
                    available.append(num)

        if available:
            return random.choice(available)

        # Last resort: any available number 1-99
        for num in range(1, 100):
            if num not in taken_numbers:
                return num

        return 0  # No numbers available (shouldn't happen with 53-man roster)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "first_name": self.first_name,
            "last_name": self.last_name,
            "position": self.position.value,
            "attributes": self.attributes.to_dict(),
            "age": self.age,
            "height_inches": self.height_inches,
            "weight_lbs": self.weight_lbs,
            "jersey_number": self.jersey_number,
            "preferred_jersey_numbers": self.preferred_jersey_numbers,
            "experience_years": self.experience_years,
            "years_on_team": self.years_on_team,
            "college": self.college,
            "draft_year": self.draft_year,
            "draft_round": self.draft_round,
            "draft_pick": self.draft_pick,
            "contract_years": self.contract_years,
            "contract_year_remaining": self.contract_year_remaining,
            "salary": self.salary,
            "signing_bonus": self.signing_bonus,
            "signing_bonus_remaining": self.signing_bonus_remaining,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Player":
        """Create from dictionary."""
        return cls(
            id=UUID(data["id"]) if "id" in data else uuid4(),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            position=Position(data.get("position", "QB")),
            attributes=PlayerAttributes.from_dict(data.get("attributes", {})),
            age=data.get("age", 22),
            height_inches=data.get("height_inches", 72),
            weight_lbs=data.get("weight_lbs", 200),
            jersey_number=data.get("jersey_number", 0),
            preferred_jersey_numbers=data.get("preferred_jersey_numbers", []),
            experience_years=data.get("experience_years", 0),
            years_on_team=data.get("years_on_team", 0),
            college=data.get("college"),
            draft_year=data.get("draft_year"),
            draft_round=data.get("draft_round"),
            draft_pick=data.get("draft_pick"),
            contract_years=data.get("contract_years"),
            contract_year_remaining=data.get("contract_year_remaining"),
            salary=data.get("salary"),
            signing_bonus=data.get("signing_bonus"),
            signing_bonus_remaining=data.get("signing_bonus_remaining"),
        )

    def __str__(self) -> str:
        return f"{self.full_name} ({self.position.value}) - {self.overall} OVR"

    def __repr__(self) -> str:
        return f"Player(name='{self.full_name}', pos={self.position.value}, ovr={self.overall})"
