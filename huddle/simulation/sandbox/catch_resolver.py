"""Probabilistic Catch Resolver.

Resolves catch outcomes using probability curves based on multiple factors:
- Receiver distance to ball
- Defender distance to ball
- Player attributes (catching, coverage)
- Throw accuracy
- Contest situation
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum
from typing import Optional


# =============================================================================
# Constants (Tunable)
# =============================================================================

# Reach probability curve
REACH_FALLOFF_CENTER = 1.0    # 50% catch probability at this distance (yards)
REACH_FALLOFF_RATE = 0.3      # Steepness of logistic curve

# Contest factors
CONTEST_BASE = 0.58           # Advantage to receiver at equal position (offense wins ties)
CONTEST_SEPARATION_WEIGHT = 0.20  # How much separation affects contest
CONTEST_SKILL_WEIGHT = 0.20   # How much skill difference affects contest

# Interception thresholds
INT_SEPARATION_THRESHOLD = 0.0   # INT possible at equal position or better for defender
INT_BASE_CHANCE = 0.10        # Base INT chance on contested catch
INT_SKILL_FACTOR = 1.2        # How much coverage skill affects INT chance
INT_MIN_CHANCE = 0.03         # Minimum INT chance on any contested catch
INT_MAX_CHANCE = 0.20         # Maximum INT chance

# Uncontested catch
UNCONTESTED_BASE_CATCH = 0.90  # Base catch rate for uncontested balls
UNCONTESTED_SKILL_BONUS = 0.06  # Max bonus from catching skill
UNCONTESTED_ACCURACY_MOD = 0.03  # Max modification from throw accuracy

# Contest range (yards)
CONTESTED_CATCH_RADIUS = 1.8  # Defender within this = contested catch


class CatchResult(str, Enum):
    """Possible catch outcomes."""
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    INTERCEPTION = "interception"


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class CatchContext:
    """All factors affecting catch probability."""
    receiver_dist_to_ball: float    # Yards from receiver to ball target
    defender_dist_to_ball: float    # Yards from closest defender to ball target
    receiver_speed: float           # Receiver current speed
    defender_speed: float           # Defender current speed
    throw_accuracy: float           # How accurate the throw was (0-1, 1 = perfect)
    is_contested: bool              # Is there a defender in catch radius
    receiver_catch_rating: int      # Receiver catching attribute (0-99)
    defender_coverage_rating: int   # Defender coverage attribute (0-99)
    ball_velocity: float            # Ball velocity (yards per tick)
    air_time: int                   # Ticks ball was in air

    def to_dict(self) -> dict:
        return {
            "receiver_dist_to_ball": round(self.receiver_dist_to_ball, 2),
            "defender_dist_to_ball": round(self.defender_dist_to_ball, 2),
            "receiver_speed": round(self.receiver_speed, 2),
            "defender_speed": round(self.defender_speed, 2),
            "throw_accuracy": round(self.throw_accuracy, 2),
            "is_contested": self.is_contested,
            "receiver_catch_rating": self.receiver_catch_rating,
            "defender_coverage_rating": self.defender_coverage_rating,
            "ball_velocity": round(self.ball_velocity, 3),
            "air_time": self.air_time,
        }


@dataclass
class CatchProbabilities:
    """Probability distribution over catch outcomes."""
    complete: float
    incomplete: float
    interception: float

    def to_dict(self) -> dict:
        return {
            "complete": round(self.complete, 4),
            "incomplete": round(self.incomplete, 4),
            "interception": round(self.interception, 4),
        }

    def validate(self) -> bool:
        """Check that probabilities sum to 1."""
        total = self.complete + self.incomplete + self.interception
        return abs(total - 1.0) < 0.0001


@dataclass
class CatchResolution:
    """Result of catch resolution."""
    result: CatchResult
    probability: float              # Probability of this result
    probabilities: CatchProbabilities  # Full distribution
    context: CatchContext           # Input context
    roll: float                     # Random roll that determined outcome

    def to_dict(self) -> dict:
        return {
            "result": self.result.value,
            "probability": round(self.probability, 4),
            "probabilities": self.probabilities.to_dict(),
            "context": self.context.to_dict(),
            "roll": round(self.roll, 4),
        }


# =============================================================================
# Utility Functions
# =============================================================================

def logistic(x: float, center: float = 0, rate: float = 1) -> float:
    """Logistic function for probability curves.

    Returns value between 0 and 1.
    At x=center, returns 0.5.
    Higher rate = steeper transition.
    """
    z = (x - center) / rate
    z = max(-20, min(20, z))  # Clamp to avoid overflow
    return 1 / (1 + math.exp(z))


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max."""
    return max(min_val, min(max_val, value))


# =============================================================================
# Catch Resolver
# =============================================================================

class CatchResolver:
    """Resolves catch outcomes using probability curves."""

    def __init__(self, variance_enabled: bool = True):
        self.variance_enabled = variance_enabled

    def calculate_probabilities(self, ctx: CatchContext) -> CatchProbabilities:
        """Calculate probability distribution over catch outcomes.

        Args:
            ctx: Context with all relevant factors

        Returns:
            CatchProbabilities with complete, incomplete, interception rates
        """
        # 1. Base reach probability (can receiver reach the ball?)
        # Logistic curve: high at 0 yards, drops off around 1 yard
        reach_prob = logistic(
            ctx.receiver_dist_to_ball,
            center=REACH_FALLOFF_CENTER,
            rate=REACH_FALLOFF_RATE,
        )

        # Ball completely uncatchable
        if reach_prob < 0.1:
            return CatchProbabilities(
                complete=0.0,
                incomplete=1.0,
                interception=0.0,
            )

        # 2. Contested or uncontested?
        if ctx.is_contested:
            return self._calculate_contested_probabilities(ctx, reach_prob)
        else:
            return self._calculate_uncontested_probabilities(ctx, reach_prob)

    def _calculate_contested_probabilities(
        self, ctx: CatchContext, reach_prob: float
    ) -> CatchProbabilities:
        """Calculate probabilities for contested catch."""
        # Separation advantage: positive = receiver closer (good)
        separation = ctx.defender_dist_to_ball - ctx.receiver_dist_to_ball

        # Skill battle
        catch_skill = ctx.receiver_catch_rating / 100
        cover_skill = ctx.defender_coverage_rating / 100

        # Contest factor (chance receiver wins the battle)
        # Base 50/50, adjusted by separation and skills
        contest_factor = (
            CONTEST_BASE
            + separation * CONTEST_SEPARATION_WEIGHT
            + (catch_skill - cover_skill) * CONTEST_SKILL_WEIGHT
        )
        contest_factor = clamp(contest_factor, 0.1, 0.9)

        # Interception chance (only if defender has position)
        if separation < INT_SEPARATION_THRESHOLD:
            # Defender has better position - INT possible
            int_chance = INT_BASE_CHANCE * (1 + (cover_skill - 0.7) * INT_SKILL_FACTOR)
            int_chance = clamp(int_chance, INT_MIN_CHANCE, INT_MAX_CHANCE)

            # Worse separation = higher INT chance
            separation_penalty = abs(separation + INT_SEPARATION_THRESHOLD) * 0.1
            int_chance = clamp(int_chance + separation_penalty, INT_MIN_CHANCE, INT_MAX_CHANCE)
        else:
            # Receiver has position - minimal INT chance
            int_chance = INT_MIN_CHANCE

        # Calculate final probabilities
        complete_prob = reach_prob * contest_factor * (1 - int_chance)
        interception_prob = reach_prob * (1 - contest_factor) * int_chance

        # Incomplete is the remainder
        incomplete_prob = 1 - complete_prob - interception_prob

        # Ensure probabilities are valid
        complete_prob = clamp(complete_prob, 0, 1)
        interception_prob = clamp(interception_prob, 0, 1)
        incomplete_prob = clamp(incomplete_prob, 0, 1)

        # Normalize if needed
        total = complete_prob + incomplete_prob + interception_prob
        if total > 0:
            complete_prob /= total
            incomplete_prob /= total
            interception_prob /= total

        return CatchProbabilities(
            complete=complete_prob,
            incomplete=incomplete_prob,
            interception=interception_prob,
        )

    def _calculate_uncontested_probabilities(
        self, ctx: CatchContext, reach_prob: float
    ) -> CatchProbabilities:
        """Calculate probabilities for uncontested catch."""
        # Base catch rate affected by receiver skill
        catch_skill = ctx.receiver_catch_rating / 100
        base_catch = UNCONTESTED_BASE_CATCH + catch_skill * UNCONTESTED_SKILL_BONUS

        # Accuracy modification
        accuracy_mod = (ctx.throw_accuracy - 0.5) * 2 * UNCONTESTED_ACCURACY_MOD
        base_catch += accuracy_mod

        # Apply reach probability
        complete_prob = clamp(reach_prob * base_catch, 0, 0.98)
        incomplete_prob = 1 - complete_prob

        return CatchProbabilities(
            complete=complete_prob,
            incomplete=incomplete_prob,
            interception=0.0,  # No INT on uncontested catch
        )

    def resolve(self, ctx: CatchContext) -> CatchResolution:
        """Resolve catch outcome by rolling against probabilities.

        Args:
            ctx: Context with all relevant factors

        Returns:
            CatchResolution with result and probability info
        """
        probs = self.calculate_probabilities(ctx)

        # Roll random number
        roll = random.random() if self.variance_enabled else 0.5

        # Determine outcome
        if roll < probs.complete:
            result = CatchResult.COMPLETE
            probability = probs.complete
        elif roll < probs.complete + probs.incomplete:
            result = CatchResult.INCOMPLETE
            probability = probs.incomplete
        else:
            result = CatchResult.INTERCEPTION
            probability = probs.interception

        return CatchResolution(
            result=result,
            probability=probability,
            probabilities=probs,
            context=ctx,
            roll=roll,
        )


# =============================================================================
# Context Builder
# =============================================================================

def build_catch_context(
    receiver_position: tuple[float, float],
    defender_position: tuple[float, float],
    ball_target: tuple[float, float],
    receiver_speed: float,
    defender_speed: float,
    receiver_catch_rating: int,
    defender_coverage_rating: int,
    throw_accuracy: float,
    ball_velocity: float,
    air_time: int,
) -> CatchContext:
    """Build CatchContext from game state.

    Args:
        receiver_position: (x, y) of receiver
        defender_position: (x, y) of closest defender
        ball_target: (x, y) where ball will land
        receiver_speed: Receiver's current speed
        defender_speed: Defender's current speed
        receiver_catch_rating: Receiver's catching attribute
        defender_coverage_rating: Defender's coverage attribute
        throw_accuracy: How accurate the throw was (0-1)
        ball_velocity: Ball velocity in yards per tick
        air_time: Ticks ball was in air

    Returns:
        CatchContext ready for resolution
    """
    # Calculate distances
    rx, ry = receiver_position
    dx, dy = defender_position
    bx, by = ball_target

    receiver_dist = math.sqrt((rx - bx) ** 2 + (ry - by) ** 2)
    defender_dist = math.sqrt((dx - bx) ** 2 + (dy - by) ** 2)

    # Check if contested
    is_contested = defender_dist < CONTESTED_CATCH_RADIUS

    return CatchContext(
        receiver_dist_to_ball=receiver_dist,
        defender_dist_to_ball=defender_dist,
        receiver_speed=receiver_speed,
        defender_speed=defender_speed,
        throw_accuracy=throw_accuracy,
        is_contested=is_contested,
        receiver_catch_rating=receiver_catch_rating,
        defender_coverage_rating=defender_coverage_rating,
        ball_velocity=ball_velocity,
        air_time=air_time,
    )
