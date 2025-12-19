"""Move Resolver - Resolves ballcarrier evasion moves.

Handles juke, spin, truck, stiff arm, hurdle, and other evasive moves.
Determines success/failure based on ballcarrier vs defender attributes.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, TYPE_CHECKING

from ..core.vec2 import Vec2
from ..core.events import EventBus, EventType

if TYPE_CHECKING:
    from ..core.entities import Player


class MoveType(str, Enum):
    """Types of evasion moves."""
    JUKE = "juke"           # Lateral direction change
    SPIN = "spin"           # 360 spin move
    TRUCK = "truck"         # Lower shoulder through contact
    STIFF_ARM = "stiff_arm" # Extend arm to ward off tackler
    HURDLE = "hurdle"       # Jump over diving tackler
    DEAD_LEG = "dead_leg"   # Subtle hesitation
    CUT = "cut"             # Sharp direction change
    SPEED_BURST = "speed_burst"  # Acceleration burst


class MoveOutcome(str, Enum):
    """Outcome of a move attempt."""
    SUCCESS = "success"       # Broke free, full speed maintained
    PARTIAL = "partial"       # Avoided tackle but lost momentum
    FAILED = "failed"         # Tackled/wrapped up
    FUMBLE = "fumble"         # Lost the ball


@dataclass
class MoveAttempt:
    """A move attempt by a ballcarrier."""
    ballcarrier_id: str
    defender_id: str
    move_type: MoveType
    distance: float           # Distance to defender at attempt
    ballcarrier_speed: float  # Speed at attempt
    defender_closing: float   # Defender's closing speed


@dataclass
class MoveResult:
    """Result of a move resolution."""
    outcome: MoveOutcome

    # Speed effects
    speed_retained: float = 1.0  # Multiplier (1.0 = full speed, 0.7 = slowed)

    # Direction effects (for jukes/cuts)
    new_direction: Optional[Vec2] = None

    # Animation/timing
    recovery_time: float = 0.0  # Time before full control restored

    # Fumble info
    fumble_pos: Optional[Vec2] = None

    # Debug
    probability: float = 0.0
    reasoning: str = ""


class MoveResolver:
    """Resolves ballcarrier evasion moves against defenders.

    Uses attribute-based probability with situational modifiers.
    """

    # Base success rates by move type (at equal attributes)
    BASE_SUCCESS_RATES = {
        MoveType.JUKE: 0.50,
        MoveType.SPIN: 0.45,
        MoveType.TRUCK: 0.40,
        MoveType.STIFF_ARM: 0.55,
        MoveType.HURDLE: 0.35,
        MoveType.DEAD_LEG: 0.60,
        MoveType.CUT: 0.55,
        MoveType.SPEED_BURST: 0.50,
    }

    # Key attributes by move type
    MOVE_ATTRIBUTES = {
        MoveType.JUKE: ("agility", "tackle"),       # BC agility vs DEF tackle
        MoveType.SPIN: ("agility", "tackle"),
        MoveType.TRUCK: ("strength", "tackle"),     # BC strength vs DEF tackle
        MoveType.STIFF_ARM: ("strength", "pursuit"),
        MoveType.HURDLE: ("agility", "pursuit"),
        MoveType.DEAD_LEG: ("agility", "play_recognition"),
        MoveType.CUT: ("agility", "pursuit"),
        MoveType.SPEED_BURST: ("speed", "speed"),   # Speed vs speed
    }

    # Optimal distances for each move
    OPTIMAL_DISTANCE = {
        MoveType.JUKE: (1.5, 3.0),      # Best at 1.5-3 yards
        MoveType.SPIN: (0.5, 1.5),      # Best at close range
        MoveType.TRUCK: (0.5, 1.5),     # Contact move
        MoveType.STIFF_ARM: (1.0, 2.5),
        MoveType.HURDLE: (1.0, 2.0),
        MoveType.DEAD_LEG: (2.0, 4.0),  # Subtle move needs space
        MoveType.CUT: (2.0, 4.0),
        MoveType.SPEED_BURST: (2.0, 5.0),
    }

    # Fumble risk by move type
    FUMBLE_RISK = {
        MoveType.JUKE: 0.02,
        MoveType.SPIN: 0.04,      # Spinning = higher risk
        MoveType.TRUCK: 0.05,     # Contact = highest risk
        MoveType.STIFF_ARM: 0.03,
        MoveType.HURDLE: 0.06,    # Risky move
        MoveType.DEAD_LEG: 0.01,
        MoveType.CUT: 0.02,
        MoveType.SPEED_BURST: 0.01,
    }

    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus

    def create_attempt(
        self,
        ballcarrier: Player,
        defender: Player,
        move_type: str,
    ) -> MoveAttempt:
        """Create a move attempt from current game state."""
        distance = ballcarrier.pos.distance_to(defender.pos)

        # Calculate closing speed
        to_bc = (ballcarrier.pos - defender.pos).normalized()
        closing = defender.velocity.dot(to_bc) if defender.velocity.length() > 0.1 else 0

        return MoveAttempt(
            ballcarrier_id=ballcarrier.id,
            defender_id=defender.id,
            move_type=MoveType(move_type) if isinstance(move_type, str) else move_type,
            distance=distance,
            ballcarrier_speed=ballcarrier.velocity.length(),
            defender_closing=closing,
        )

    def resolve(
        self,
        attempt: MoveAttempt,
        ballcarrier: Player,
        defender: Player,
        tick: int,
        time: float,
    ) -> MoveResult:
        """Resolve a move attempt.

        Args:
            attempt: The move attempt details
            ballcarrier: Ballcarrier player
            defender: Defending player
            tick: Current tick
            time: Current game time

        Returns:
            MoveResult with outcome and effects
        """
        move_type = attempt.move_type

        # Calculate base probability
        probability = self._calculate_probability(attempt, ballcarrier, defender)

        # Roll the dice
        roll = random.random()

        # Build reasoning
        reasoning_parts = [f"{move_type.value} attempt at {attempt.distance:.1f}yd"]

        if roll < probability:
            # Success!
            outcome = MoveOutcome.SUCCESS
            speed_retained = self._get_success_speed(move_type)
            new_direction = self._get_success_direction(move_type, ballcarrier, defender)
            recovery_time = 0.1  # Brief recovery
            reasoning_parts.append(f"SUCCESS ({probability:.0%} prob)")

            self._emit_event(
                EventType.MOVE_SUCCESS,
                ballcarrier.id,
                f"{ballcarrier.name} breaks tackle with {move_type.value}!",
                tick, time,
                {"defender_id": defender.id, "move": move_type.value},
            )

        elif roll < probability + 0.25:
            # Partial - avoided but slowed
            outcome = MoveOutcome.PARTIAL
            speed_retained = 0.6  # Significant slowdown
            new_direction = None
            recovery_time = 0.25  # Longer recovery
            reasoning_parts.append(f"PARTIAL - slowed ({probability:.0%} prob)")

        else:
            # Failed - tackled or wrapped
            outcome = MoveOutcome.FAILED
            speed_retained = 0.0
            new_direction = None
            recovery_time = 0.0
            reasoning_parts.append(f"FAILED ({probability:.0%} prob)")

        # Check for fumble on contact moves
        fumble_pos = None
        if outcome != MoveOutcome.SUCCESS and move_type in (MoveType.TRUCK, MoveType.HURDLE):
            fumble_chance = self.FUMBLE_RISK[move_type]
            # Ball security reduces fumble chance
            carry_rating = getattr(ballcarrier.attributes, 'carrying', 80)
            fumble_chance *= (100 - carry_rating) / 50  # Higher carry = lower fumble

            if random.random() < fumble_chance:
                outcome = MoveOutcome.FUMBLE
                fumble_pos = ballcarrier.pos
                reasoning_parts.append("FUMBLE!")

                self._emit_event(
                    EventType.FUMBLE,
                    ballcarrier.id,
                    f"{ballcarrier.name} fumbles!",
                    tick, time,
                    {"caused_by": defender.id, "move": move_type.value},
                )

        return MoveResult(
            outcome=outcome,
            speed_retained=speed_retained,
            new_direction=new_direction,
            recovery_time=recovery_time,
            fumble_pos=fumble_pos,
            probability=probability,
            reasoning=" | ".join(reasoning_parts),
        )

    def _calculate_probability(
        self,
        attempt: MoveAttempt,
        ballcarrier: Player,
        defender: Player,
    ) -> float:
        """Calculate probability of move success."""
        move_type = attempt.move_type

        # Base rate
        prob = self.BASE_SUCCESS_RATES.get(move_type, 0.5)

        # Get relevant attributes
        bc_attr_name, def_attr_name = self.MOVE_ATTRIBUTES.get(move_type, ("agility", "tackle"))
        bc_attr = getattr(ballcarrier.attributes, bc_attr_name, 75)
        def_attr = getattr(defender.attributes, def_attr_name, 75)

        # Attribute differential
        # +10 attribute advantage = +15% success
        attr_diff = (bc_attr - def_attr) / 10 * 0.15
        prob += attr_diff

        # Distance modifier
        optimal_min, optimal_max = self.OPTIMAL_DISTANCE.get(move_type, (1.5, 3.0))
        if attempt.distance < optimal_min:
            # Too close - less time to execute
            prob -= (optimal_min - attempt.distance) * 0.1
        elif attempt.distance > optimal_max:
            # Too far - defender can adjust
            prob -= (attempt.distance - optimal_max) * 0.05

        # Speed advantage
        if attempt.ballcarrier_speed > 0:
            speed_factor = attempt.ballcarrier_speed / 7.0  # Normalize to ~max speed
            prob += (speed_factor - 0.7) * 0.1  # Bonus for running with momentum

        # Closing speed modifier
        if attempt.defender_closing > 5.0:
            # Defender closing fast - harder to juke
            prob -= 0.1
        elif attempt.defender_closing < 2.0:
            # Defender not closing - easier move
            prob += 0.05

        # Clamp to valid range
        return max(0.1, min(0.9, prob))

    def _get_success_speed(self, move_type: MoveType) -> float:
        """Get speed retention on successful move."""
        # Some moves maintain more speed than others
        speed_retention = {
            MoveType.JUKE: 0.85,
            MoveType.SPIN: 0.75,       # Spin loses momentum
            MoveType.TRUCK: 0.70,      # Contact slows you
            MoveType.STIFF_ARM: 0.90,  # Maintains momentum well
            MoveType.HURDLE: 0.80,
            MoveType.DEAD_LEG: 0.95,   # Subtle, keeps speed
            MoveType.CUT: 0.80,
            MoveType.SPEED_BURST: 1.0, # Full speed by definition
        }
        return speed_retention.get(move_type, 0.85)

    def _get_success_direction(
        self,
        move_type: MoveType,
        ballcarrier: Player,
        defender: Player,
    ) -> Optional[Vec2]:
        """Calculate new direction after successful move."""
        bc_pos = ballcarrier.pos
        def_pos = defender.pos
        bc_vel = ballcarrier.velocity

        if move_type == MoveType.JUKE:
            # Juke perpendicular to defender approach
            to_bc = (bc_pos - def_pos).normalized()
            # Pick the better perpendicular direction
            perp1 = Vec2(-to_bc.y, to_bc.x)
            perp2 = Vec2(to_bc.y, -to_bc.x)
            # Prefer the one more aligned with upfield
            if perp1.y > perp2.y:
                return (perp1 + Vec2(0, 0.5)).normalized()
            return (perp2 + Vec2(0, 0.5)).normalized()

        elif move_type == MoveType.SPIN:
            # Spin away from defender
            to_bc = (bc_pos - def_pos).normalized()
            return (to_bc + Vec2(0, 1)).normalized()  # Away + upfield

        elif move_type == MoveType.CUT:
            # Sharp cut - 45-90 degree change
            if bc_vel.length() > 0.1:
                current_dir = bc_vel.normalized()
                # Cut perpendicular, favor upfield
                perp = Vec2(-current_dir.y, current_dir.x)
                if perp.y < 0:
                    perp = Vec2(current_dir.y, -current_dir.x)
                return perp

        # Default: continue roughly current direction or upfield
        if bc_vel.length() > 0.1:
            return bc_vel.normalized()
        return Vec2(0, 1)  # Upfield

    def _emit_event(
        self,
        event_type: EventType,
        player_id: str,
        description: str,
        tick: int,
        time: float,
        data: dict = None,
    ) -> None:
        """Emit an event if event bus is available."""
        if self.event_bus:
            self.event_bus.emit_simple(
                event_type,
                tick,
                time,
                description=description,
                player_id=player_id,
                data=data or {},
            )
