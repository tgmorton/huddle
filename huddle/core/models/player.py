"""Player model."""

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from huddle.core.attributes import PlayerAttributes
from huddle.core.enums import Position

if TYPE_CHECKING:
    from huddle.core.personality import PersonalityProfile, Trait, ArchetypeType
    from huddle.core.approval import PlayerApproval
    from huddle.core.mental_state import WeeklyMentalState, PlayerGameState
    from huddle.core.contracts.contract import Contract


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

    # Portrait appearance (set once at creation, persists)
    portrait_seed: Optional[int] = None        # For reproducible generation
    skin_tone: Optional[int] = None            # 0-7 (0=lightest, 7=darkest)
    face_width: Optional[int] = None           # 0-7 (0=narrowest, 7=widest)
    hair_style: Optional[tuple[int, int]] = None        # (row, col) or None for bald
    facial_hair_style: Optional[tuple[int, int]] = None # (row, col) or None for clean shaven
    hair_color: Optional[str] = None           # Current hair color (can change with age)
    portrait_url: Optional[str] = None         # Generated portrait URL

    # Combine measurables (for prospects)
    forty_yard_dash: Optional[float] = None  # e.g., 4.42
    bench_press_reps: Optional[int] = None   # 225lb reps
    vertical_jump: Optional[float] = None    # inches, e.g., 38.5
    broad_jump: Optional[int] = None         # inches, e.g., 124

    # Scouting progress (for prospects)
    scouting_interviewed: bool = False
    scouting_private_workout: bool = False
    projected_draft_round: Optional[int] = None  # 1-7, None if undrafted projection

    # Jersey number preferences (in order of preference)
    # When joining a team, player tries to get these numbers
    preferred_jersey_numbers: list[int] = field(default_factory=list)

    # Career info
    experience_years: int = 0  # Total NFL experience
    years_on_team: int = 0  # Tenure with current team (affects jersey priority)
    team_id: Optional[UUID] = None  # Set when added to roster, cleared when released

    # Optional metadata for different management levels
    college: Optional[str] = None
    draft_year: Optional[int] = None
    draft_round: Optional[int] = None
    draft_pick: Optional[int] = None

    # Contract info (for pro level)
    # Legacy fields (backward compatibility - prefer using contract object)
    contract_years: Optional[int] = None
    contract_year_remaining: Optional[int] = None  # Years left on current deal
    salary: Optional[int] = None  # Annual salary (in thousands)
    signing_bonus: Optional[int] = None  # Total signing bonus
    signing_bonus_remaining: Optional[int] = None  # Prorated bonus remaining (for dead money)

    # Full contract object (preferred for new code)
    # When set, this provides complete NFL-style contract details
    contract: Optional["Contract"] = None

    # Personality (HC09-style archetypes)
    personality: Optional["PersonalityProfile"] = None

    # Approval tracking (morale/satisfaction)
    approval: Optional["PlayerApproval"] = None

    # Perceived potentials (scout estimates that may differ from actual)
    # Only used for prospects - stores media/scout perception of potential
    perceived_potentials: Optional[dict[str, int]] = None

    # Injury history - tracks past injuries and their impact
    # Each entry: {"type": str, "body_part": str, "season": int, "games_missed": int,
    #              "was_season_ending": bool, "degradation_applied": int}
    injury_history: list[dict] = field(default_factory=list)

    # Player archetype (HC09-style) - determines how OVR is calculated
    # e.g., "power" RB vs "speed" RB affects which attributes matter
    # This is DIFFERENT from personality archetype - this is positional philosophy
    player_archetype: Optional[str] = None

    @property
    def overall(self) -> int:
        """Calculate overall rating based on position."""
        return self.attributes.calculate_overall(self.position.value)

    @property
    def archetype_overall(self) -> int:
        """
        Calculate OVR using this player's archetype weights (HC09-style).

        If the player has an assigned archetype (e.g., "power" for RB),
        the OVR is calculated using the archetype's attribute weights.
        This can differ significantly from the generic position OVR.

        Example:
        - Power RB with high trucking/strength: archetype_overall = 88
        - Same player's generic overall: 82 (speed counts against them)

        Returns:
            Overall rating based on archetype, or generic overall if no archetype
        """
        if not self.player_archetype:
            return self.overall

        from huddle.core.philosophy.evaluation import PHILOSOPHY_ATTRIBUTE_WEIGHTS

        weights = PHILOSOPHY_ATTRIBUTE_WEIGHTS.get(self.player_archetype, {})
        if not weights:
            return self.overall

        total_weight = 0.0
        weighted_sum = 0.0

        for attr_name, weight in weights.items():
            value = self.attributes.get(attr_name, 50)
            weighted_sum += value * weight
            total_weight += weight

        if total_weight == 0:
            return self.overall

        return int(weighted_sum / total_weight)

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

    @property
    def current_salary(self) -> int:
        """Get current year salary (uses contract if available)."""
        if self.contract:
            year_data = self.contract.current_year_data()
            return year_data.base_salary if year_data else 0
        return self.salary or 0

    @property
    def cap_hit(self) -> int:
        """Get current year cap hit (uses contract if available)."""
        if self.contract:
            return self.contract.cap_hit()
        # Legacy: simple calculation (salary + prorated bonus)
        if self.salary and self.contract_years:
            prorated = (self.signing_bonus or 0) // self.contract_years
            return self.salary + prorated
        return self.salary or 0

    @property
    def dead_money(self) -> int:
        """Get dead money if cut (uses contract if available)."""
        if self.contract:
            return self.contract.dead_money_if_cut()
        return self.signing_bonus_remaining or 0

    @property
    def is_contract_expiring(self) -> bool:
        """Check if contract expires after this season."""
        if self.contract:
            return self.contract.is_expiring()
        return self.contract_year_remaining == 1

    @property
    def archetype(self) -> Optional["ArchetypeType"]:
        """Get player's personality archetype, if assigned."""
        if self.personality:
            return self.personality.archetype
        return None

    def get_trait(self, trait: "Trait", default: float = 0.5) -> float:
        """
        Get a personality trait value.

        Args:
            trait: The trait to query
            default: Value if no personality assigned (0.5 = neutral)

        Returns:
            Trait value between 0.0 and 1.0
        """
        if self.personality:
            return self.personality.get_trait(trait, default)
        return default

    def has_strong_trait(self, trait: "Trait", threshold: float = 0.7) -> bool:
        """
        Check if player has a strong personality trait.

        Args:
            trait: The trait to check
            threshold: Minimum value to be considered "strong"

        Returns:
            True if trait is above threshold (or False if no personality)
        """
        if self.personality:
            return self.personality.is_trait_strong(trait, threshold)
        return False

    def get_approval_rating(self) -> float:
        """
        Get player's current approval rating.

        Returns:
            Approval value (0-100), default 50 if not tracked
        """
        if self.approval:
            return self.approval.approval
        return 50.0

    def get_performance_modifier(self) -> float:
        """
        Get performance modifier based on approval.

        Returns:
            Multiplier for performance (0.92 to 1.05)
        """
        if self.approval:
            return self.approval.get_performance_modifier()
        return 1.0

    def is_unhappy(self) -> bool:
        """Check if player is unhappy (may request trade)."""
        if self.approval:
            return self.approval.is_trade_candidate()
        return False

    def is_disgruntled(self) -> bool:
        """Check if player is disgruntled (holdout risk)."""
        if self.approval:
            return self.approval.is_holdout_risk()
        return False

    # =========================================================================
    # Inner Weather: Mental State Helpers
    # =========================================================================

    def get_weekly_mental_state(self, team=None) -> "WeeklyMentalState":
        """
        Build the weekly mental state snapshot for this player.

        Pulls from morale/approval, game prep, and playbook familiarity.

        Args:
            team: Player's team (optional, for prep/familiarity data)

        Returns:
            WeeklyMentalState populated from current systems
        """
        from huddle.core.mental_state import build_weekly_mental_state
        return build_weekly_mental_state(self, team)

    def prepare_for_game(self, team=None) -> "PlayerGameState":
        """
        Package everything simulation needs about this player's mental state.

        This is the handoff from management layer to simulation layer.
        Called before each game.

        Args:
            team: Player's team (optional, for prep data)

        Returns:
            PlayerGameState ready for simulation
        """
        from huddle.core.mental_state import prepare_player_for_game
        return prepare_player_for_game(self, team)

    def get_confidence_volatility(self) -> float:
        """
        Get how much this player's confidence swings during games.

        Returns:
            Volatility multiplier (0.6 = steady, 1.0 = normal, 1.4 = volatile)
        """
        if self.personality:
            return self.personality.get_confidence_volatility()
        return 1.0

    def get_pressure_response(self) -> float:
        """
        Get how this player responds to pressure situations.

        Returns:
            Response modifier (-0.3 = wilts, 0 = neutral, +0.3 = rises)
        """
        if self.personality:
            return self.personality.get_pressure_response()
        return 0.0

    def get_morale(self) -> float:
        """
        Get current morale (from approval system).

        Returns:
            Morale value (0-100), 50 is neutral
        """
        return self.get_approval_rating()

    def get_cognitive_capacity(self) -> int:
        """
        Get cognitive capacity (from awareness attribute).

        Higher values = can track more information under pressure.

        Returns:
            Cognitive capacity (0-100)
        """
        return self.attributes.get("awareness", 50)

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
        data = {
            "id": str(self.id),
            "first_name": self.first_name,
            "last_name": self.last_name,
            "position": self.position.value,
            "attributes": self.attributes.to_dict(),
            "age": self.age,
            "height_inches": self.height_inches,
            "weight_lbs": self.weight_lbs,
            "jersey_number": self.jersey_number,
            # Portrait appearance
            "portrait_seed": self.portrait_seed,
            "skin_tone": self.skin_tone,
            "face_width": self.face_width,
            "hair_style": list(self.hair_style) if self.hair_style else None,
            "facial_hair_style": list(self.facial_hair_style) if self.facial_hair_style else None,
            "hair_color": self.hair_color,
            "portrait_url": self.portrait_url,
            # Combine measurables
            "forty_yard_dash": self.forty_yard_dash,
            "bench_press_reps": self.bench_press_reps,
            "vertical_jump": self.vertical_jump,
            "broad_jump": self.broad_jump,
            "scouting_interviewed": self.scouting_interviewed,
            "scouting_private_workout": self.scouting_private_workout,
            "projected_draft_round": self.projected_draft_round,
            "preferred_jersey_numbers": self.preferred_jersey_numbers,
            "experience_years": self.experience_years,
            "years_on_team": self.years_on_team,
            "team_id": str(self.team_id) if self.team_id else None,
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
        # Include full contract if assigned
        if self.contract:
            data["contract"] = self.contract.to_dict()
        # Include personality if assigned
        if self.personality:
            data["personality"] = self.personality.to_dict()
        # Include approval if tracked
        if self.approval:
            data["approval"] = self.approval.to_dict()
        # Include perceived potentials for prospects
        if self.perceived_potentials:
            data["perceived_potentials"] = self.perceived_potentials
        # Include injury history
        if self.injury_history:
            data["injury_history"] = self.injury_history
        # Include player archetype (HC09-style)
        if self.player_archetype:
            data["player_archetype"] = self.player_archetype
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Player":
        """Create from dictionary."""
        # Load personality if present
        personality = None
        if "personality" in data:
            from huddle.core.personality import PersonalityProfile
            personality = PersonalityProfile.from_dict(data["personality"])

        # Load approval if present
        approval = None
        if "approval" in data:
            from huddle.core.approval import PlayerApproval
            approval = PlayerApproval.from_dict(data["approval"])

        # Load full contract if present
        contract = None
        if "contract" in data:
            from huddle.core.contracts.contract import Contract
            contract = Contract.from_dict(data["contract"])

        # Parse hair/facial styles from lists back to tuples
        hair_style = data.get("hair_style")
        if hair_style and isinstance(hair_style, list):
            hair_style = tuple(hair_style)
        facial_hair_style = data.get("facial_hair_style")
        if facial_hair_style and isinstance(facial_hair_style, list):
            facial_hair_style = tuple(facial_hair_style)

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
            # Portrait appearance
            portrait_seed=data.get("portrait_seed"),
            skin_tone=data.get("skin_tone"),
            face_width=data.get("face_width"),
            hair_style=hair_style,
            facial_hair_style=facial_hair_style,
            hair_color=data.get("hair_color"),
            portrait_url=data.get("portrait_url"),
            # Combine measurables
            forty_yard_dash=data.get("forty_yard_dash"),
            bench_press_reps=data.get("bench_press_reps"),
            vertical_jump=data.get("vertical_jump"),
            broad_jump=data.get("broad_jump"),
            scouting_interviewed=data.get("scouting_interviewed", False),
            scouting_private_workout=data.get("scouting_private_workout", False),
            projected_draft_round=data.get("projected_draft_round"),
            preferred_jersey_numbers=data.get("preferred_jersey_numbers", []),
            experience_years=data.get("experience_years", 0),
            years_on_team=data.get("years_on_team", 0),
            team_id=UUID(data["team_id"]) if data.get("team_id") else None,
            college=data.get("college"),
            draft_year=data.get("draft_year"),
            draft_round=data.get("draft_round"),
            draft_pick=data.get("draft_pick"),
            contract_years=data.get("contract_years"),
            contract_year_remaining=data.get("contract_year_remaining"),
            salary=data.get("salary"),
            signing_bonus=data.get("signing_bonus"),
            signing_bonus_remaining=data.get("signing_bonus_remaining"),
            contract=contract,
            personality=personality,
            approval=approval,
            perceived_potentials=data.get("perceived_potentials"),
            injury_history=data.get("injury_history", []),
            player_archetype=data.get("player_archetype"),
        )

    def __str__(self) -> str:
        return f"{self.full_name} ({self.position.value}) - {self.overall} OVR"

    def __repr__(self) -> str:
        return f"Player(name='{self.full_name}', pos={self.position.value}, ovr={self.overall})"
