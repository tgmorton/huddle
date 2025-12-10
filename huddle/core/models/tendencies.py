"""
Team Tendencies Model.

Defines AI behavior for CPU-controlled teams in drafting, trading,
free agency, and cap management. These tendencies shape each team's
unique decision-making personality.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, TYPE_CHECKING
import random

from huddle.core.philosophy.evaluation import TeamPhilosophies

if TYPE_CHECKING:
    from huddle.core.attributes.registry import PlayerAttributes


class DraftStrategy(Enum):
    """How the AI approaches the draft."""
    BEST_AVAILABLE = "best_available"  # Always pick highest rated player
    NEED_BASED = "need_based"  # Fill roster holes first
    BALANCED = "balanced"  # Mix of BPA and need
    TRADE_DOWN = "trade_down"  # Accumulate picks, trade back
    TRADE_UP = "trade_up"  # Aggressive to get specific players


class TradeAggression(Enum):
    """How often the AI initiates trades."""
    HEAVY_TRADER = "heavy_trader"  # Frequently makes trades
    MODERATE = "moderate"  # Normal trade activity
    LIGHT_TRADER = "light_trader"  # Rarely trades
    STANDPAT = "standpat"  # Almost never trades


class NegotiationTone(Enum):
    """How the AI handles contract negotiations."""
    LOWBALL = "lowball"  # Always start low, hard negotiator
    FAIR = "fair"  # Offers market value
    OVERPAY = "overpay"  # Willing to pay premium for targets
    HAGGLER = "haggler"  # Lots of back and forth


class FuturePickValue(Enum):
    """How much AI values future draft picks."""
    HOARDER = "hoarder"  # Highly values future picks, builds through draft
    BALANCED = "balanced"  # Normal valuation
    WIN_NOW = "win_now"  # Trades futures for current talent


class CapManagement(Enum):
    """How the AI manages salary cap."""
    SPEND_TO_CAP = "spend_to_cap"  # Uses all available cap space
    MODERATE = "moderate"  # Maintains some flexibility
    THRIFTY = "thrifty"  # Conservative spending, hoards cap space


class OffensiveScheme(Enum):
    """Offensive philosophy - affects player evaluation."""
    WEST_COAST = "west_coast"  # Short passes, timing routes - values accuracy
    AIR_RAID = "air_raid"  # Spread, vertical passing - values arm strength
    POWER_RUN = "power_run"  # Ground and pound - values RBs, OL
    SPREAD = "spread"  # Speed, space - values athleticism
    PRO_STYLE = "pro_style"  # Balanced, traditional
    RPO_HEAVY = "rpo_heavy"  # Run-pass option - values mobile QBs


class DefensiveScheme(Enum):
    """Defensive philosophy - affects player evaluation."""
    FOUR_THREE = "4-3"  # 4 DL, 3 LB - traditional
    THREE_FOUR = "3-4"  # 3 DL, 4 LB - versatile
    TAMPA_TWO = "tampa_2"  # Zone coverage focused
    PRESS_MAN = "press_man"  # Aggressive man coverage
    MULTIPLE = "multiple"  # Hybrid, changes look
    BLITZ_HEAVY = "blitz_heavy"  # Aggressive, risk-reward


# NOTE: Position-specific philosophies (QBPhilosophy, RBPhilosophy, etc.)
# have been moved to huddle.core.philosophy module for HC09-style evaluation.
# Use TeamPhilosophies for team-specific player OVR calculation.


@dataclass
class TeamTendencies:
    """
    AI behavior tendencies for a team.

    These define how CPU-controlled teams make decisions in:
    - Draft (who to pick, when to trade)
    - Free agency (who to pursue, how much to offer)
    - Trades (frequency, pick valuation)
    - Cap management (how much to spend)
    - Scheme fit (which player traits matter most)
    """

    # Draft & Roster Building
    draft_strategy: DraftStrategy = DraftStrategy.BALANCED
    trade_aggression: TradeAggression = TradeAggression.MODERATE
    negotiation_tone: NegotiationTone = NegotiationTone.FAIR
    future_pick_value: FuturePickValue = FuturePickValue.BALANCED
    cap_management: CapManagement = CapManagement.MODERATE

    # Scheme & Philosophy
    offensive_scheme: OffensiveScheme = OffensiveScheme.PRO_STYLE
    defensive_scheme: DefensiveScheme = DefensiveScheme.FOUR_THREE
    # HC09-style position philosophies - affects how team calculates player OVR
    philosophies: TeamPhilosophies = field(default_factory=TeamPhilosophies)

    # Gameplay tendencies (0.0 to 1.0)
    run_tendency: float = 0.5  # Higher = more run plays
    aggression: float = 0.5  # Higher = more aggressive on 4th down, 2-pt
    blitz_tendency: float = 0.3  # Higher = more blitzes

    # Position value weights for draft (relative importance)
    # Range compressed to 0.85-1.0 for skill positions, 0.5-0.6 for specialists
    # These should act as slight modifiers, not dramatic multipliers
    position_values: dict[str, float] = field(default_factory=lambda: {
        "QB": 1.0,
        "RB": 0.90,
        "WR": 0.95,
        "TE": 0.88,
        "OL": 0.92,  # Covers LT, LG, C, RG, RT
        "DE": 0.95,
        "DT": 0.90,
        "LB": 0.90,  # Covers MLB, OLB, ILB
        "CB": 0.95,
        "S": 0.88,  # Covers FS, SS
        "K": 0.60,
        "P": 0.55,
    })

    def get_position_value(self, position: str) -> float:
        """Get the value weight for a position."""
        # Map specific positions to general categories
        pos_map = {
            "LT": "OL", "LG": "OL", "C": "OL", "RG": "OL", "RT": "OL",
            "MLB": "LB", "OLB": "LB", "ILB": "LB",
            "FS": "S", "SS": "S",
            "NT": "DT", "FB": "RB",
        }
        category = pos_map.get(position, position)
        return self.position_values.get(category, 0.5)

    def evaluate_player_fit(self, player_overall: int, player_position: str,
                           team_need_score: float = 0.5) -> float:
        """
        Evaluate how well a player fits this team's tendencies.

        Returns a score combining:
        - Raw overall rating (normalized to 0-100 scale)
        - Position value to this team
        - Team need at the position
        - Draft strategy influence

        Args:
            player_overall: Player's overall rating (0-100)
            player_position: Player's position
            team_need_score: How much team needs this position (0-1)

        Returns:
            Combined evaluation score (roughly 0-100 scale)
        """
        position_weight = self.get_position_value(player_position)

        # Determine how much to weight need vs talent based on strategy
        if self.draft_strategy == DraftStrategy.BEST_AVAILABLE:
            # 85% talent, 15% need
            talent_weight = 0.85
            need_weight = 0.15
        elif self.draft_strategy == DraftStrategy.NEED_BASED:
            # 50% talent, 50% need
            talent_weight = 0.50
            need_weight = 0.50
        else:  # BALANCED, TRADE_UP, TRADE_DOWN
            # 70% talent, 30% need
            talent_weight = 0.70
            need_weight = 0.30

        # Talent score: overall * position value (position_weight is ~0.8-1.2)
        talent_score = player_overall * position_weight

        # Need score: scale need (0-1) to similar range as overall (0-100)
        # High need (0.8+) should make a 75 OVR player competitive with 85 OVR low-need
        need_score = team_need_score * 100

        # Combine with weights
        score = (talent_score * talent_weight) + (need_score * need_weight)

        return score

    def will_trade_pick(self, pick_round: int, pick_position: int) -> tuple[bool, str]:
        """
        Determine if team wants to trade a draft pick.

        Returns (wants_to_trade, direction) where direction is 'up', 'down', or 'none'.
        """
        if self.trade_aggression == TradeAggression.STANDPAT:
            return (False, "none")

        # Trade down teams look to move back in early rounds
        if self.draft_strategy == DraftStrategy.TRADE_DOWN:
            if pick_round <= 2 and random.random() < 0.6:
                return (True, "down")

        # Trade up teams look to move up for premium picks
        if self.draft_strategy == DraftStrategy.TRADE_UP:
            if pick_round <= 3 and random.random() < 0.4:
                return (True, "up")

        # Win now teams trade futures for current picks
        if self.future_pick_value == FuturePickValue.WIN_NOW:
            if pick_round >= 4 and random.random() < 0.3:
                return (True, "down")  # Trade future late picks

        # Heavy traders occasionally make moves
        if self.trade_aggression == TradeAggression.HEAVY_TRADER:
            if random.random() < 0.2:
                return (True, random.choice(["up", "down"]))

        return (False, "none")

    def calculate_player_overall(
        self, attributes: "PlayerAttributes", position: str
    ) -> int:
        """
        Calculate a player's OVR according to this team's philosophies.

        Different teams will see different OVR values for the same player
        based on their positional philosophies.

        Args:
            attributes: The player's attribute values
            position: The player's position

        Returns:
            Overall rating according to this team's evaluation
        """
        from huddle.core.philosophy.evaluation import calculate_philosophy_overall
        return calculate_philosophy_overall(attributes, position, self.philosophies)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "draft_strategy": self.draft_strategy.value,
            "trade_aggression": self.trade_aggression.value,
            "negotiation_tone": self.negotiation_tone.value,
            "future_pick_value": self.future_pick_value.value,
            "cap_management": self.cap_management.value,
            "offensive_scheme": self.offensive_scheme.value,
            "defensive_scheme": self.defensive_scheme.value,
            "philosophies": self.philosophies.to_dict(),
            "run_tendency": self.run_tendency,
            "aggression": self.aggression,
            "blitz_tendency": self.blitz_tendency,
            "position_values": self.position_values,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TeamTendencies":
        """Create from dictionary."""
        # Handle legacy data with old positional_philosophy format
        philosophies_data = data.get("philosophies", {})
        if not philosophies_data and "positional_philosophy" in data:
            # Legacy format - use defaults
            philosophies = TeamPhilosophies()
        else:
            philosophies = TeamPhilosophies.from_dict(philosophies_data)

        return cls(
            draft_strategy=DraftStrategy(data.get("draft_strategy", "balanced")),
            trade_aggression=TradeAggression(data.get("trade_aggression", "moderate")),
            negotiation_tone=NegotiationTone(data.get("negotiation_tone", "fair")),
            future_pick_value=FuturePickValue(data.get("future_pick_value", "balanced")),
            cap_management=CapManagement(data.get("cap_management", "moderate")),
            offensive_scheme=OffensiveScheme(data.get("offensive_scheme", "pro_style")),
            defensive_scheme=DefensiveScheme(data.get("defensive_scheme", "4-3")),
            philosophies=philosophies,
            run_tendency=data.get("run_tendency", 0.5),
            aggression=data.get("aggression", 0.5),
            blitz_tendency=data.get("blitz_tendency", 0.3),
            position_values=data.get("position_values", {}),
        )

    @classmethod
    def generate_random(cls) -> "TeamTendencies":
        """Generate random tendencies for a team."""
        return cls(
            draft_strategy=random.choice(list(DraftStrategy)),
            trade_aggression=random.choice(list(TradeAggression)),
            negotiation_tone=random.choice(list(NegotiationTone)),
            future_pick_value=random.choice(list(FuturePickValue)),
            cap_management=random.choice(list(CapManagement)),
            offensive_scheme=random.choice(list(OffensiveScheme)),
            defensive_scheme=random.choice(list(DefensiveScheme)),
            philosophies=TeamPhilosophies.generate_random(),
            run_tendency=random.uniform(0.3, 0.7),
            aggression=random.uniform(0.3, 0.7),
            blitz_tendency=random.uniform(0.2, 0.5),
        )
