"""Block Resolution System - Resolves OL vs DL engagements.

Handles the physical interaction between offensive and defensive linemen.
Determines who wins each rep and what movement results.

The brains decide WHAT to do (anchor, bull_rush, swim, etc.)
This resolver determines WHAT ACTUALLY HAPPENS.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Tuple, TYPE_CHECKING

from ..core.vec2 import Vec2
from ..core.events import EventBus, EventType

if TYPE_CHECKING:
    from ..core.entities import Player


# =============================================================================
# Constants
# =============================================================================

ENGAGEMENT_RANGE = 1.5  # Yards - players within this are engaged
SHED_THRESHOLD = 1.0    # Shed progress reaches this = DL is free

# Base win rates (before attribute modifiers)
BASE_OL_WIN_RATE = 0.50  # 50/50 at equal attributes

# Attribute weights for pass blocking
PASS_BLOCK_WEIGHTS = {
    "block_finesse": 0.35,
    "block_power": 0.25,
    "strength": 0.25,
    "awareness": 0.15,
}

PASS_RUSH_WEIGHTS = {
    "pass_rush": 0.40,
    "strength": 0.25,
    "speed": 0.20,
    "agility": 0.15,
}

# Attribute weights for run blocking
RUN_BLOCK_WEIGHTS = {
    "block_power": 0.40,
    "strength": 0.35,
    "block_finesse": 0.15,
    "awareness": 0.10,
}

RUN_DEFENSE_WEIGHTS = {
    "strength": 0.35,
    "pass_rush": 0.30,  # Reuse pass_rush for block shedding
    "tackling": 0.20,
    "awareness": 0.15,
}

# Shed progress rates per tick when winning
SHED_RATE_DOMINANT = 0.15   # DL dominating
SHED_RATE_WINNING = 0.08    # DL winning
SHED_RATE_NEUTRAL = 0.02    # Stalemate (slow progress)
SHED_RATE_LOSING = -0.05    # OL winning (progress reversed)

# Movement rates (yards per second)
PUSH_RATE_DOMINANT = 1.5    # Winner pushing loser back
PUSH_RATE_WINNING = 0.8
PUSH_RATE_NEUTRAL = 0.0


# =============================================================================
# Enums
# =============================================================================

class BlockOutcome(str, Enum):
    """Outcome of a single tick of blocking."""
    OL_DOMINANT = "ol_dominant"    # OL clearly winning, driving DL back
    OL_WINNING = "ol_winning"      # OL has edge, holding ground
    NEUTRAL = "neutral"            # Stalemate
    DL_WINNING = "dl_winning"      # DL has edge, making progress
    DL_DOMINANT = "dl_dominant"    # DL clearly winning, pushing through
    DL_SHED = "dl_shed"            # DL beat the block, now free
    DISENGAGED = "disengaged"      # Not in contact


class BlockType(str, Enum):
    """Type of blocking situation."""
    PASS_PRO = "pass_pro"     # Pass protection
    RUN_BLOCK = "run_block"   # Run blocking
    PULL = "pull"             # Pulling blocker


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class BlockResult:
    """Result of block resolution for one tick."""
    outcome: BlockOutcome

    # Movement
    ol_new_pos: Vec2           # Where OL ends up
    dl_new_pos: Vec2           # Where DL ends up

    # Shed tracking
    shed_progress: float       # 0.0 to 1.0, DL sheds at 1.0

    # Win probability (for debugging/tuning)
    ol_win_prob: float = 0.5

    # Debug info
    reasoning: str = ""


@dataclass
class EngagementState:
    """Tracks ongoing engagement between OL and DL."""
    ol_id: str
    dl_id: str
    shed_progress: float = 0.0
    ticks_engaged: int = 0
    block_type: BlockType = BlockType.PASS_PRO

    # Last actions (for counter detection)
    last_ol_action: Optional[str] = None
    last_dl_action: Optional[str] = None


# =============================================================================
# Action Matchup Matrix
# =============================================================================

# How well each DL move does against each OL counter
# Positive = DL advantage, Negative = OL advantage
ACTION_MATCHUPS = {
    # DL move: {OL counter: modifier}
    "bull_rush": {
        "anchor": -0.10,      # Anchor is good vs bull rush
        "punch": 0.05,        # Punch is okay
        "mirror": 0.15,       # Mirror doesn't help vs power
        "refit": 0.10,
    },
    "swim": {
        "anchor": 0.15,       # Anchor doesn't stop swim
        "punch": -0.10,       # Punch disrupts swim
        "mirror": 0.05,
        "refit": -0.05,
    },
    "spin": {
        "anchor": 0.10,
        "punch": 0.05,
        "mirror": 0.15,       # Mirror struggles with spin
        "refit": -0.15,       # Refit is designed for spin
    },
    "rip": {
        "anchor": 0.10,
        "punch": -0.05,
        "mirror": 0.00,
        "refit": -0.10,
    },
    "speed_rush": {
        "anchor": 0.20,       # Anchor too slow
        "punch": 0.10,
        "mirror": -0.15,      # Mirror is for speed rush
        "refit": 0.05,
    },
    "club_swim": {
        "anchor": 0.05,
        "punch": -0.05,
        "mirror": 0.00,
        "refit": -0.05,
    },
    "long_arm": {
        "anchor": -0.05,
        "punch": -0.10,       # Punch beats long arm
        "mirror": 0.05,
        "refit": 0.00,
    },
}

# Default matchup when action not in matrix
DEFAULT_MATCHUP = 0.0


# =============================================================================
# Block Resolver
# =============================================================================

class BlockResolver:
    """Resolves OL vs DL blocking engagements.

    Usage:
        resolver = BlockResolver(event_bus)

        # Each tick, for each engaged OL/DL pair:
        result = resolver.resolve(
            ol_player, dl_player,
            ol_action="anchor", dl_action="bull_rush",
            block_type=BlockType.PASS_PRO,
            dt=0.05
        )

        # Apply result
        ol_player.pos = result.ol_new_pos
        dl_player.pos = result.dl_new_pos

        if result.outcome == BlockOutcome.DL_SHED:
            dl_player.is_engaged = False  # DL is free!
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus
        self._engagements: dict[str, EngagementState] = {}  # Key: "ol_id:dl_id"

    def get_engagement_key(self, ol_id: str, dl_id: str) -> str:
        """Get unique key for an engagement."""
        return f"{ol_id}:{dl_id}"

    def get_engagement(self, ol_id: str, dl_id: str) -> Optional[EngagementState]:
        """Get existing engagement state."""
        return self._engagements.get(self.get_engagement_key(ol_id, dl_id))

    def get_engagement_for_player(self, player_id: str) -> Optional[EngagementState]:
        """Get engagement state for a player (either OL or DL)."""
        for engagement in self._engagements.values():
            if engagement.ol_id == player_id or engagement.dl_id == player_id:
                return engagement
        return None

    def clear_engagements(self) -> None:
        """Clear all engagement states (start of new play)."""
        self._engagements.clear()

    def is_engaged(self, ol: Player, dl: Player) -> bool:
        """Check if two players are within engagement range."""
        return ol.pos.distance_to(dl.pos) <= ENGAGEMENT_RANGE

    def resolve(
        self,
        ol: Player,
        dl: Player,
        ol_action: str,
        dl_action: str,
        block_type: BlockType,
        dt: float,
        tick: int = 0,
        time: float = 0.0,
    ) -> BlockResult:
        """Resolve one tick of blocking between OL and DL.

        Args:
            ol: Offensive lineman
            dl: Defensive lineman
            ol_action: OL's blocking action (anchor, punch, etc.)
            dl_action: DL's rush move (bull_rush, swim, etc.)
            block_type: Pass protection or run blocking
            dt: Time step
            tick: Current tick (for events)
            time: Current time (for events)

        Returns:
            BlockResult with outcome and new positions
        """
        distance = ol.pos.distance_to(dl.pos)

        # Check if actually engaged
        if distance > ENGAGEMENT_RANGE:
            return BlockResult(
                outcome=BlockOutcome.DISENGAGED,
                ol_new_pos=ol.pos,
                dl_new_pos=dl.pos,
                shed_progress=0.0,
                reasoning="Not in engagement range",
            )

        # Get or create engagement state
        key = self.get_engagement_key(ol.id, dl.id)
        if key not in self._engagements:
            self._engagements[key] = EngagementState(
                ol_id=ol.id,
                dl_id=dl.id,
                block_type=block_type,
            )

        state = self._engagements[key]
        state.ticks_engaged += 1
        state.last_ol_action = ol_action
        state.last_dl_action = dl_action

        # Calculate win probability
        ol_win_prob = self._calculate_win_probability(
            ol, dl, ol_action, dl_action, block_type
        )

        # Roll for this tick's outcome
        roll = random.random()

        # Determine outcome based on roll vs probability
        margin = roll - ol_win_prob

        if margin < -0.25:
            outcome = BlockOutcome.OL_DOMINANT
            shed_delta = SHED_RATE_LOSING * 1.5
        elif margin < -0.10:
            outcome = BlockOutcome.OL_WINNING
            shed_delta = SHED_RATE_LOSING
        elif margin < 0.10:
            outcome = BlockOutcome.NEUTRAL
            shed_delta = SHED_RATE_NEUTRAL
        elif margin < 0.25:
            outcome = BlockOutcome.DL_WINNING
            shed_delta = SHED_RATE_WINNING
        else:
            outcome = BlockOutcome.DL_DOMINANT
            shed_delta = SHED_RATE_DOMINANT

        # Update shed progress
        state.shed_progress = max(0.0, min(1.0, state.shed_progress + shed_delta))

        # Check for shed
        if state.shed_progress >= SHED_THRESHOLD:
            outcome = BlockOutcome.DL_SHED
            self._emit_event(
                EventType.BLOCK_SHED,
                dl.id,
                f"{dl.name} sheds block from {ol.name}",
                tick, time,
                {"ol_id": ol.id, "move": dl_action},
            )
            # Remove engagement
            del self._engagements[key]

        # Calculate movement
        ol_new_pos, dl_new_pos = self._calculate_movement(
            ol, dl, outcome, block_type, dt
        )

        # Build reasoning
        reasoning = f"{ol_action} vs {dl_action}: {outcome.value} (OL win prob: {ol_win_prob:.0%}, shed: {state.shed_progress:.0%})"

        return BlockResult(
            outcome=outcome,
            ol_new_pos=ol_new_pos,
            dl_new_pos=dl_new_pos,
            shed_progress=state.shed_progress,
            ol_win_prob=ol_win_prob,
            reasoning=reasoning,
        )

    def _calculate_win_probability(
        self,
        ol: Player,
        dl: Player,
        ol_action: str,
        dl_action: str,
        block_type: BlockType,
    ) -> float:
        """Calculate probability that OL wins this tick.

        Returns:
            Float from 0.0 (DL always wins) to 1.0 (OL always wins)
        """
        # Start with base rate
        prob = BASE_OL_WIN_RATE

        # Get attribute weights based on block type
        if block_type == BlockType.PASS_PRO:
            ol_weights = PASS_BLOCK_WEIGHTS
            dl_weights = PASS_RUSH_WEIGHTS
        else:
            ol_weights = RUN_BLOCK_WEIGHTS
            dl_weights = RUN_DEFENSE_WEIGHTS

        # Calculate weighted attribute scores
        ol_score = self._calculate_attribute_score(ol, ol_weights)
        dl_score = self._calculate_attribute_score(dl, dl_weights)

        # Attribute difference modifier
        # +10 attribute advantage = +10% win rate
        attr_diff = (ol_score - dl_score) / 100
        prob += attr_diff

        # Action matchup modifier
        matchup_mod = self._get_action_matchup(dl_action, ol_action)
        prob -= matchup_mod  # Subtract because positive = DL advantage

        # Clamp to valid range
        return max(0.15, min(0.85, prob))

    def _calculate_attribute_score(
        self,
        player: Player,
        weights: dict[str, float],
    ) -> float:
        """Calculate weighted attribute score."""
        score = 0.0
        total_weight = 0.0

        for attr_name, weight in weights.items():
            value = getattr(player.attributes, attr_name, 75)  # Default to 75
            score += value * weight
            total_weight += weight

        if total_weight > 0:
            score /= total_weight

        return score

    def _get_action_matchup(self, dl_action: str, ol_action: str) -> float:
        """Get matchup modifier for action pairing."""
        dl_action_lower = dl_action.lower() if dl_action else ""
        ol_action_lower = ol_action.lower() if ol_action else ""

        if dl_action_lower in ACTION_MATCHUPS:
            return ACTION_MATCHUPS[dl_action_lower].get(ol_action_lower, DEFAULT_MATCHUP)

        return DEFAULT_MATCHUP

    def _calculate_movement(
        self,
        ol: Player,
        dl: Player,
        outcome: BlockOutcome,
        block_type: BlockType,
        dt: float,
    ) -> Tuple[Vec2, Vec2]:
        """Calculate new positions based on outcome."""
        ol_pos = ol.pos
        dl_pos = dl.pos

        # Direction from OL to DL (toward defense)
        if ol_pos.distance_to(dl_pos) > 0.1:
            push_dir = (dl_pos - ol_pos).normalized()
        else:
            push_dir = Vec2(0, 1)  # Default to upfield

        # Determine push rate and direction based on outcome
        if outcome == BlockOutcome.OL_DOMINANT:
            # OL drives DL back
            push_rate = PUSH_RATE_DOMINANT
            dl_new = dl_pos + push_dir * push_rate * dt
            ol_new = ol_pos + push_dir * push_rate * dt * 0.5  # OL follows

        elif outcome == BlockOutcome.OL_WINNING:
            # OL pushes DL back slightly
            push_rate = PUSH_RATE_WINNING
            dl_new = dl_pos + push_dir * push_rate * dt
            ol_new = ol_pos + push_dir * push_rate * dt * 0.3

        elif outcome == BlockOutcome.DL_DOMINANT:
            # DL drives through OL
            push_rate = PUSH_RATE_DOMINANT
            ol_new = ol_pos - push_dir * push_rate * dt  # OL pushed back
            dl_new = dl_pos - push_dir * push_rate * dt * 0.5  # DL advances

        elif outcome == BlockOutcome.DL_WINNING:
            # DL pushes through slowly
            push_rate = PUSH_RATE_WINNING
            ol_new = ol_pos - push_dir * push_rate * dt
            dl_new = dl_pos - push_dir * push_rate * dt * 0.3

        elif outcome == BlockOutcome.DL_SHED:
            # DL breaks free, moves toward QB area
            ol_new = ol_pos  # OL stays (beat)
            # DL moves past OL
            dl_new = dl_pos - push_dir * 2.0 * dt

        else:  # NEUTRAL or DISENGAGED
            ol_new = ol_pos
            dl_new = dl_pos

        return ol_new, dl_new

    def _emit_event(
        self,
        event_type: EventType,
        player_id: str,
        description: str,
        tick: int,
        time: float,
        data: dict = None,
    ) -> None:
        """Emit an event if event bus available."""
        if self.event_bus:
            self.event_bus.emit_simple(
                event_type,
                tick,
                time,
                player_id=player_id,
                description=description,
                data=data or {},
            )


# =============================================================================
# Convenience Functions
# =============================================================================

def find_blocking_matchups(
    offense: List[Player],
    defense: List[Player],
) -> List[Tuple[Player, Player]]:
    """Find OL/DL pairs that are engaged or should engage.

    Simple nearest-neighbor matching for now.
    """
    from ..core.entities import Position

    OL_POSITIONS = {Position.LT, Position.LG, Position.C, Position.RG, Position.RT}
    DL_POSITIONS = {Position.DE, Position.DT, Position.NT}

    matchups = []
    used_dl = set()

    # For each OL, find nearest DL
    for ol in offense:
        if ol.position not in OL_POSITIONS:
            continue

        nearest_dl = None
        nearest_dist = float('inf')

        for dl in defense:
            if dl.position not in DL_POSITIONS:
                continue
            if dl.id in used_dl:
                continue

            dist = ol.pos.distance_to(dl.pos)
            if dist < nearest_dist and dist < 5.0:  # Max 5 yards to consider
                nearest_dist = dist
                nearest_dl = dl

        if nearest_dl:
            matchups.append((ol, nearest_dl))
            used_dl.add(nearest_dl.id)

    return matchups
