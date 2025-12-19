"""Tackle resolution system.

Handles tackle attempts when defenders contact ballcarriers.
Determines outcomes based on attributes, angles, and physics.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from ..core.vec2 import Vec2
from ..core.entities import Player, Team
from ..core.events import EventBus, EventType


# =============================================================================
# Constants
# =============================================================================

# Distance thresholds (yards)
TACKLE_ATTEMPT_RANGE = 1.5      # Can attempt tackle within this range
SURE_TACKLE_RANGE = 0.5         # Very close = high success rate
DIVE_TACKLE_RANGE = 2.5         # Can dive tackle from further

# Base probabilities
BASE_TACKLE_PROBABILITY = 0.70  # Starting point before modifiers
SURE_TACKLE_BONUS = 0.25        # Bonus when very close
DIVE_TACKLE_PENALTY = 0.20      # Penalty for diving tackles

# Attribute weights
TACKLING_WEIGHT = 0.35          # Defender tackling attribute
ELUSIVENESS_WEIGHT = 0.25       # Ballcarrier elusiveness
STRENGTH_DIFF_WEIGHT = 0.15     # Strength difference
ANGLE_WEIGHT = 0.15             # Approach angle quality
SPEED_WEIGHT = 0.10             # Speed at contact

# Angle thresholds (degrees)
HEAD_ON_ANGLE = 30              # Direct approach
GOOD_ANGLE = 60                 # Solid angle
CHASE_ANGLE = 120               # Pursuit from behind

# Gang tackle bonuses
GANG_TACKLE_BONUS = 0.15        # Per additional tackler (diminishing)
MAX_GANG_TACKLERS = 4           # Cap on simultaneous tacklers

# Broken tackle outcomes
STUMBLE_SPEED_PENALTY = 0.3     # Speed reduction after breaking tackle
BROKEN_TACKLE_YAC_BOOST = 2.0   # Typical yards gained when breaking


# =============================================================================
# Data Structures
# =============================================================================

class TackleType(str, Enum):
    """Type of tackle attempt."""
    STANDARD = "standard"       # Normal wrap-up tackle
    DIVE = "dive"               # Diving/lunging tackle
    ARM_TACKLE = "arm_tackle"   # Arm-only, high miss rate
    HIT_STICK = "hit_stick"     # Big hit, high risk/reward
    WRAP_UP = "wrap_up"         # Secure fundamentals
    SHOESTRING = "shoestring"   # Low diving at feet


class TackleOutcome(str, Enum):
    """Result of a tackle attempt."""
    TACKLED = "tackled"           # Ballcarrier down
    BROKEN = "broken"             # Ballcarrier escaped
    STUMBLE = "stumble"           # Ballcarrier stumbled but stayed up
    MISSED = "missed"             # Complete whiff
    GANG_TACKLED = "gang_tackled" # Multiple defenders
    FUMBLE = "fumble"             # Ball came loose


@dataclass
class TackleAttempt:
    """A single tackle attempt by one defender."""
    defender: Player
    ballcarrier: Player
    tackle_type: TackleType
    distance: float             # Distance at attempt
    approach_angle: float       # Angle of approach (0 = head on)
    closing_speed: float        # Combined speed at contact

    # Calculated
    base_probability: float = 0.0
    final_probability: float = 0.0
    modifiers: dict = field(default_factory=dict)


@dataclass
class TackleResult:
    """Result of tackle resolution."""
    outcome: TackleOutcome
    ballcarrier: Player
    primary_tackler: Optional[Player]
    assist_tacklers: List[Player]

    # Details
    probability_was: float      # What the success probability was
    roll: float                 # What was rolled (for debugging)
    yards_after_contact: float  # YAC gained/lost during tackle
    fumble: bool = False
    fumble_recovered_by: Optional[str] = None

    # Position info
    tackle_position: Optional[Vec2] = None

    def format_description(self) -> str:
        """Human-readable description."""
        if self.outcome == TackleOutcome.TACKLED:
            if self.primary_tackler:
                return f"Tackled by {self.primary_tackler.name}"
            return "Tackled"
        elif self.outcome == TackleOutcome.GANG_TACKLED:
            names = [self.primary_tackler.name] if self.primary_tackler else []
            names += [t.name for t in self.assist_tacklers[:2]]
            return f"Gang tackled by {', '.join(names)}"
        elif self.outcome == TackleOutcome.BROKEN:
            return f"Broke tackle from {self.primary_tackler.name if self.primary_tackler else 'defender'}"
        elif self.outcome == TackleOutcome.MISSED:
            return f"Missed tackle by {self.primary_tackler.name if self.primary_tackler else 'defender'}"
        elif self.outcome == TackleOutcome.FUMBLE:
            return f"Fumble! Forced by {self.primary_tackler.name if self.primary_tackler else 'defender'}"
        return str(self.outcome.value)


# =============================================================================
# Tackle Resolver
# =============================================================================

class TackleResolver:
    """Resolves tackle attempts between defenders and ballcarriers.

    Usage:
        resolver = TackleResolver(event_bus)

        # Check for tackle opportunities each tick
        attempts = resolver.find_tackle_attempts(ballcarrier, defenders)

        if attempts:
            result = resolver.resolve(attempts)
            if result.outcome in (TackleOutcome.TACKLED, TackleOutcome.GANG_TACKLED):
                # Play is over
                pass
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    def find_tackle_attempts(
        self,
        ballcarrier: Player,
        defenders: List[Player],
        include_diving: bool = True,
    ) -> List[TackleAttempt]:
        """Find all defenders in position to attempt a tackle.

        Args:
            ballcarrier: Player with the ball
            defenders: List of defensive players
            include_diving: Whether to include diving tackle attempts

        Returns:
            List of TackleAttempt objects for defenders in range
        """
        attempts = []

        for defender in defenders:
            if defender.is_down or defender.is_engaged:
                continue

            distance = ballcarrier.pos.distance_to(defender.pos)

            # Check if in range for any tackle type
            max_range = DIVE_TACKLE_RANGE if include_diving else TACKLE_ATTEMPT_RANGE
            if distance > max_range:
                continue

            # Calculate approach angle
            # 0 = head on, 90 = side, 180 = from behind
            to_ballcarrier = (ballcarrier.pos - defender.pos).normalized()
            bc_direction = ballcarrier.velocity.normalized() if ballcarrier.velocity.length() > 0.1 else ballcarrier.facing

            # Dot product gives cos of angle
            dot = to_ballcarrier.dot(bc_direction)
            approach_angle = math.degrees(math.acos(max(-1, min(1, -dot))))  # Negate because we want angle relative to BC direction

            # Calculate closing speed
            defender_speed = defender.velocity.length()
            bc_speed = ballcarrier.velocity.length()
            # Closing speed is relative velocity component toward each other
            relative_vel = defender.velocity - ballcarrier.velocity
            closing_speed = max(0, relative_vel.dot(to_ballcarrier))

            # Determine tackle type
            tackle_type = self._select_tackle_type(distance, approach_angle, defender)

            # Skip if diving tackle and not included
            if tackle_type == TackleType.DIVE and not include_diving:
                continue

            attempt = TackleAttempt(
                defender=defender,
                ballcarrier=ballcarrier,
                tackle_type=tackle_type,
                distance=distance,
                approach_angle=approach_angle,
                closing_speed=closing_speed,
            )

            # Calculate probability
            attempt.base_probability, attempt.final_probability, attempt.modifiers = \
                self._calculate_probability(attempt)

            attempts.append(attempt)

        # Sort by probability (best attempts first)
        attempts.sort(key=lambda a: a.final_probability, reverse=True)

        return attempts

    def _select_tackle_type(
        self,
        distance: float,
        approach_angle: float,
        defender: Player,
    ) -> TackleType:
        """Select the type of tackle based on situation."""
        # Very close = wrap up
        if distance < SURE_TACKLE_RANGE:
            return TackleType.WRAP_UP

        # Need to dive if too far
        if distance > TACKLE_ATTEMPT_RANGE:
            if approach_angle < 45:
                return TackleType.DIVE
            else:
                return TackleType.SHOESTRING

        # From behind = arm tackle likely
        if approach_angle > CHASE_ANGLE:
            return TackleType.ARM_TACKLE

        # Head on with good tackling = hit stick opportunity
        if approach_angle < HEAD_ON_ANGLE and defender.attributes.tackling >= 80:
            # High tackling + head on = can go for big hit
            if random.random() < 0.3:  # 30% chance to try hit stick
                return TackleType.HIT_STICK

        return TackleType.STANDARD

    def _calculate_probability(
        self,
        attempt: TackleAttempt,
    ) -> Tuple[float, float, dict]:
        """Calculate tackle success probability.

        Returns:
            (base_probability, final_probability, modifiers_dict)
        """
        modifiers = {}

        # Start with base
        base = BASE_TACKLE_PROBABILITY

        # Distance modifier
        if attempt.distance < SURE_TACKLE_RANGE:
            dist_mod = SURE_TACKLE_BONUS
            modifiers["close_range"] = dist_mod
        elif attempt.distance > TACKLE_ATTEMPT_RANGE:
            # Diving tackle penalty
            dist_mod = -DIVE_TACKLE_PENALTY
            modifiers["diving"] = dist_mod
        else:
            # Linear falloff in normal range
            dist_mod = SURE_TACKLE_BONUS * (1 - (attempt.distance - SURE_TACKLE_RANGE) /
                                            (TACKLE_ATTEMPT_RANGE - SURE_TACKLE_RANGE))
            modifiers["distance"] = dist_mod

        # Tackling attribute (0-99 scale -> -0.15 to +0.20)
        tackling = attempt.defender.attributes.tackling
        tackle_mod = (tackling - 75) / 100 * TACKLING_WEIGHT
        modifiers["tackling"] = tackle_mod

        # Elusiveness attribute (higher = harder to tackle)
        elusiveness = attempt.ballcarrier.attributes.elusiveness
        elusive_mod = -(elusiveness - 75) / 100 * ELUSIVENESS_WEIGHT
        modifiers["elusiveness"] = elusive_mod

        # Strength differential
        strength_diff = attempt.defender.attributes.strength - attempt.ballcarrier.attributes.strength
        strength_mod = (strength_diff / 50) * STRENGTH_DIFF_WEIGHT
        strength_mod = max(-0.15, min(0.15, strength_mod))  # Cap
        modifiers["strength"] = strength_mod

        # Approach angle (head on is better)
        if attempt.approach_angle < HEAD_ON_ANGLE:
            angle_mod = ANGLE_WEIGHT  # Best angle
        elif attempt.approach_angle < GOOD_ANGLE:
            angle_mod = ANGLE_WEIGHT * 0.5  # Good angle
        elif attempt.approach_angle < CHASE_ANGLE:
            angle_mod = 0  # Neutral
        else:
            angle_mod = -ANGLE_WEIGHT  # Chasing from behind
        modifiers["angle"] = angle_mod

        # Tackle type modifiers
        type_mods = {
            TackleType.WRAP_UP: 0.10,     # Fundamentally sound
            TackleType.STANDARD: 0.0,
            TackleType.HIT_STICK: -0.05,  # Risky but rewards
            TackleType.DIVE: -0.15,       # Desperation
            TackleType.ARM_TACKLE: -0.20, # Weak
            TackleType.SHOESTRING: -0.25, # Low percentage
        }
        type_mod = type_mods.get(attempt.tackle_type, 0)
        modifiers["tackle_type"] = type_mod

        # Calculate final
        final = base + dist_mod + tackle_mod + elusive_mod + strength_mod + angle_mod + type_mod

        # Clamp to reasonable range
        final = max(0.10, min(0.98, final))

        return base, final, modifiers

    def resolve(
        self,
        attempts: List[TackleAttempt],
        tick: int = 0,
        time: float = 0.0,
    ) -> TackleResult:
        """Resolve tackle attempts.

        If multiple defenders are attempting, resolves as gang tackle
        with increased probability.

        Args:
            attempts: List of tackle attempts (should be sorted by probability)
            tick: Current tick for events
            time: Current time for events

        Returns:
            TackleResult with outcome
        """
        if not attempts:
            raise ValueError("No tackle attempts to resolve")

        ballcarrier = attempts[0].ballcarrier
        primary = attempts[0]
        assists = attempts[1:MAX_GANG_TACKLERS]

        # Calculate combined probability for gang tackle
        combined_prob = primary.final_probability

        for i, assist in enumerate(assists):
            # Diminishing returns for additional tacklers
            bonus = GANG_TACKLE_BONUS * (0.7 ** i)  # 0.15, 0.105, 0.07...
            combined_prob += bonus * assist.final_probability

        combined_prob = min(0.98, combined_prob)

        # Roll the dice
        roll = random.random()

        # Determine outcome
        if roll < combined_prob:
            # Tackle successful
            if len(assists) >= 1:
                outcome = TackleOutcome.GANG_TACKLED
            else:
                outcome = TackleOutcome.TACKLED

            # Check for fumble (rare)
            fumble = False
            fumble_recovered_by = None
            if primary.tackle_type == TackleType.HIT_STICK:
                fumble_chance = 0.08  # Hit sticks cause more fumbles
            else:
                fumble_chance = 0.02  # Base fumble rate

            # Modify by ball security (awareness as proxy)
            fumble_chance *= (100 - ballcarrier.attributes.awareness) / 100

            if random.random() < fumble_chance:
                fumble = True
                outcome = TackleOutcome.FUMBLE
                # 50/50 on recovery for now (simplified)
                fumble_recovered_by = primary.defender.id if random.random() < 0.5 else ballcarrier.id

            yac = 0.0  # Stopped at point of contact

        else:
            # Tackle failed
            margin = roll - combined_prob

            if margin > 0.20:
                # Clean miss
                outcome = TackleOutcome.MISSED
                yac = BROKEN_TACKLE_YAC_BOOST * 1.5
            elif margin > 0.10:
                # Broken cleanly
                outcome = TackleOutcome.BROKEN
                yac = BROKEN_TACKLE_YAC_BOOST
            else:
                # Stumbled but stayed up
                outcome = TackleOutcome.STUMBLE
                yac = BROKEN_TACKLE_YAC_BOOST * 0.5

            fumble = False
            fumble_recovered_by = None

        result = TackleResult(
            outcome=outcome,
            ballcarrier=ballcarrier,
            primary_tackler=primary.defender,
            assist_tacklers=[a.defender for a in assists],
            probability_was=combined_prob,
            roll=roll,
            yards_after_contact=yac,
            fumble=fumble,
            fumble_recovered_by=fumble_recovered_by,
            tackle_position=ballcarrier.pos,
        )

        # Emit events
        self._emit_events(result, tick, time)

        return result

    def _emit_events(self, result: TackleResult, tick: int, time: float) -> None:
        """Emit events for tackle resolution."""

        if result.outcome in (TackleOutcome.TACKLED, TackleOutcome.GANG_TACKLED):
            self.event_bus.emit_simple(
                EventType.TACKLE,
                tick,
                time,
                player_id=result.primary_tackler.id if result.primary_tackler else None,
                target_id=result.ballcarrier.id,
                description=result.format_description(),
                position=(result.tackle_position.x, result.tackle_position.y) if result.tackle_position else None,
                probability=result.probability_was,
            )

        elif result.outcome == TackleOutcome.MISSED:
            self.event_bus.emit_simple(
                EventType.MISSED_TACKLE,
                tick,
                time,
                player_id=result.primary_tackler.id if result.primary_tackler else None,
                target_id=result.ballcarrier.id,
                description=result.format_description(),
            )

        elif result.outcome in (TackleOutcome.BROKEN, TackleOutcome.STUMBLE):
            self.event_bus.emit_simple(
                EventType.MISSED_TACKLE,
                tick,
                time,
                player_id=result.primary_tackler.id if result.primary_tackler else None,
                target_id=result.ballcarrier.id,
                description=result.format_description(),
                broken=True,
            )

        if result.fumble:
            self.event_bus.emit_simple(
                EventType.FUMBLE,
                tick,
                time,
                player_id=result.ballcarrier.id,
                description=f"Fumble! Recovered by {result.fumble_recovered_by}",
                recovered_by=result.fumble_recovered_by,
            )


# =============================================================================
# Convenience Functions
# =============================================================================

def check_tackle_opportunity(
    ballcarrier: Player,
    defender: Player,
) -> bool:
    """Quick check if defender can attempt tackle.

    Use this before calling find_tackle_attempts for single defender checks.
    """
    if defender.is_down or defender.is_engaged:
        return False

    distance = ballcarrier.pos.distance_to(defender.pos)
    return distance <= DIVE_TACKLE_RANGE


def calculate_tackle_probability(
    ballcarrier: Player,
    defender: Player,
) -> float:
    """Quick probability calculation without full TackleAttempt.

    Useful for AI decision-making (should I pursue this guy?).
    """
    distance = ballcarrier.pos.distance_to(defender.pos)

    if distance > DIVE_TACKLE_RANGE:
        return 0.0

    # Simplified calculation
    base = BASE_TACKLE_PROBABILITY

    # Distance
    if distance < SURE_TACKLE_RANGE:
        base += SURE_TACKLE_BONUS
    elif distance > TACKLE_ATTEMPT_RANGE:
        base -= DIVE_TACKLE_PENALTY

    # Attributes
    tackle_mod = (defender.attributes.tackling - 75) / 100 * TACKLING_WEIGHT
    elusive_mod = -(ballcarrier.attributes.elusiveness - 75) / 100 * ELUSIVENESS_WEIGHT

    return max(0.1, min(0.95, base + tackle_mod + elusive_mod))
