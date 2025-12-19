"""
Inner Weather: Mental State Model.

This module implements the unified mental state model for players,
connecting personality (stable), morale/preparation (weekly), and
confidence (in-game) into a coherent system.

The three layers:
1. STABLE: Personality traits, experience, cognitive capacity (career-long)
2. WEEKLY: Morale, preparation, physical baseline (changes between games)
3. IN-GAME: Confidence, pressure, focus (fluctuates play-to-play)

Management owns Stable and Weekly layers. Simulation owns In-Game layer.
This module provides the handoff structures between them.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from huddle.core.models.player import Player
    from huddle.core.personality import PersonalityProfile


# =============================================================================
# Constants
# =============================================================================

# Confidence bounds
DEFAULT_CONFIDENCE = 50.0
MIN_CONFIDENCE = 0.0
MAX_CONFIDENCE = 100.0

# Starting confidence calculation
MORALE_CONFIDENCE_WEIGHT = 0.4  # How much morale affects starting confidence


def clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp a value between minimum and maximum."""
    return max(minimum, min(maximum, value))


# =============================================================================
# Weekly Mental State
# =============================================================================

@dataclass
class WeeklyMentalState:
    """
    The weekly layer of a player's mental state.

    Captures everything that changes week-to-week and sets up
    the starting point for in-game mental state.

    This is what management tracks and updates through:
    - Approval system (morale)
    - Game prep system (opponent familiarity)
    - Playbook system (scheme familiarity)
    """

    player_id: UUID

    # From morale/approval system
    morale: float = 50.0              # 0-100, current approval
    morale_trend: float = 0.0         # Rising/falling indicator
    grievances: List[str] = field(default_factory=list)

    # From game prep system
    opponent_familiarity: float = 0.0  # 0-1, how prepared for opponent

    # From playbook system
    scheme_familiarity: float = 0.5    # 0-1, average play mastery

    # Physical baseline (future - for now defaults)
    fatigue_baseline: float = 0.0      # 0-1, accumulated fatigue debt
    injury_limitations: List[str] = field(default_factory=list)

    def get_starting_confidence(self, personality: Optional["PersonalityProfile"] = None) -> float:
        """
        Calculate game-start confidence from morale + personality.

        Args:
            personality: Player's personality profile for modifiers

        Returns:
            Starting confidence (20-80 typical range)
        """
        base = DEFAULT_CONFIDENCE

        # Morale contributes to confidence
        # If morale is 70, that's +8 confidence ((70-50) * 0.4)
        # If morale is 30, that's -8 confidence ((30-50) * 0.4)
        morale_contribution = (self.morale - 50) * MORALE_CONFIDENCE_WEIGHT

        # Preparation helps confidence
        prep_contribution = self.opponent_familiarity * 5.0  # Up to +5

        # Familiarity with scheme helps confidence
        scheme_contribution = (self.scheme_familiarity - 0.5) * 6.0  # -3 to +3

        # Fatigue hurts confidence
        fatigue_penalty = self.fatigue_baseline * -5.0  # Up to -5

        # Personality modifier
        personality_mod = 0.0
        if personality:
            personality_mod = personality.get_baseline_confidence_modifier()

        starting = base + morale_contribution + prep_contribution + scheme_contribution + fatigue_penalty + personality_mod

        # Clamp to reasonable starting range (not too extreme)
        return clamp(starting, 20.0, 80.0)

    def get_confidence_bounds(self, personality: Optional["PersonalityProfile"] = None) -> Tuple[float, float]:
        """
        Calculate min/max confidence bounds for this player.

        More volatile personalities have wider bounds.

        Args:
            personality: Player's personality profile

        Returns:
            Tuple of (floor, ceiling) for confidence
        """
        volatility = 1.0
        if personality:
            volatility = personality.get_confidence_volatility()

        # Base range is 20-80, volatility stretches it
        floor = 50 - (35 * volatility)
        ceiling = 50 + (35 * volatility)

        return (clamp(floor, 5.0, 40.0), clamp(ceiling, 60.0, 95.0))

    def get_resilience_modifier(self, personality: Optional["PersonalityProfile"] = None) -> float:
        """
        Get resilience modifier for confidence recovery.

        High morale + good personality = faster recovery from mistakes.

        Args:
            personality: Player's personality profile

        Returns:
            Resilience multiplier (0.5 to 1.5)
        """
        base = 1.0

        # Low morale = slower recovery
        if self.morale < 40:
            base *= 0.7
        elif self.morale < 50:
            base *= 0.85
        elif self.morale > 70:
            base *= 1.2
        elif self.morale > 80:
            base *= 1.3

        # Personality affects recovery
        if personality:
            base *= personality.get_confidence_recovery_rate()

        # Fatigue slows recovery
        base *= (1.0 - self.fatigue_baseline * 0.3)

        return clamp(base, 0.4, 1.6)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "player_id": str(self.player_id),
            "morale": self.morale,
            "morale_trend": self.morale_trend,
            "grievances": self.grievances,
            "opponent_familiarity": self.opponent_familiarity,
            "scheme_familiarity": self.scheme_familiarity,
            "fatigue_baseline": self.fatigue_baseline,
            "injury_limitations": self.injury_limitations,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WeeklyMentalState":
        """Create from dictionary."""
        return cls(
            player_id=UUID(data["player_id"]),
            morale=data.get("morale", 50.0),
            morale_trend=data.get("morale_trend", 0.0),
            grievances=data.get("grievances", []),
            opponent_familiarity=data.get("opponent_familiarity", 0.0),
            scheme_familiarity=data.get("scheme_familiarity", 0.5),
            fatigue_baseline=data.get("fatigue_baseline", 0.0),
            injury_limitations=data.get("injury_limitations", []),
        )


# =============================================================================
# Player Game State (Handoff to Simulation)
# =============================================================================

@dataclass
class PlayerGameState:
    """
    Complete mental state package for game simulation.

    This is the handoff from management layer to simulation layer.
    Contains everything simulation needs to initialize and run
    the in-game mental state model.

    Created before each game by `prepare_player_for_game()`.
    """

    player_id: UUID

    # === From Stable Layer ===
    experience_years: int = 0
    cognitive_capacity: int = 50        # From awareness attribute
    confidence_volatility: float = 1.0  # From personality
    pressure_response: float = 0.0      # From personality
    confidence_recovery_rate: float = 1.0  # From personality

    # === From Weekly Layer → Starting Points ===
    starting_confidence: float = 50.0
    confidence_floor: float = 15.0
    confidence_ceiling: float = 85.0
    resilience_modifier: float = 1.0

    # === Familiarity Bonuses ===
    opponent_familiarity: float = 0.0   # Game prep bonus
    scheme_familiarity: float = 0.5     # Playbook mastery

    # === Physical State ===
    fatigue_baseline: float = 0.0
    injury_limitations: List[str] = field(default_factory=list)

    # === Morale Context (for post-game updates) ===
    current_morale: float = 50.0
    morale_trend: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "player_id": str(self.player_id),
            "experience_years": self.experience_years,
            "cognitive_capacity": self.cognitive_capacity,
            "confidence_volatility": self.confidence_volatility,
            "pressure_response": self.pressure_response,
            "confidence_recovery_rate": self.confidence_recovery_rate,
            "starting_confidence": self.starting_confidence,
            "confidence_floor": self.confidence_floor,
            "confidence_ceiling": self.confidence_ceiling,
            "resilience_modifier": self.resilience_modifier,
            "opponent_familiarity": self.opponent_familiarity,
            "scheme_familiarity": self.scheme_familiarity,
            "fatigue_baseline": self.fatigue_baseline,
            "injury_limitations": self.injury_limitations,
            "current_morale": self.current_morale,
            "morale_trend": self.morale_trend,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerGameState":
        """Create from dictionary."""
        return cls(
            player_id=UUID(data["player_id"]),
            experience_years=data.get("experience_years", 0),
            cognitive_capacity=data.get("cognitive_capacity", 50),
            confidence_volatility=data.get("confidence_volatility", 1.0),
            pressure_response=data.get("pressure_response", 0.0),
            confidence_recovery_rate=data.get("confidence_recovery_rate", 1.0),
            starting_confidence=data.get("starting_confidence", 50.0),
            confidence_floor=data.get("confidence_floor", 15.0),
            confidence_ceiling=data.get("confidence_ceiling", 85.0),
            resilience_modifier=data.get("resilience_modifier", 1.0),
            opponent_familiarity=data.get("opponent_familiarity", 0.0),
            scheme_familiarity=data.get("scheme_familiarity", 0.5),
            fatigue_baseline=data.get("fatigue_baseline", 0.0),
            injury_limitations=data.get("injury_limitations", []),
            current_morale=data.get("current_morale", 50.0),
            morale_trend=data.get("morale_trend", 0.0),
        )


# =============================================================================
# Helper Functions
# =============================================================================

def build_weekly_mental_state(player: "Player", team=None) -> WeeklyMentalState:
    """
    Build WeeklyMentalState from a player's current state.

    Pulls from:
    - player.approval for morale
    - team.game_prep_bonus for opponent familiarity
    - team.player_knowledge for scheme familiarity

    Args:
        player: The player
        team: The player's team (optional, for prep/familiarity data)

    Returns:
        WeeklyMentalState populated from current systems
    """
    # Get morale from approval system
    morale = 50.0
    morale_trend = 0.0
    grievances = []
    if player.approval:
        morale = player.approval.approval
        morale_trend = player.approval.trend
        grievances = player.approval.grievances.copy()

    # Get opponent familiarity from game prep
    opponent_familiarity = 0.0
    if team and team.game_prep_bonus:
        opponent_familiarity = team.game_prep_bonus.prep_level

    # Get scheme familiarity from playbook knowledge
    scheme_familiarity = 0.5  # Default
    if team and player.id in team.player_knowledge:
        knowledge = team.player_knowledge[player.id]
        # Average mastery across known plays
        if knowledge.plays:
            from huddle.core.playbook import MasteryLevel
            total = 0.0
            for mastery in knowledge.plays.values():
                if mastery.level == MasteryLevel.MASTERED:
                    total += 1.0
                elif mastery.level == MasteryLevel.LEARNED:
                    total += 0.6 + mastery.progress * 0.4
                else:
                    total += mastery.progress * 0.6
            scheme_familiarity = total / len(knowledge.plays)

    return WeeklyMentalState(
        player_id=player.id,
        morale=morale,
        morale_trend=morale_trend,
        grievances=grievances,
        opponent_familiarity=opponent_familiarity,
        scheme_familiarity=scheme_familiarity,
        fatigue_baseline=0.0,  # Future: from fatigue system
        injury_limitations=[],  # Future: from injury system
    )


def prepare_player_for_game(player: "Player", team=None) -> PlayerGameState:
    """
    Package everything simulation needs about a player's mental state.

    This is the handoff from management layer to simulation layer.
    Called before each game.

    Args:
        player: The player
        team: The player's team (optional, for prep data)

    Returns:
        PlayerGameState ready for simulation
    """
    # Build weekly state
    weekly = build_weekly_mental_state(player, team)

    # Get personality-derived values
    personality = player.personality
    volatility = 1.0
    pressure_response = 0.0
    recovery_rate = 1.0

    if personality:
        volatility = personality.get_confidence_volatility()
        pressure_response = personality.get_pressure_response()
        recovery_rate = personality.get_confidence_recovery_rate()

    # Calculate starting confidence and bounds
    starting = weekly.get_starting_confidence(personality)
    floor, ceiling = weekly.get_confidence_bounds(personality)
    resilience = weekly.get_resilience_modifier(personality)

    # Get cognitive capacity from awareness attribute
    cognitive_capacity = player.attributes.get("awareness", 50)

    return PlayerGameState(
        player_id=player.id,
        experience_years=player.experience_years,
        cognitive_capacity=cognitive_capacity,
        confidence_volatility=volatility,
        pressure_response=pressure_response,
        confidence_recovery_rate=recovery_rate,
        starting_confidence=starting,
        confidence_floor=floor,
        confidence_ceiling=ceiling,
        resilience_modifier=resilience,
        opponent_familiarity=weekly.opponent_familiarity,
        scheme_familiarity=weekly.scheme_familiarity,
        fatigue_baseline=weekly.fatigue_baseline,
        injury_limitations=weekly.injury_limitations,
        current_morale=weekly.morale,
        morale_trend=weekly.morale_trend,
    )
