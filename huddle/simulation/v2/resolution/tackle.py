"""Tackle resolution system.

Handles tackle attempts when defenders contact ballcarriers.
Determines outcomes based on attributes, angles, and physics.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Sequence

from ..core.vec2 import Vec2
from ..core.entities import Player, Team, Position
from ..core.events import EventBus, EventType
from ..core.variance import sigmoid_matchup_probability


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

# Facing direction thresholds
FACING_ANGLE_MAX = 120          # Max angle from facing to attempt tackle (degrees)
                                # 120 = can tackle within 60 degrees of facing direction
                                # Can't tackle someone behind you

# Path blocking (OL wall)
BLOCKER_PROXIMITY_THRESHOLD = 1.5  # OL must be within this distance of path
PATH_BLOCK_TOLERANCE = 0.8         # How close to the direct path OL must be


# =============================================================================
# Helper Functions - Path Blocking and Facing
# =============================================================================

def _is_facing_target(defender: Player, target_pos: Vec2) -> bool:
    """Check if defender is facing toward the target (within FACING_ANGLE_MAX).

    You can't tackle someone behind you - need to be somewhat facing them.

    Args:
        defender: The defensive player
        target_pos: Position of the ballcarrier

    Returns:
        True if defender is facing within the allowed angle
    """
    # Get defender's facing direction
    facing = defender.facing if defender.facing.length() > 0.1 else Vec2(0, -1)

    # Direction from defender to target
    to_target = (target_pos - defender.pos)
    if to_target.length() < 0.1:
        return True  # On top of target, can tackle
    to_target = to_target.normalized()

    # Calculate angle between facing and to_target
    dot = facing.dot(to_target)
    # Clamp to avoid math errors
    dot = max(-1, min(1, dot))
    angle = math.degrees(math.acos(dot))

    return angle <= FACING_ANGLE_MAX


def _is_path_blocked_by_ol(
    defender: Player,
    ballcarrier: Player,
    blockers: Sequence[Player],
) -> bool:
    """Check if there's an OL between the defender and ballcarrier.

    The OL forms a wall - even if not engaged, defenders can't tackle
    through them. This checks if any OL is positioned on the direct
    path between defender and ballcarrier.

    Args:
        defender: The defensive player attempting tackle
        ballcarrier: The player with the ball
        blockers: List of potential blockers (typically offense)

    Returns:
        True if path is blocked, False if clear
    """
    defender_pos = defender.pos
    bc_pos = ballcarrier.pos

    # Vector from defender to ballcarrier
    path_vec = bc_pos - defender_pos
    path_length = path_vec.length()

    if path_length < 0.5:
        return False  # Too close, no room for blocker

    path_dir = path_vec.normalized()

    # Check each potential blocker
    OL_POSITIONS = {Position.LT, Position.LG, Position.C, Position.RG, Position.RT}

    for blocker in blockers:
        # Only OL count as blockers for this purpose
        if blocker.position not in OL_POSITIONS:
            continue

        # Vector from defender to blocker
        to_blocker = blocker.pos - defender_pos

        # Project blocker onto the path
        projection = to_blocker.dot(path_dir)

        # Blocker must be between defender and ballcarrier
        if projection <= 0 or projection >= path_length:
            continue

        # Calculate perpendicular distance from blocker to path
        # Point on path closest to blocker
        closest_on_path = defender_pos + path_dir * projection
        perp_distance = blocker.pos.distance_to(closest_on_path)

        # If blocker is close to the path, they're blocking it
        if perp_distance < PATH_BLOCK_TOLERANCE:
            return True

    return False


# Gang tackle bonuses
GANG_TACKLE_BONUS = 0.15        # Per additional tackler (diminishing)
MAX_GANG_TACKLERS = 4           # Cap on simultaneous tacklers

# Broken tackle outcomes
STUMBLE_SPEED_PENALTY = 0.3     # Speed reduction after breaking tackle
BROKEN_TACKLE_YAC_BOOST = 2.0   # Typical yards gained when breaking

# =============================================================================
# Tackle Engagement Constants
# =============================================================================

# Engagement duration
TACKLE_ENGAGEMENT_MAX_TICKS = 12    # Max ticks before forced resolution (~0.6s)
TACKLE_ENGAGEMENT_MIN_TICKS = 3     # Min ticks of struggle before down

# Fall forward - based on momentum at contact
FALL_FORWARD_BASE = 0.5             # Minimum fall forward (yards)
FALL_FORWARD_PER_SPEED = 0.15       # Extra yards per yard/sec of speed
FALL_FORWARD_MAX = 3.0              # Maximum fall forward yards

# Leverage in tackle engagement (similar to blocking)
# Positive = ballcarrier winning, Negative = tackler winning
TACKLE_LEVERAGE_SHIFT_RATE = 0.15   # How fast leverage shifts per tick
TACKLE_LEVERAGE_TACKLER_BASE = 0.10 # Base advantage to tackler (they made contact)

# Push through thresholds
PUSH_THROUGH_THRESHOLD = 0.6        # Leverage above this = ballcarrier breaks free
BROUGHT_DOWN_THRESHOLD = -0.5       # Leverage below this = ballcarrier going down

# Attribute weights for tackle engagement
BC_STRENGTH_WEIGHT = 0.35           # Ballcarrier strength
BC_ELUSIVENESS_WEIGHT = 0.25        # Breaking tackles
BC_SPEED_WEIGHT = 0.20              # Momentum
BC_BALANCE_WEIGHT = 0.20            # Staying upright (use agility as proxy)

TACKLER_STRENGTH_WEIGHT = 0.35      # Bringing down
TACKLER_TACKLE_WEIGHT = 0.35        # Tackle technique
TACKLER_PURSUIT_WEIGHT = 0.15       # Angle quality
TACKLER_HIT_POWER_WEIGHT = 0.15     # Big hit potential (use strength as proxy)


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


class TackleEngagementOutcome(str, Enum):
    """State of an ongoing tackle engagement."""
    IN_PROGRESS = "in_progress"     # Still fighting
    BROUGHT_DOWN = "brought_down"   # Tackler won, ballcarrier going down
    BROKE_FREE = "broke_free"       # Ballcarrier escaped
    PUSHED_THROUGH = "pushed_through"  # Ballcarrier powered through


@dataclass
class TackleEngagement:
    """Tracks an ongoing tackle engagement (contact made, outcome pending).

    Similar to blocking engagements, but for ballcarrier vs tackler.
    The struggle continues until one side wins.
    """
    ballcarrier_id: str
    primary_tackler_id: str
    assist_tackler_ids: List[str] = field(default_factory=list)

    # Contact point
    contact_position: Vec2 = field(default_factory=lambda: Vec2(0, 0))
    contact_time: float = 0.0

    # Momentum at contact (for fall forward)
    bc_velocity_at_contact: Vec2 = field(default_factory=lambda: Vec2(0, 0))
    bc_speed_at_contact: float = 0.0

    # Tackle type affects leverage
    tackle_type: TackleType = TackleType.STANDARD

    # Leverage: positive = BC winning, negative = tackler winning
    leverage: float = 0.0
    ticks_engaged: int = 0

    # Movement during engagement
    yards_gained_in_engagement: float = 0.0

    def calculate_fall_forward(self) -> float:
        """Calculate fall forward yards based on momentum at contact."""
        # Base fall forward
        fall_forward = FALL_FORWARD_BASE

        # Add momentum-based fall forward
        fall_forward += self.bc_speed_at_contact * FALL_FORWARD_PER_SPEED

        # Cap it
        return min(FALL_FORWARD_MAX, fall_forward)


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
        self._engagements: dict[str, TackleEngagement] = {}  # Key: ballcarrier_id

    def get_engagement(self, ballcarrier_id: str) -> Optional[TackleEngagement]:
        """Get active tackle engagement for a ballcarrier."""
        return self._engagements.get(ballcarrier_id)

    def clear_engagements(self) -> None:
        """Clear all engagements (start of new play)."""
        self._engagements.clear()

    def start_engagement(
        self,
        ballcarrier: Player,
        attempts: List[TackleAttempt],
        time: float,
    ) -> TackleEngagement:
        """Start a tackle engagement when contact is made.

        Args:
            ballcarrier: The ballcarrier
            attempts: Tackle attempts (sorted by quality)
            time: Current game time

        Returns:
            The new TackleEngagement
        """
        primary = attempts[0]
        assists = [a.defender.id for a in attempts[1:MAX_GANG_TACKLERS]]

        # Calculate initial leverage based on tackle type and attributes
        # Tackler starts with slight advantage (they made contact)
        initial_leverage = -TACKLE_LEVERAGE_TACKLER_BASE

        # Tackle type affects starting leverage
        type_modifiers = {
            TackleType.WRAP_UP: -0.15,      # Secure tackle = tackler advantage
            TackleType.STANDARD: -0.05,
            TackleType.HIT_STICK: -0.10,    # Big hit
            TackleType.ARM_TACKLE: 0.15,    # Weak tackle = BC advantage
            TackleType.DIVE: 0.05,          # Risky
            TackleType.SHOESTRING: 0.10,    # Low percentage
        }
        initial_leverage += type_modifiers.get(primary.tackle_type, 0)

        # Gang tackle gives tacklers more advantage
        if assists:
            initial_leverage -= 0.10 * min(len(assists), 2)

        engagement = TackleEngagement(
            ballcarrier_id=ballcarrier.id,
            primary_tackler_id=primary.defender.id,
            assist_tackler_ids=assists,
            contact_position=ballcarrier.pos,
            contact_time=time,
            bc_velocity_at_contact=ballcarrier.velocity,
            bc_speed_at_contact=ballcarrier.velocity.length(),
            tackle_type=primary.tackle_type,
            leverage=initial_leverage,
        )

        self._engagements[ballcarrier.id] = engagement
        return engagement

    def update_engagement(
        self,
        ballcarrier: Player,
        tacklers: List[Player],
        dt: float,
    ) -> Tuple[TackleEngagementOutcome, Optional[TackleResult]]:
        """Update a tackle engagement for one tick.

        Returns:
            (outcome, result) - result is None if still in progress
        """
        engagement = self._engagements.get(ballcarrier.id)
        if not engagement:
            return TackleEngagementOutcome.IN_PROGRESS, None

        engagement.ticks_engaged += 1

        # Get primary tackler
        primary_tackler = None
        for t in tacklers:
            if t.id == engagement.primary_tackler_id:
                primary_tackler = t
                break

        if not primary_tackler:
            # Tackler disappeared? BC breaks free
            del self._engagements[ballcarrier.id]
            return TackleEngagementOutcome.BROKE_FREE, None

        # Calculate leverage shift based on attributes
        leverage_shift = self._calculate_leverage_shift(
            ballcarrier, primary_tackler, engagement
        )

        # Apply leverage shift
        engagement.leverage += leverage_shift

        # Add small random variance
        engagement.leverage += (random.random() - 0.5) * 0.04

        # Clamp leverage
        engagement.leverage = max(-1.0, min(1.0, engagement.leverage))

        # Calculate movement during engagement
        # BC moves in their velocity direction, slowed by tackle
        # Movement rate decreases as tackler wins leverage
        move_rate = 0.3 + (engagement.leverage + 1.0) * 0.2  # 0.1 to 0.7
        move_dist = move_rate * dt * engagement.bc_speed_at_contact * 0.5
        engagement.yards_gained_in_engagement += move_dist

        # Check for resolution
        if engagement.leverage >= PUSH_THROUGH_THRESHOLD:
            # Ballcarrier powered through!
            outcome = TackleEngagementOutcome.PUSHED_THROUGH
            result = self._create_result(
                engagement, ballcarrier, primary_tackler, tacklers,
                TackleOutcome.BROKEN, engagement.yards_gained_in_engagement + 1.0
            )
            del self._engagements[ballcarrier.id]
            return outcome, result

        if engagement.leverage <= BROUGHT_DOWN_THRESHOLD:
            # Tackler brought them down
            # But BC still gets fall forward
            fall_forward = engagement.calculate_fall_forward()
            total_yac = engagement.yards_gained_in_engagement + fall_forward

            # Check for gang tackle
            if len(engagement.assist_tackler_ids) >= 1:
                tackle_outcome = TackleOutcome.GANG_TACKLED
            else:
                tackle_outcome = TackleOutcome.TACKLED

            outcome = TackleEngagementOutcome.BROUGHT_DOWN
            result = self._create_result(
                engagement, ballcarrier, primary_tackler, tacklers,
                tackle_outcome, total_yac
            )
            del self._engagements[ballcarrier.id]
            return outcome, result

        # Check for timeout (too long = BC usually wins)
        if engagement.ticks_engaged >= TACKLE_ENGAGEMENT_MAX_TICKS:
            # Forced resolution - whoever has leverage wins
            if engagement.leverage > 0:
                outcome = TackleEngagementOutcome.BROKE_FREE
                result = self._create_result(
                    engagement, ballcarrier, primary_tackler, tacklers,
                    TackleOutcome.BROKEN, engagement.yards_gained_in_engagement + 0.5
                )
            else:
                fall_forward = engagement.calculate_fall_forward() * 0.5  # Less fall forward on slow tackle
                outcome = TackleEngagementOutcome.BROUGHT_DOWN
                result = self._create_result(
                    engagement, ballcarrier, primary_tackler, tacklers,
                    TackleOutcome.TACKLED, engagement.yards_gained_in_engagement + fall_forward
                )
            del self._engagements[ballcarrier.id]
            return outcome, result

        # Still in progress
        return TackleEngagementOutcome.IN_PROGRESS, None

    def _calculate_leverage_shift(
        self,
        ballcarrier: Player,
        tackler: Player,
        engagement: TackleEngagement,
    ) -> float:
        """Calculate leverage shift for this tick.

        Positive = ballcarrier gaining, Negative = tackler gaining
        """
        # Ballcarrier attributes
        bc_strength = ballcarrier.attributes.strength
        bc_elusiveness = getattr(ballcarrier.attributes, 'elusiveness', 75)
        bc_agility = ballcarrier.attributes.agility
        bc_speed = engagement.bc_speed_at_contact

        bc_score = (
            bc_strength * BC_STRENGTH_WEIGHT +
            bc_elusiveness * BC_ELUSIVENESS_WEIGHT +
            bc_speed * 10 * BC_SPEED_WEIGHT +  # Scale speed to attribute range
            bc_agility * BC_BALANCE_WEIGHT
        )

        # Tackler attributes
        t_strength = tackler.attributes.strength
        t_tackling = tackler.attributes.tackling
        t_pursuit = getattr(tackler.attributes, 'pursuit', 75)

        t_score = (
            t_strength * TACKLER_STRENGTH_WEIGHT +
            t_tackling * TACKLER_TACKLE_WEIGHT +
            t_pursuit * TACKLER_PURSUIT_WEIGHT +
            t_strength * TACKLER_HIT_POWER_WEIGHT  # Use strength as hit power proxy
        )

        # Difference drives leverage shift
        diff = (bc_score - t_score) / 100.0  # Normalize
        shift = diff * TACKLE_LEVERAGE_SHIFT_RATE

        # Gang tackle reduces BC's ability to break free
        if engagement.assist_tackler_ids:
            shift -= 0.02 * len(engagement.assist_tackler_ids)

        # Tackle type affects ongoing struggle
        if engagement.tackle_type == TackleType.ARM_TACKLE:
            shift += 0.03  # Easier to break arm tackle
        elif engagement.tackle_type == TackleType.WRAP_UP:
            shift -= 0.02  # Harder to break wrap-up

        return shift

    def _create_result(
        self,
        engagement: TackleEngagement,
        ballcarrier: Player,
        primary_tackler: Player,
        all_tacklers: List[Player],
        outcome: TackleOutcome,
        yac: float,
    ) -> TackleResult:
        """Create a TackleResult from an engagement."""
        assist_tacklers = [
            t for t in all_tacklers
            if t.id in engagement.assist_tackler_ids
        ]

        return TackleResult(
            outcome=outcome,
            ballcarrier=ballcarrier,
            primary_tackler=primary_tackler,
            assist_tacklers=assist_tacklers,
            probability_was=0.5 - engagement.leverage * 0.3,  # Approximate
            roll=0.0,  # Not used in engagement system
            yards_after_contact=yac,
            fumble=False,
            fumble_recovered_by=None,
            tackle_position=engagement.contact_position,
        )

    def find_tackle_attempts(
        self,
        ballcarrier: Player,
        defenders: List[Player],
        include_diving: bool = True,
        blockers: Optional[Sequence[Player]] = None,
    ) -> List[TackleAttempt]:
        """Find all defenders in position to attempt a tackle.

        Args:
            ballcarrier: Player with the ball
            defenders: List of defensive players
            include_diving: Whether to include diving tackle attempts
            blockers: List of potential blockers (OL) that can block tackle path

        Returns:
            List of TackleAttempt objects for defenders in range
        """
        attempts = []
        blockers = blockers or []

        for defender in defenders:
            if defender.is_down or defender.is_engaged:
                continue

            # Check if defender is facing the ballcarrier
            # Can't tackle someone behind you
            if not _is_facing_target(defender, ballcarrier.pos):
                continue

            # Check if path is blocked by OL
            # Defenders can't tackle through the offensive line
            if blockers and _is_path_blocked_by_ol(defender, ballcarrier, blockers):
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

        # Use sigmoid curve for attribute matchup - provides better differentiation at extremes
        # Tackling vs Elusiveness: the core contest
        tackling = attempt.defender.attributes.tackling
        elusiveness = attempt.ballcarrier.attributes.elusiveness

        # Sigmoid matchup: returns 0.1-0.9 range based on rating difference
        # Elite tackler (95) vs avg runner (75) = ~0.75 success
        # Avg tackler (75) vs elite runner (95) = ~0.25 success
        matchup_prob = sigmoid_matchup_probability(
            tackling, elusiveness,
            base_advantage=0.0,  # Slightly favor defender at catch-up
            steepness=0.06,      # Moderate curve - 20 point diff = ~0.80 prob
            min_prob=0.20,
            max_prob=0.85,
        )
        # Convert to modifier (center at 0.525 which is average probability)
        attribute_mod = (matchup_prob - 0.525) * 0.5  # Scale to -0.15 to +0.15 range
        modifiers["attributes"] = attribute_mod

        # Strength differential - still use linear but capped
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

        # Calculate final (using sigmoid-based attribute_mod instead of linear tackle/elusive mods)
        final = base + dist_mod + attribute_mod + strength_mod + angle_mod + type_mod

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
