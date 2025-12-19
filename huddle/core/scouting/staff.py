"""
Scouting staff system.

Manages scouts and their impact on scouting accuracy.
Better scouts produce more accurate projections and reveal
hidden traits more reliably.

Scouts have cognitive biases that affect their evaluations:
- Recency bias: Overweighting recent performances
- Measurables bias: Being dazzled by combine numbers
- Confirmation bias: Seeing what they expect to see
- School/regional bias: Over/undervaluing certain programs
- Position blindspots: Struggling with certain positions
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
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

# Conference/school mappings for regional biases
CONFERENCE_REGIONS: dict[str, str] = {
    "SEC": "southeast",
    "ACC": "southeast",
    "Big Ten": "midwest",
    "Big 12": "southwest",
    "Pac-12": "west_coast",
    "Pac-10": "west_coast",
    "Big East": "northeast",
    "AAC": "midwest",
    "Mountain West": "west_coast",
    "MAC": "midwest",
    "Sun Belt": "southeast",
    "C-USA": "southwest",
    "Independent": "general",
}


# =============================================================================
# Scout Biases
# =============================================================================

@dataclass
class ScoutTrackRecord:
    """
    Tracks a scout's historical accuracy.

    This lets players learn over time which scouts to trust for what.
    """
    total_evaluations: int = 0
    accurate_evaluations: int = 0  # Within 5 points of true value

    # Position-specific tracking
    position_evaluations: Dict[str, int] = field(default_factory=dict)
    position_accurate: Dict[str, int] = field(default_factory=dict)

    # Notable calls
    big_hits: List[str] = field(default_factory=list)  # Players they were right about
    big_misses: List[str] = field(default_factory=list)  # Players they were wrong about

    @property
    def overall_accuracy(self) -> float:
        """Overall accuracy percentage (0-1)."""
        if self.total_evaluations == 0:
            return 0.5  # Unknown
        return self.accurate_evaluations / self.total_evaluations

    def get_position_accuracy(self, position: str) -> float:
        """Accuracy for a specific position."""
        total = self.position_evaluations.get(position, 0)
        if total == 0:
            return 0.5  # Unknown
        accurate = self.position_accurate.get(position, 0)
        return accurate / total

    def record_evaluation(
        self,
        position: str,
        was_accurate: bool,
        player_name: str = "",
        was_notable: bool = False,
    ) -> None:
        """Record an evaluation result."""
        self.total_evaluations += 1
        if was_accurate:
            self.accurate_evaluations += 1

        # Position tracking
        self.position_evaluations[position] = self.position_evaluations.get(position, 0) + 1
        if was_accurate:
            self.position_accurate[position] = self.position_accurate.get(position, 0) + 1

        # Notable calls (limit to last 5)
        if was_notable and player_name:
            if was_accurate:
                self.big_hits.append(player_name)
                self.big_hits = self.big_hits[-5:]
            else:
                self.big_misses.append(player_name)
                self.big_misses = self.big_misses[-5:]

    def to_dict(self) -> dict:
        return {
            "total_evaluations": self.total_evaluations,
            "accurate_evaluations": self.accurate_evaluations,
            "position_evaluations": self.position_evaluations,
            "position_accurate": self.position_accurate,
            "big_hits": self.big_hits,
            "big_misses": self.big_misses,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScoutTrackRecord":
        return cls(
            total_evaluations=data.get("total_evaluations", 0),
            accurate_evaluations=data.get("accurate_evaluations", 0),
            position_evaluations=data.get("position_evaluations", {}),
            position_accurate=data.get("position_accurate", {}),
            big_hits=data.get("big_hits", []),
            big_misses=data.get("big_misses", []),
        )


@dataclass
class ScoutBiases:
    """
    Cognitive biases that affect scout evaluations.

    All values are 0.0-1.0 where 0.5 is neutral.
    Lower values = bias in one direction, higher = opposite direction.
    """

    # Recency bias: How much recent performances affect evaluations
    # High (>0.6): Last game/week matters a lot
    # Low (<0.4): Focuses on full body of work
    recency_bias: float = 0.5

    # Measurables bias: How much physical tools affect all evaluations
    # High (>0.6): Athletic freaks get boosted across the board
    # Low (<0.4): Film-first, may miss athletes
    measurables_bias: float = 0.5

    # Confirmation strength: How sticky are first impressions
    # High (>0.6): Once they decide, hard to change their mind
    # Low (<0.4): Open to revising opinions
    confirmation_strength: float = 0.5

    # Risk tolerance: How they weight upside vs floor
    # High (>0.6): "Ceiling scout" - sees potential, may miss red flags
    # Low (<0.4): "Floor scout" - conservative, may miss upside
    risk_tolerance: float = 0.5

    # School/conference biases: +/- adjustment by conference
    # Positive = overvalues, negative = undervalues
    conference_biases: Dict[str, float] = field(default_factory=dict)

    # Position weaknesses: Positions they struggle to evaluate
    # These positions get accuracy penalty
    position_weaknesses: List[str] = field(default_factory=list)

    # First impressions tracking (for confirmation bias)
    # player_id -> "high" / "medium" / "low" initial assessment
    initial_impressions: Dict[str, str] = field(default_factory=dict)

    def get_conference_bias(self, conference: str) -> float:
        """Get bias modifier for a conference (-10 to +10)."""
        return self.conference_biases.get(conference, 0.0)

    def has_position_weakness(self, position: str) -> bool:
        """Check if scout has weakness evaluating this position."""
        return position in self.position_weaknesses

    def set_initial_impression(self, player_id: str, impression: str) -> None:
        """Record first impression of a player."""
        if player_id not in self.initial_impressions:
            self.initial_impressions[player_id] = impression

    def get_confirmation_modifier(self, player_id: str) -> float:
        """
        Get projection modifier from confirmation bias.

        Returns: -5 to +5 adjustment based on initial impression and bias strength.
        """
        if player_id not in self.initial_impressions:
            return 0.0

        impression = self.initial_impressions[player_id]

        # Scale by confirmation strength (0.5 = no effect, 1.0 = max effect)
        strength_factor = (self.confirmation_strength - 0.5) * 2  # -1 to +1

        if impression == "high":
            return 5.0 * strength_factor
        elif impression == "low":
            return -5.0 * strength_factor
        return 0.0

    def to_dict(self) -> dict:
        return {
            "recency_bias": self.recency_bias,
            "measurables_bias": self.measurables_bias,
            "confirmation_strength": self.confirmation_strength,
            "risk_tolerance": self.risk_tolerance,
            "conference_biases": self.conference_biases,
            "position_weaknesses": self.position_weaknesses,
            "initial_impressions": self.initial_impressions,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScoutBiases":
        return cls(
            recency_bias=data.get("recency_bias", 0.5),
            measurables_bias=data.get("measurables_bias", 0.5),
            confirmation_strength=data.get("confirmation_strength", 0.5),
            risk_tolerance=data.get("risk_tolerance", 0.5),
            conference_biases=data.get("conference_biases", {}),
            position_weaknesses=data.get("position_weaknesses", []),
            initial_impressions=data.get("initial_impressions", {}),
        )

    @classmethod
    def generate_random(cls) -> "ScoutBiases":
        """Generate random bias profile."""
        biases = cls(
            recency_bias=random.gauss(0.5, 0.15),
            measurables_bias=random.gauss(0.5, 0.15),
            confirmation_strength=random.gauss(0.5, 0.15),
            risk_tolerance=random.gauss(0.5, 0.15),
        )

        # Clamp to valid range
        biases.recency_bias = max(0.1, min(0.9, biases.recency_bias))
        biases.measurables_bias = max(0.1, min(0.9, biases.measurables_bias))
        biases.confirmation_strength = max(0.1, min(0.9, biases.confirmation_strength))
        biases.risk_tolerance = max(0.1, min(0.9, biases.risk_tolerance))

        # Random conference biases (most scouts have 1-2)
        all_conferences = list(CONFERENCE_REGIONS.keys())
        num_biases = random.randint(0, 3)
        for _ in range(num_biases):
            conf = random.choice(all_conferences)
            # Positive or negative bias (-8 to +8)
            biases.conference_biases[conf] = random.uniform(-8, 8)

        # Random position weaknesses (0-2)
        all_positions = ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB"]
        num_weaknesses = random.choices([0, 1, 2], weights=[0.4, 0.4, 0.2])[0]
        biases.position_weaknesses = random.sample(all_positions, num_weaknesses)

        return biases


@dataclass
class Scout:
    """
    A member of the scouting staff.

    Each scout has a skill level, specialty, cognitive biases, and track record
    that affect their accuracy when evaluating players.

    Scouts are "characters, not just information sources" - you learn over time
    who to trust for what positions and situations.
    """
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    level: ScoutingLevel = ScoutingLevel.AVERAGE
    specialty: ScoutSpecialty = ScoutSpecialty.GENERAL
    experience_years: int = 0

    # Hidden "true" skill (affects actual accuracy)
    # Player only sees the level, not the exact skill
    _skill: int = 50  # 1-99 scale

    # Cognitive biases that affect evaluations
    biases: ScoutBiases = field(default_factory=ScoutBiases)

    # Track record of past evaluations
    track_record: ScoutTrackRecord = field(default_factory=ScoutTrackRecord)

    @property
    def skill(self) -> int:
        """Scout's actual skill rating."""
        return self._skill

    @property
    def is_high_recency(self) -> bool:
        """Does this scout overweight recent performances?"""
        return self.biases.recency_bias > 0.6

    @property
    def is_measurables_scout(self) -> bool:
        """Is this scout dazzled by athletic testing?"""
        return self.biases.measurables_bias > 0.6

    @property
    def is_film_scout(self) -> bool:
        """Does this scout focus on tape over measurables?"""
        return self.biases.measurables_bias < 0.4

    @property
    def is_ceiling_scout(self) -> bool:
        """Does this scout project upside?"""
        return self.biases.risk_tolerance > 0.6

    @property
    def is_floor_scout(self) -> bool:
        """Is this scout conservative?"""
        return self.biases.risk_tolerance < 0.4

    def get_accuracy_for_position(self, position: str) -> ScoutingLevel:
        """
        Get effective accuracy level for a specific position.

        Scouts get a bonus when evaluating their specialty,
        and a penalty for positions they have blindspots on.
        """
        level_order = [
            ScoutingLevel.ROOKIE,
            ScoutingLevel.AVERAGE,
            ScoutingLevel.EXPERIENCED,
            ScoutingLevel.ELITE,
        ]
        current_idx = level_order.index(self.level)

        # Check if position matches specialty (bonus)
        specialty_positions = SPECIALTY_POSITIONS.get(self.specialty, [])
        if position in specialty_positions:
            current_idx = min(current_idx + 1, len(level_order) - 1)

        # Check for position weakness (penalty)
        # Map specific positions to weakness categories
        weakness_map = {
            "QB": "QB",
            "RB": "RB", "FB": "RB",
            "WR": "WR",
            "TE": "TE",
            "LT": "OL", "LG": "OL", "C": "OL", "RG": "OL", "RT": "OL",
            "DE": "DL", "DT": "DL", "NT": "DL",
            "MLB": "LB", "OLB": "LB", "ILB": "LB",
            "CB": "DB", "FS": "DB", "SS": "DB",
        }
        weakness_category = weakness_map.get(position, position)
        if self.biases.has_position_weakness(weakness_category):
            current_idx = max(current_idx - 1, 0)

        return level_order[current_idx]

    def apply_biases_to_projection(
        self,
        base_projection: int,
        player_id: str,
        position: str,
        conference: str = "",
        recent_performance: str = "neutral",
        is_athletic_freak: bool = False,
    ) -> int:
        """
        Apply scout's cognitive biases to a projection.

        Args:
            base_projection: The base projected value
            player_id: Player being evaluated
            position: Player's position
            conference: Player's college conference
            recent_performance: "great", "neutral", or "poor"
            is_athletic_freak: Does player have elite measurables?

        Returns:
            Biased projection value (clamped to 1-99)
        """
        adjustment = 0.0

        # Recency bias
        if self.biases.recency_bias > 0.5:
            recency_strength = (self.biases.recency_bias - 0.5) * 2  # 0 to 1
            if recent_performance == "great":
                adjustment += 5.0 * recency_strength
            elif recent_performance == "poor":
                adjustment -= 5.0 * recency_strength

        # Measurables bias (halo effect)
        if is_athletic_freak:
            measurables_effect = (self.biases.measurables_bias - 0.5) * 2  # -1 to +1
            adjustment += 4.0 * measurables_effect

        # Conference bias
        if conference:
            adjustment += self.biases.get_conference_bias(conference)

        # Confirmation bias
        adjustment += self.biases.get_confirmation_modifier(player_id)

        # Apply adjustment
        result = base_projection + int(adjustment)
        return max(1, min(99, result))

    def get_bias_summary(self) -> str:
        """Get a human-readable summary of scout's notable biases."""
        traits = []

        if self.is_high_recency:
            traits.append("Overweights recent games")
        if self.is_measurables_scout:
            traits.append("Loves athletic freaks")
        elif self.is_film_scout:
            traits.append("Film-first evaluator")
        if self.is_ceiling_scout:
            traits.append("Sees upside everywhere")
        elif self.is_floor_scout:
            traits.append("Conservative evaluator")
        if self.biases.confirmation_strength > 0.7:
            traits.append("Stubborn on first impressions")
        if self.biases.position_weaknesses:
            traits.append(f"Struggles with: {', '.join(self.biases.position_weaknesses)}")
        if self.biases.conference_biases:
            for conf, bias in self.biases.conference_biases.items():
                if bias > 3:
                    traits.append(f"Loves {conf}")
                elif bias < -3:
                    traits.append(f"Undervalues {conf}")

        return "; ".join(traits) if traits else "No notable biases"

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "level": self.level.value,
            "specialty": self.specialty.value,
            "experience_years": self.experience_years,
            "_skill": self._skill,
            "biases": self.biases.to_dict(),
            "track_record": self.track_record.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Scout":
        biases = ScoutBiases()
        if "biases" in data:
            biases = ScoutBiases.from_dict(data["biases"])

        track_record = ScoutTrackRecord()
        if "track_record" in data:
            track_record = ScoutTrackRecord.from_dict(data["track_record"])

        return cls(
            id=UUID(data["id"]) if "id" in data else uuid4(),
            name=data.get("name", ""),
            level=ScoutingLevel(data.get("level", "average")),
            specialty=ScoutSpecialty(data.get("specialty", "general")),
            experience_years=data.get("experience_years", 0),
            _skill=data.get("_skill", 50),
            biases=biases,
            track_record=track_record,
        )

    @classmethod
    def generate_random(cls, name: str = "") -> "Scout":
        """Generate a random scout with biases."""
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

        # Generate random biases
        biases = ScoutBiases.generate_random()

        # Regional scouts tend to have stronger conference biases
        specialty = random.choice(list(ScoutSpecialty))
        if specialty in (
            ScoutSpecialty.SOUTHEAST,
            ScoutSpecialty.MIDWEST,
            ScoutSpecialty.WEST_COAST,
            ScoutSpecialty.SOUTHWEST,
            ScoutSpecialty.NORTHEAST,
        ):
            # Add home-region bias
            region_to_conf = {
                ScoutSpecialty.SOUTHEAST: "SEC",
                ScoutSpecialty.MIDWEST: "Big Ten",
                ScoutSpecialty.WEST_COAST: "Pac-12",
                ScoutSpecialty.SOUTHWEST: "Big 12",
                ScoutSpecialty.NORTHEAST: "ACC",
            }
            home_conf = region_to_conf.get(specialty)
            if home_conf:
                # Strong positive bias for home conference
                biases.conference_biases[home_conf] = random.uniform(3, 8)

        return cls(
            name=name or _generate_scout_name(),
            level=level,
            specialty=specialty,
            experience_years=random.randint(0, 25),
            _skill=skill,
            biases=biases,
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
