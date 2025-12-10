"""Utility AI for QB decision-making.

Replaces threshold-based throw decisions with a weighted multi-factor
scoring system that evaluates each option and selects the best action.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .play_sim import TeamQB, TeamReceiver
    from .team_route_sim import MatchupResult
    from .route_sim import RoutePhase


# =============================================================================
# Constants (Tunable)
# =============================================================================

# Throw thresholds by QB decision_making (lower = more aggressive)
THROW_THRESHOLD_LOW = 50    # Poor decision-making QB (50 rating)
THROW_THRESHOLD_HIGH = 30   # Elite QB (99 rating)

# Variance applied to utility scores
UTILITY_VARIANCE = 4.0      # Gaussian noise stddev (reduced to avoid random early throws)

# Factor weights
SEPARATION_MAX_SCORE = 40   # Maximum points from separation
SEPARATION_CENTER = 2.5     # Sigmoid center (yards)
SEPARATION_SCALE = 1.5      # Sigmoid steepness

# Early throw penalty - provides additional safety against very early throws
# Route phase scores already gate most early throws, this is a backup
MIN_THROW_TICK = 6          # Absolute minimum - no throws before this tick
EARLY_THROW_PENALTY = -15   # Moderate penalty (route phase provides primary gating)

ROUTE_PHASE_SCORES = {
    "pre_snap": -30,        # Strong negative - can't throw pre-snap
    "release": -20,         # Strong negative - receiver just released
    "stem": -8,             # Moderate negative - route still developing
    "break": 25,            # Best time to throw - route breaking open
    "post_break": 20,       # Good - receiver in final phase
    "complete": 8,          # Lower - route done, window may be closing
}

READ_ORDER_PENALTY = -2     # Points per read index
RECEIVER_QUALITY_MAX = 10   # Max points from receiver catching
WINDOW_CLOSING_PENALTY = -15  # Penalty when window is closing
EVALUATION_BONUS_PER_TICK = 1.25  # Points per tick of evaluation

# Hold utility
HOLD_BASE_VALUE = 30        # Base utility of holding the ball
HOLD_TIME_PENALTY = -30     # Max time pressure penalty
HOLD_READS_BONUS = 5        # Points per remaining read


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class UtilityScore:
    """A scored action with its utility value and factor breakdown."""
    action: str                         # "throw" or "hold"
    score: float                        # Total utility score
    factors: dict[str, float] = field(default_factory=dict)  # Factor contributions
    target_id: Optional[str] = None     # Receiver ID for throw actions

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "score": round(self.score, 2),
            "factors": {k: round(v, 2) for k, v in self.factors.items()},
            "target_id": self.target_id,
        }


@dataclass
class ThrowDecision:
    """Result of QB decision-making."""
    should_throw: bool
    target_id: Optional[str] = None
    utility_score: Optional[UtilityScore] = None
    all_scores: list[UtilityScore] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "should_throw": self.should_throw,
            "target_id": self.target_id,
            "utility_score": self.utility_score.to_dict() if self.utility_score else None,
            "all_scores": [s.to_dict() for s in self.all_scores],
        }


# =============================================================================
# Utility Functions
# =============================================================================

def sigmoid(x: float) -> float:
    """Sigmoid function clamped to avoid overflow."""
    x = max(-20, min(20, x))  # Clamp to avoid overflow
    return 1 / (1 + math.exp(-x))


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b."""
    return a + (b - a) * t


# =============================================================================
# Utility Evaluator
# =============================================================================

class UtilityEvaluator:
    """Evaluates utility scores for QB decisions."""

    def __init__(self, variance_enabled: bool = True):
        self.variance_enabled = variance_enabled

    def evaluate_throw(
        self,
        receiver: "TeamReceiver",
        matchup: "MatchupResult",
        qb: "TeamQB",
        tick: int,
        pressure: float,
        read_idx: int,
    ) -> UtilityScore:
        """Calculate utility of throwing to this receiver.

        Args:
            receiver: Target receiver
            matchup: Current matchup result (separation, etc.)
            qb: QB making the decision
            tick: Current simulation tick
            pressure: Pressure level (0-1)
            read_idx: Index of this receiver in read order

        Returns:
            UtilityScore with breakdown of all factors
        """
        factors = {}

        # 1. Separation Factor (0-40 points)
        # Sigmoid curve centered at 2.5 yards
        sep = matchup.separation
        sep_normalized = (sep - SEPARATION_CENTER) / SEPARATION_SCALE
        factors['separation'] = SEPARATION_MAX_SCORE * sigmoid(sep_normalized)

        # 2. Route Phase Factor (0-20 points)
        # Prefer receivers in BREAK or POST_BREAK
        phase_name = receiver.route_phase.value if hasattr(receiver.route_phase, 'value') else str(receiver.route_phase)
        factors['route_phase'] = ROUTE_PHASE_SCORES.get(phase_name, 5)

        # 3. Read Progression Penalty (-10 to 0 points)
        # Later reads get slight penalty (trusted less)
        factors['read_order'] = READ_ORDER_PENALTY * read_idx

        # 4. Pressure Factor (-20 to 0 points)
        # High pressure = more willing to throw (less penalty)
        # pressure=0 -> -20, pressure=1 -> 0
        factors['pressure'] = -20 * (1 - pressure)

        # 5. Receiver Quality Bonus (0-10 points)
        catching = getattr(receiver.attributes, 'catching', 85)
        factors['receiver'] = (catching / 100) * RECEIVER_QUALITY_MAX

        # 6. Window Closing Penalty (-15 to 0)
        # If separation is decreasing significantly, penalize
        if matchup.max_separation > 0:
            sep_ratio = matchup.separation / matchup.max_separation
            if sep_ratio < 0.7:
                factors['window_closing'] = WINDOW_CLOSING_PENALTY
            else:
                factors['window_closing'] = 0
        else:
            factors['window_closing'] = 0

        # 7. Time on Read Bonus (0-5 points)
        # More time evaluating = more confident
        eval_ticks = min(qb.ticks_on_read, 4)
        factors['evaluation'] = eval_ticks * EVALUATION_BONUS_PER_TICK

        # 8. Early Throw Penalty - Backup safety for very early throws
        # Route phase scores provide primary gating; this is a simple floor
        if tick < MIN_THROW_TICK:
            factors['early_throw'] = EARLY_THROW_PENALTY * 2  # Strong penalty before absolute minimum
        elif tick < 10:
            # Small residual penalty that phases out by tick 10
            progress = (tick - MIN_THROW_TICK) / 4
            factors['early_throw'] = EARLY_THROW_PENALTY * (1 - progress)
        else:
            factors['early_throw'] = 0

        total = sum(factors.values())

        return UtilityScore(
            action="throw",
            score=total,
            factors=factors,
            target_id=receiver.id,
        )

    def evaluate_hold(
        self,
        qb: "TeamQB",
        tick: int,
        pressure: float,
    ) -> UtilityScore:
        """Calculate utility of holding the ball / moving to next read.

        Args:
            qb: QB making the decision
            tick: Current simulation tick
            pressure: Pressure level (0-1)

        Returns:
            UtilityScore for holding
        """
        factors = {}

        # Base value of holding
        factors['base'] = HOLD_BASE_VALUE

        # Time pressure (-30 to 0)
        # As tick increases, holding becomes less attractive
        time_factor = min(1.0, tick / 40)
        factors['time'] = HOLD_TIME_PENALTY * time_factor

        # Pressure penalty
        # Under pressure, holding is less attractive
        factors['pressure'] = -20 * pressure

        # Reads remaining bonus
        # More reads left = more reason to hold and look elsewhere
        reads_left = len(qb.read_order) - qb.current_read_idx - 1
        factors['reads_left'] = HOLD_READS_BONUS * max(0, reads_left)

        total = sum(factors.values())

        return UtilityScore(
            action="hold",
            score=total,
            factors=factors,
        )

    def get_throw_threshold(self, qb: "TeamQB") -> float:
        """Get throw threshold based on QB decision_making attribute.

        Higher decision_making = lower threshold = more willing to throw
        to tighter windows.
        """
        dm = qb.attributes.decision_making
        # Linear interpolation from LOW (dm=50) to HIGH (dm=99)
        factor = (dm - 50) / 49
        factor = max(0.0, min(1.0, factor))
        return lerp(THROW_THRESHOLD_LOW, THROW_THRESHOLD_HIGH, factor)

    def make_decision(
        self,
        qb: "TeamQB",
        receivers: list["TeamReceiver"],
        matchups: dict[str, "MatchupResult"],
        tick: int,
        pressure: float,
    ) -> ThrowDecision:
        """Make QB throw/hold decision using utility AI.

        Args:
            qb: QB making the decision
            receivers: All receivers on the field
            matchups: Current matchup results by receiver ID
            tick: Current simulation tick
            pressure: Pressure level (0-1)

        Returns:
            ThrowDecision with selected action and full score breakdown
        """
        all_scores: list[UtilityScore] = []

        # Evaluate throw to each receiver in read order
        for idx, receiver_id in enumerate(qb.read_order):
            receiver = next((r for r in receivers if r.id == receiver_id), None)
            if not receiver:
                continue

            matchup = matchups.get(receiver_id)
            if not matchup:
                continue

            throw_score = self.evaluate_throw(
                receiver=receiver,
                matchup=matchup,
                qb=qb,
                tick=tick,
                pressure=pressure,
                read_idx=idx,
            )

            # Add variance
            if self.variance_enabled:
                throw_score.score += random.gauss(0, UTILITY_VARIANCE)

            all_scores.append(throw_score)

        # Evaluate hold
        hold_score = self.evaluate_hold(qb, tick, pressure)
        if self.variance_enabled:
            hold_score.score += random.gauss(0, UTILITY_VARIANCE)
        all_scores.append(hold_score)

        # Find best throw option
        throw_scores = [s for s in all_scores if s.action == "throw"]
        best_throw = max(throw_scores, key=lambda s: s.score) if throw_scores else None

        # Get threshold for this QB
        threshold = self.get_throw_threshold(qb)

        # Decision: throw if best throw exceeds threshold
        if best_throw and best_throw.score > threshold:
            return ThrowDecision(
                should_throw=True,
                target_id=best_throw.target_id,
                utility_score=best_throw,
                all_scores=all_scores,
            )

        return ThrowDecision(
            should_throw=False,
            target_id=None,
            utility_score=hold_score,
            all_scores=all_scores,
        )
