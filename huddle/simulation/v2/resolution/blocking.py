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
from ..core.entities import Position
from ..core.variance import sigmoid_matchup_probability

if TYPE_CHECKING:
    from ..core.entities import Player


# =============================================================================
# Constants
# =============================================================================

ENGAGEMENT_RANGE = 1.5  # Yards - players within this are engaged
SHED_THRESHOLD = 1.0    # Shed progress reaches this = DL is free
MIN_SEPARATION = 0.8    # Yards - minimum distance between OL/DL bodies (can't clip through)

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

# Shed progress rates per tick when winning (RUN BLOCKING)
# Run blocking is quicker - need to make fast decisions
SHED_RATE_DOMINANT = 0.15   # DL dominating - sheds in ~0.35s
SHED_RATE_WINNING = 0.08    # DL winning - sheds in ~0.6s
SHED_RATE_NEUTRAL = 0.02    # Stalemate (slow progress)
SHED_RATE_LOSING = -0.05    # OL winning (progress reversed)

# Shed progress rates for PASS PROTECTION
# Pass pro is slower - OL sets up and maintains leverage
# Target: average matchup holds ~2.5-3 seconds
PASS_PRO_SHED_RATE_DOMINANT = 0.06   # DL dominating - sheds in ~0.8s
PASS_PRO_SHED_RATE_WINNING = 0.03    # DL winning - sheds in ~1.7s
PASS_PRO_SHED_RATE_NEUTRAL = 0.01    # Stalemate - sheds in ~5s
PASS_PRO_SHED_RATE_LOSING = -0.02    # OL winning (slow reversal)

# Movement rates (yards per second)
# Increased for visual clarity in demos - real NFL would be slower
PUSH_RATE_DOMINANT = 1.2    # Clear winner - ~6 yards over 5 sec (pancake territory)
PUSH_RATE_WINNING = 0.5     # Has edge - ~2.5 yards over 5 sec
PUSH_RATE_NEUTRAL = 0.0     # Stalemate - both hold position

# =============================================================================
# Momentum System Constants
# =============================================================================

# Leverage change rate - how fast leverage shifts per tick
# Based on attribute advantage (per 10 pts of advantage)
# Higher = faster visual feedback for attribute differences
LEVERAGE_SHIFT_RATE = 0.12  # Needs to be high enough to break out of neutral zone

# Run blocking gets faster leverage shifts - OL fires off the ball with purpose
# and the battle is decided quicker than pass protection
RUN_BLOCKING_LEVERAGE_MULTIPLIER = 1.5

# =============================================================================
# NFL Win Rate Calibration (based on real data)
# =============================================================================
# Pass blocking: OL wins 92-99% of reps. Elite DT PRWR is only 9-20%.
# Run blocking: OL wins 70-86% of reps. Elite DT RSWR is 38-46%.
#
# Initial leverage determines who "wins" most reps.
# Leverage of 0.5+ = OL wins, -0.5+ = DL wins
# To get 90%+ OL win rate in pass pro, start leverage high
# To get 75% OL win rate in run blocking, start leverage moderate

# Pass protection - OL should win 90%+ of reps
# Elite pass rushers only win 15-25% of the time
PASS_BLOCK_CHARGE_BONUS = 0.55  # OL starts with big advantage in pass pro

# Run blocking - OL should win 70-85% of reps
# DTs are BETTER at run stopping (38-46%) than pass rushing (9-20%)
RUN_BLOCKING_CHARGE_BONUS = 0.30  # More competitive in run game

# Position-specific adjustments
# DTs win fewer pass rush reps but more run stop reps than edge
DT_PASS_RUSH_PENALTY = 0.08   # DTs are worse pass rushers (9-20% vs 15-26%)
DT_RUN_STOP_BONUS = 0.10      # DTs are better run stoppers (38-46% vs 29-39%)

# Momentum decay - leverage momentum decays each tick
# 1.0 = no decay, 0.5 = halves each tick
MOMENTUM_DECAY = 0.85

# Momentum influence - how much momentum contributes to leverage shift
MOMENTUM_FACTOR = 0.6

# Stagger threshold - when leverage hits these, player staggers
STAGGER_THRESHOLD = 0.85

# Stagger duration in ticks
STAGGER_DURATION = 8

# Stagger leverage bonus - staggered player gives up leverage faster
STAGGER_LEVERAGE_BONUS = 0.08

# Drive threshold - commit to drive when leverage advantage is this high
DRIVE_THRESHOLD = 0.6

# Drive duration in ticks
DRIVE_DURATION = 6

# Drive leverage bonus during committed drive
DRIVE_LEVERAGE_BONUS = 0.03

# Random variance added each tick (small)
VARIANCE_PER_TICK = 0.02

# =============================================================================
# Play-Level Blocking Quality System
# =============================================================================
# NFL blocking is correlated - sometimes the whole OL fires off well,
# sometimes they all struggle. This creates the variance in run outcomes.
#
# On any given play:
# - 15% chance OL executes GREAT → all get bonus → explosive run potential
# - 20% chance OL executes POOR → all get penalty → stuff potential
# - 65% chance AVERAGE → normal outcomes → 3-4 yard run

PLAY_QUALITY_GREAT_CHANCE = 0.18  # 18% of plays OL dominates (fills 7-9 yard bucket)
PLAY_QUALITY_POOR_CHANCE = 0.17   # 17% of plays DL wins up front
# 65% average

GREAT_BLOCKING_LEVERAGE_BONUS = 0.25   # OL gets big initial leverage boost
POOR_BLOCKING_LEVERAGE_PENALTY = 0.30  # DL gets leverage advantage

# Track current play quality (set at snap)
_current_play_quality: str = "average"  # "great", "average", "poor"


def roll_play_blocking_quality() -> str:
    """Roll for this play's blocking quality. Call at snap.

    Returns:
        "great", "average", or "poor"
    """
    global _current_play_quality

    roll = random.random()
    if roll < PLAY_QUALITY_GREAT_CHANCE:
        _current_play_quality = "great"
    elif roll < PLAY_QUALITY_GREAT_CHANCE + PLAY_QUALITY_POOR_CHANCE:
        _current_play_quality = "poor"
    else:
        _current_play_quality = "average"

    return _current_play_quality


def get_play_blocking_quality() -> str:
    """Get current play's blocking quality."""
    return _current_play_quality


def reset_play_blocking_quality() -> None:
    """Reset to average (for new play)."""
    global _current_play_quality
    _current_play_quality = "average"


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

    # Momentum system - makes blocking feel weighty
    # leverage: -1.0 = DL fully dominant, +1.0 = OL fully dominant
    leverage: float = 0.0

    # How fast leverage is shifting (positive = toward OL, negative = toward DL)
    leverage_momentum: float = 0.0

    # Stagger: when a player gets knocked back hard, they need recovery
    # Positive = OL staggered, Negative = DL staggered
    stagger_ticks: int = 0

    # Drive state: when one side commits to driving, they push for several ticks
    drive_direction: Optional[Vec2] = None
    drive_ticks_remaining: int = 0


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

    def remove_engagement(self, dl_id: str) -> bool:
        """Remove engagement for a DL (when they disengage to tackle).

        Returns True if an engagement was removed.
        """
        keys_to_remove = []
        for key, engagement in self._engagements.items():
            if engagement.dl_id == dl_id:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._engagements[key]

        return len(keys_to_remove) > 0

    def attempt_emergency_shed(self, dl_id: str) -> tuple[bool, float]:
        """Attempt emergency shed when ballcarrier is nearby.

        When an RB runs past an engaged DL, the DL can try to disengage
        and make a tackle. Success depends on current shed_progress.

        Args:
            dl_id: ID of the defensive lineman

        Returns:
            (success, probability): Whether shed succeeded and what the roll was
        """
        import random

        engagement = self.get_engagement_for_player(dl_id)
        if not engagement:
            return False, 0.0

        # Emergency shed probability based on current shed progress
        # Already winning the battle = easier to disengage
        # shed_progress 0.0 = 15% chance (OL dominant, hard to escape)
        # shed_progress 0.5 = 40% chance (neutral battle)
        # shed_progress 0.8 = 65% chance (already close to shedding)
        # shed_progress 1.0 = already shed, should be free
        base_prob = 0.15 + (engagement.shed_progress * 0.55)

        # Leverage also matters - positive leverage = DL winning
        leverage_bonus = max(0, -engagement.leverage) * 0.15  # Up to +15% if DL has leverage

        final_prob = min(0.75, base_prob + leverage_bonus)

        roll = random.random()
        success = roll < final_prob

        return success, final_prob

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
        block_direction: str = "",  # "left", "right", or "straight" - OL's intended push direction
    ) -> BlockResult:
        """Resolve one tick of blocking between OL and DL.

        Uses a momentum-based system where leverage shifts gradually based on
        attribute matchups. Creates sustained advantages rather than coin-flip
        outcomes each tick.

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
            # Initial leverage based on block type
            # Calibrated to NFL win rates:
            # - Pass blocking: OL wins 90%+ (PBWR 92-99%)
            # - Run blocking: OL wins 70-85% (RBWR 70-86%)
            if block_type == BlockType.RUN_BLOCK:
                initial_leverage = RUN_BLOCKING_CHARGE_BONUS
                # DTs are BETTER at run stopping than edge rushers
                # DT RSWR: 38-46% vs Edge RSWR: 29-39%
                if dl.position in (Position.DT, Position.NT):
                    initial_leverage -= DT_RUN_STOP_BONUS  # DT gets bonus (reduces OL advantage)

                # Apply play-level blocking quality (creates run game variance)
                # This is the key to explosive plays and stuffs
                play_quality = get_play_blocking_quality()
                if play_quality == "great":
                    initial_leverage += GREAT_BLOCKING_LEVERAGE_BONUS  # OL dominates → big play potential
                elif play_quality == "poor":
                    initial_leverage -= POOR_BLOCKING_LEVERAGE_PENALTY  # DL wins → stuff potential
            else:
                initial_leverage = PASS_BLOCK_CHARGE_BONUS
                # DTs are WORSE at pass rushing than edge rushers
                # DT PRWR: 9-20% vs Edge PRWR: 15-26%
                if dl.position in (Position.DT, Position.NT):
                    initial_leverage += DT_PASS_RUSH_PENALTY  # DT gets penalty (increases OL advantage)

            self._engagements[key] = EngagementState(
                ol_id=ol.id,
                dl_id=dl.id,
                block_type=block_type,
                leverage=initial_leverage,
            )

        state = self._engagements[key]
        state.ticks_engaged += 1
        state.last_ol_action = ol_action
        state.last_dl_action = dl_action

        # === MOMENTUM-BASED LEVERAGE SYSTEM ===

        # 1. Calculate base leverage shift from attributes and actions
        leverage_shift = self._calculate_leverage_shift(
            ol, dl, ol_action, dl_action, block_type
        )

        # Run blocking has faster leverage shifts - battles resolve quicker
        if block_type == BlockType.RUN_BLOCK:
            leverage_shift *= RUN_BLOCKING_LEVERAGE_MULTIPLIER

        # 2. Handle stagger state - staggered player gives up leverage faster
        if state.stagger_ticks > 0:
            state.stagger_ticks -= 1
            # Apply stagger penalty (positive stagger = OL staggered)
            if state.stagger_ticks > 0:
                leverage_shift -= STAGGER_LEVERAGE_BONUS  # Shifts toward DL

        # 3. Handle drive state - committed drive maintains pressure
        if state.drive_ticks_remaining > 0:
            state.drive_ticks_remaining -= 1
            # Drive direction: positive leverage = OL driving
            if state.leverage > 0:
                leverage_shift += DRIVE_LEVERAGE_BONUS
            else:
                leverage_shift -= DRIVE_LEVERAGE_BONUS

        # 4. Apply momentum - smooth out the leverage changes
        # Momentum decays each tick
        state.leverage_momentum *= MOMENTUM_DECAY

        # Add this tick's influence to momentum
        state.leverage_momentum += leverage_shift * (1.0 - MOMENTUM_DECAY)

        # Apply momentum to leverage
        leverage_delta = leverage_shift + state.leverage_momentum * MOMENTUM_FACTOR

        # 5. Add small random variance (keeps it from being perfectly deterministic)
        variance = (random.random() - 0.5) * VARIANCE_PER_TICK * 2
        leverage_delta += variance

        # 6. Update leverage
        state.leverage = max(-1.0, min(1.0, state.leverage + leverage_delta))

        # 7. Check for stagger trigger (big leverage swing)
        if abs(state.leverage) >= STAGGER_THRESHOLD and state.stagger_ticks == 0:
            # Player getting dominated staggers
            state.stagger_ticks = STAGGER_DURATION
            # Reset leverage slightly (stagger creates a pause)
            if state.leverage > 0:
                state.leverage = STAGGER_THRESHOLD * 0.7
            else:
                state.leverage = -STAGGER_THRESHOLD * 0.7

        # 8. Check for drive trigger (sustained advantage)
        if abs(state.leverage) >= DRIVE_THRESHOLD and state.drive_ticks_remaining == 0:
            state.drive_ticks_remaining = DRIVE_DURATION
            # Set drive direction based on who's winning
            push_dir = (dl.pos - ol.pos).normalized() if ol.pos.distance_to(dl.pos) > 0.1 else Vec2(0, 1)
            if state.leverage > 0:
                state.drive_direction = push_dir  # OL driving forward
            else:
                state.drive_direction = push_dir * -1  # DL driving backward

        # === MAP LEVERAGE TO OUTCOME ===
        outcome = self._leverage_to_outcome(state.leverage)

        # === UPDATE SHED PROGRESS ===
        # Shed progress only advances when DL has leverage advantage
        # Use different rates for pass protection vs run blocking
        is_pass_pro = block_type == BlockType.PASS_PRO

        # === PASS RUSH "QUICK BEAT" MECHANIC ===
        # DL can occasionally execute a successful pass rush move
        # that dramatically accelerates shed progress.
        # This creates the variability needed for ~6.5% sack rate.
        #
        # Calibration for ~6.5% sack rate:
        # - 4 DL rushing for ~50 ticks (2.5 seconds before typical throw)
        # - Need ~8-10% of plays to have a DL get free early
        # - ~65% of "free" DL convert to sack (some QB escapes, some don't reach)
        # - Target: ~6% base chance per tick per DL for quick beat attempt
        if is_pass_pro:
            # Quick beat chance - based on DL pass rush skill vs OL block power
            dl_pass_rush = getattr(dl.attributes, 'pass_rush', 75)
            ol_block_power = getattr(ol.attributes, 'block_power', 75)

            # Base 2% chance per tick, modified by skill differential
            # Calibrated to balance sack rate (~6.5%) vs completion rate (~60%)
            # Reduced base from 3% to 2% - sack rate was 12%, target 6.5%
            # Too high = too many incomplete/sacks, too low = no pass rush
            skill_diff = (dl_pass_rush - ol_block_power) / 100
            quick_beat_chance = 0.02 + skill_diff * 0.02  # 1.0% to 4.0%
            quick_beat_chance = max(0.01, min(0.04, quick_beat_chance))

            if random.random() < quick_beat_chance:
                # Successful pass rush move! Instant shed
                state.shed_progress = 1.0  # Instant shed
                # Shift leverage toward DL
                state.leverage = -0.6

        if state.leverage < -0.5:
            shed_delta = PASS_PRO_SHED_RATE_DOMINANT if is_pass_pro else SHED_RATE_DOMINANT
        elif state.leverage < -0.2:
            shed_delta = PASS_PRO_SHED_RATE_WINNING if is_pass_pro else SHED_RATE_WINNING
        elif state.leverage < 0.2:
            shed_delta = PASS_PRO_SHED_RATE_NEUTRAL if is_pass_pro else SHED_RATE_NEUTRAL
        elif state.leverage < 0.5:
            shed_delta = PASS_PRO_SHED_RATE_LOSING if is_pass_pro else SHED_RATE_LOSING
        else:
            losing_rate = PASS_PRO_SHED_RATE_LOSING if is_pass_pro else SHED_RATE_LOSING
            shed_delta = losing_rate * 1.5

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

        # Calculate movement - now influenced by drive state and block direction
        ol_new_pos, dl_new_pos = self._calculate_movement(
            ol, dl, outcome, block_type, dt, state, block_direction
        )

        # Build reasoning with momentum info
        reasoning = (
            f"{ol_action} vs {dl_action}: {outcome.value} "
            f"(leverage: {state.leverage:+.2f}, momentum: {state.leverage_momentum:+.2f}, "
            f"shed: {state.shed_progress:.0%})"
        )

        return BlockResult(
            outcome=outcome,
            ol_new_pos=ol_new_pos,
            dl_new_pos=dl_new_pos,
            shed_progress=state.shed_progress,
            ol_win_prob=0.5 + state.leverage * 0.35,  # Approximate for debugging
            reasoning=reasoning,
        )

    def _calculate_leverage_shift(
        self,
        ol: Player,
        dl: Player,
        ol_action: str,
        dl_action: str,
        block_type: BlockType,
    ) -> float:
        """Calculate how much leverage shifts this tick.

        Positive = shifts toward OL (OL gaining advantage)
        Negative = shifts toward DL (DL gaining advantage)
        """
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

        # Attribute difference drives leverage shift
        # +10 attribute advantage = +0.04 leverage shift per tick
        attr_diff = (ol_score - dl_score) / 10.0
        shift = attr_diff * LEVERAGE_SHIFT_RATE

        # Action matchup modifier
        matchup_mod = self._get_action_matchup(dl_action, ol_action)
        shift -= matchup_mod * LEVERAGE_SHIFT_RATE * 2  # Actions have big impact

        return shift

    def _leverage_to_outcome(self, leverage: float) -> BlockOutcome:
        """Map leverage value to outcome enum."""
        if leverage >= 0.6:
            return BlockOutcome.OL_DOMINANT
        elif leverage >= 0.25:
            return BlockOutcome.OL_WINNING
        elif leverage >= -0.25:
            return BlockOutcome.NEUTRAL
        elif leverage >= -0.6:
            return BlockOutcome.DL_WINNING
        else:
            return BlockOutcome.DL_DOMINANT

    def _calculate_win_probability(
        self,
        ol: Player,
        dl: Player,
        ol_action: str,
        dl_action: str,
        block_type: BlockType,
    ) -> float:
        """Calculate probability that OL wins this tick.

        Uses sigmoid curve for attribute matchups to provide better
        differentiation at rating extremes. Elite players are in a
        class of their own - a 95 vs 70 is almost automatic.

        Returns:
            Float from 0.0 (DL always wins) to 1.0 (OL always wins)
        """
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

        # Use sigmoid curve for attribute matchup
        # This provides better differentiation at extremes:
        # - Elite OL (95) vs avg DL (75) = ~0.75 OL win rate
        # - Avg OL (75) vs elite DL (95) = ~0.25 OL win rate
        # - Even matchup (75 vs 75) = ~0.55 (slight OL advantage)
        base_prob = sigmoid_matchup_probability(
            int(ol_score), int(dl_score),
            base_advantage=0.05,  # Slight OL advantage (pass sets, knowing count)
            steepness=0.05,       # Gradual curve - blocking is sustained effort
            min_prob=0.20,
            max_prob=0.80,
        )

        # Action matchup modifier (still linear - represents technique choices)
        matchup_mod = self._get_action_matchup(dl_action, ol_action)
        prob = base_prob - matchup_mod * 0.15  # Scale matchup modifier

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
        state: Optional[EngagementState] = None,
        block_direction: str = "",
    ) -> Tuple[Vec2, Vec2]:
        """Calculate new positions based on outcome and momentum state.

        Key insight: DL is ALWAYS trying to get to their target (QB/ball).
        OL is trying to hold them back. The outcome determines who wins
        each tick, but there's always tension - it never fully stabilizes.

        During a committed drive, movement is more consistent and sustained.
        Otherwise, movement follows the outcome but with inertia from momentum.

        block_direction controls the "wash" - when OL is winning, they push
        the DL in their intended direction (playside for runs, slide direction
        for pass pro).
        """
        ol_pos = ol.pos
        dl_pos = dl.pos

        # Direction from OL to DL (toward defense)
        if ol_pos.distance_to(dl_pos) > 0.1:
            push_dir = (dl_pos - ol_pos).normalized()
        else:
            push_dir = Vec2(0, 1)  # Default to upfield

        # DL's target direction (toward QB/backfield = negative Y)
        # This represents the DL's constant effort to reach their target
        target_dir = Vec2(0, -1)  # Always pushing toward backfield
        DL_PRESSURE_RATE = 0.3  # Base pressure rate regardless of outcome

        # During a committed drive, use drive direction for consistent movement
        in_drive = state and state.drive_ticks_remaining > 0 and state.drive_direction
        drive_bonus = 1.3 if in_drive else 1.0  # 30% more movement during drive

        # Calculate wash direction based on OL's blocking intent
        # When OL is winning, they push DL in their intended direction
        # For runs: playside creates running lanes
        # For pass pro: slide direction walls off that side
        wash_dir = Vec2(0, 0)
        WASH_RATE = 0.8  # Yards per second of wash movement when OL winning
        RUN_WASH_RATE = 1.5  # Stronger wash for run blocking - need to move DL
        is_run_block = block_type == BlockType.RUN_BLOCK
        effective_wash_rate = RUN_WASH_RATE if is_run_block else WASH_RATE

        if block_direction == "right":
            # Push DL right and back (positive y = toward defense backfield)
            wash_dir = Vec2(1, 1).normalized()
        elif block_direction == "left":
            # Push DL left and back
            wash_dir = Vec2(-1, 1).normalized()
        elif is_run_block:
            # Run blocking with no lateral direction - just drive straight back
            wash_dir = Vec2(0, 1)  # Straight back toward defense
        # "straight" or empty for pass = no wash

        # Determine push rate and direction based on outcome
        # DL always applies pressure toward backfield, outcome determines if OL can counter it
        if outcome == BlockOutcome.OL_DOMINANT:
            # OL DOMINATES - drives DL in blocking direction
            # In run blocking, this creates the "wash" that opens lanes
            # DL gets NO forward progress when dominated
            wash_movement = wash_dir * effective_wash_rate * dt * 1.5
            if is_run_block:
                # Run blocking: OL drives DL back, no DL pressure allowed
                dl_new = dl_pos + wash_movement
                ol_new = ol_pos + wash_movement * 0.7
            else:
                # Pass pro: DL still applies slight pressure even when dominated
                push_rate = PUSH_RATE_DOMINANT * drive_bonus * 0.3
                dl_new = dl_pos + target_dir * DL_PRESSURE_RATE * dt * 0.1 + wash_movement
                ol_new = ol_pos + target_dir * DL_PRESSURE_RATE * dt * 0.1 + wash_movement * 0.8

        elif outcome == BlockOutcome.OL_WINNING:
            # OL winning - sustains block with moderate wash
            wash_movement = wash_dir * effective_wash_rate * dt * 0.8
            if is_run_block:
                # Run blocking: OL drives DL back moderately
                dl_new = dl_pos + wash_movement
                ol_new = ol_pos + wash_movement * 0.6
            else:
                # Pass pro: slight drift toward backfield
                drift_rate = DL_PRESSURE_RATE * 0.25
                dl_new = dl_pos + target_dir * drift_rate * dt + wash_movement
                ol_new = ol_pos + target_dir * drift_rate * dt * 0.8 + wash_movement * 0.8

        elif outcome == BlockOutcome.DL_DOMINANT:
            # DL pressure overwhelms OL, drives through
            # DL advances toward QB while maintaining contact with OL
            # Both move toward backfield together until shed
            push_rate = PUSH_RATE_DOMINANT * drive_bonus
            # Both move toward backfield, DL slightly faster (closing in)
            ol_new = ol_pos + target_dir * push_rate * dt * 0.8
            dl_new = dl_pos + target_dir * push_rate * dt  # DL advances toward QB

        elif outcome == BlockOutcome.DL_WINNING:
            # DL pressure winning, pushing through slowly
            # Both move toward backfield, maintaining contact
            push_rate = PUSH_RATE_WINNING * drive_bonus
            ol_new = ol_pos + target_dir * push_rate * dt * 0.5
            dl_new = dl_pos + target_dir * push_rate * dt * 0.7  # DL advances

        elif outcome == BlockOutcome.DL_SHED:
            # DL breaks free, sprints toward QB area
            ol_new = ol_pos  # OL stays (beat)
            dl_new = dl_pos + target_dir * 2.0 * dt  # Sprint toward backfield

        else:  # NEUTRAL or DISENGAGED
            # Stalemate - DL applies pressure, OL holds, slight oscillation
            # Neither side gaining ground but constant tension
            if state and abs(state.leverage_momentum) > 0.01:
                # Momentum causes slight drift
                drift = state.leverage_momentum * 0.3 * dt
                if state.leverage_momentum > 0:
                    # OL has momentum, DL gets pushed slightly
                    dl_new = dl_pos + push_dir * drift
                    ol_new = ol_pos + push_dir * drift * 0.3
                else:
                    # DL has momentum toward target
                    ol_new = ol_pos + target_dir * abs(drift) * 0.3
                    dl_new = dl_pos + target_dir * abs(drift) * 0.5
            else:
                # True stalemate
                if is_run_block:
                    # Run blocking: true neutral = nobody moves
                    # OL has charge advantage, so neutral means DL can't advance
                    dl_new = dl_pos
                    ol_new = ol_pos
                else:
                    # Pass pro: tiny oscillation to show tension
                    dl_new = dl_pos + target_dir * DL_PRESSURE_RATE * dt * 0.1
                    ol_new = ol_pos + target_dir * DL_PRESSURE_RATE * dt * 0.1

        # Enforce minimum separation - prevent clipping through each other
        ol_new, dl_new = self._enforce_separation(ol_new, dl_new, MIN_SEPARATION)

        return ol_new, dl_new

    def _enforce_separation(
        self,
        ol_pos: Vec2,
        dl_pos: Vec2,
        min_dist: float,
    ) -> Tuple[Vec2, Vec2]:
        """Ensure OL and DL maintain minimum separation distance.

        If players are too close, push them apart along their connecting axis.
        Each player is pushed proportionally (50/50 split).
        """
        dist = ol_pos.distance_to(dl_pos)

        if dist >= min_dist:
            return ol_pos, dl_pos

        if dist < 0.01:
            # Exactly overlapping - push apart along Y axis
            separation_dir = Vec2(0, 1)
            dist = 0.01
        else:
            # Push apart along connecting axis
            separation_dir = (dl_pos - ol_pos).normalized()

        # How much to separate
        overlap = min_dist - dist

        # Push each player half the overlap distance
        half_push = overlap / 2.0

        ol_new = ol_pos - separation_dir * half_push
        dl_new = dl_pos + separation_dir * half_push

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

    Uses greedy optimal matching: closest pairs matched first,
    regardless of player list order.
    """
    from ..core.entities import Position

    OL_POSITIONS = {Position.LT, Position.LG, Position.C, Position.RG, Position.RT}
    DL_POSITIONS = {Position.DE, Position.DT, Position.NT}

    # Collect all potential OL-DL pairs with distances
    candidates = []
    for ol in offense:
        if ol.position not in OL_POSITIONS:
            continue
        for dl in defense:
            if dl.position not in DL_POSITIONS:
                continue
            dist = ol.pos.distance_to(dl.pos)
            if dist < 5.0:  # Max 5 yards to consider
                candidates.append((dist, ol, dl))

    # Sort by distance (closest first)
    candidates.sort(key=lambda x: x[0])

    # Greedily assign closest matches
    matchups = []
    used_ol = set()
    used_dl = set()

    for dist, ol, dl in candidates:
        if ol.id in used_ol or dl.id in used_dl:
            continue
        matchups.append((ol, dl))
        used_ol.add(ol.id)
        used_dl.add(dl.id)

    return matchups
