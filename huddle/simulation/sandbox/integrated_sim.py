"""Integrated passing play simulation.

Combines pocket collapse simulation with route/coverage simulation
in a unified tick loop with bidirectional pressure and action flow.

The integrated simulator runs both simulations in lockstep:
1. Pocket sim processes blocking/pressure
2. Pressure state flows to play sim
3. Play sim processes routes/coverage/QB decisions
4. QB action (throw) flows back to pocket sim
5. Check termination conditions

Coordinate System:
    The integrated simulator uses the unified coordinate system:
    - x = lateral (negative = left, positive = right)
    - y = depth (0 = LOS, positive = downfield toward defense)

    Pocket sim uses the opposite y-convention internally, so
    coordinates are converted at the integration boundary.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

# Shared components
from .shared import (
    Vec2,
    FieldContext,
    HashPosition,
    convert_pocket_to_unified,
    convert_pocket_vec2_to_unified,
)

# Pocket simulation
from .pocket_sim import (
    PocketSimulator,
    PocketSimState,
    QBState,
    QBAction,
    PressureLevel,
    DefensiveFront,
    BlockingScheme,
    DefensiveStunt,
    EngagementState,
    DropbackType,
    PlayerAttributes as PocketPlayerAttributes,
    create_man_protection,
    create_slide_protection,
)

# Play simulation
from .play_sim import (
    PlaySimulator,
    PlaySimState,
    PlayResult,
    TeamQB,
    QBAttributes,
)

from .team_route_sim import (
    Formation,
    CoverageScheme,
    RouteConcept,
    ReceiverPosition,
    DefenderPosition,
)

from .route_sim import (
    ReceiverAttributes,
    DBAttributes,
)

from .pressure import (
    PressureClock,
    get_pressure_throw_variance_multiplier,
)


# =============================================================================
# Constants
# =============================================================================

# Timing
MIN_DROPBACK_TICKS = 6          # QB won't throw before this
MAX_TIME_TO_THROW = 45          # Max ticks before forced throw/sack (~4.5 seconds)
PANIC_ETA_THRESHOLD = 3         # Ticks - below this forces immediate throw

# Pressure conversion
LIGHT_PRESSURE_DISTANCE = 4.0
MODERATE_PRESSURE_DISTANCE = 3.0
HEAVY_PRESSURE_DISTANCE = 2.0
CRITICAL_PRESSURE_DISTANCE = 1.0


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class PocketPressureState:
    """Pressure state output from pocket simulation each tick."""
    total: float = 0.0                  # 0-1 overall pressure level
    level: PressureLevel = PressureLevel.CLEAN
    eta_ticks: float = float('inf')     # Estimated ticks until closest rusher reaches QB

    # Directional breakdown
    left: float = 0.0                   # 0-1 pressure from left edge
    right: float = 0.0                  # 0-1 pressure from right edge
    front: float = 0.0                  # 0-1 pressure up the middle

    # QB state flags
    qb_moving: bool = False             # QB is stepping/sliding/scrambling
    panic: bool = False                 # eta_ticks < 3, must throw immediately
    free_rusher: bool = False           # Unblocked rusher bearing down

    # QB position (in unified coordinates)
    qb_position: Vec2 = field(default_factory=Vec2)

    def to_dict(self) -> dict:
        return {
            "total": round(self.total, 3),
            "level": self.level.value,
            "eta_ticks": round(self.eta_ticks, 1) if self.eta_ticks < 100 else "inf",
            "left": round(self.left, 3),
            "right": round(self.right, 3),
            "front": round(self.front, 3),
            "qb_moving": self.qb_moving,
            "panic": self.panic,
            "free_rusher": self.free_rusher,
            "qb_position": self.qb_position.to_dict(),
        }


@dataclass
class QBActionCommand:
    """Command from play sim to pocket sim about QB actions."""
    throwing: bool = False              # QB is throwing - terminate pocket sim
    release_tick: Optional[int] = None  # When throw was released
    target_position: Optional[Vec2] = None  # Where throw is going (for facing)

    # Scramble commands
    scramble_intent: bool = False       # QB wants to escape pocket
    scramble_direction: Optional[Vec2] = None

    def to_dict(self) -> dict:
        return {
            "throwing": self.throwing,
            "release_tick": self.release_tick,
            "target_position": self.target_position.to_dict() if self.target_position else None,
            "scramble_intent": self.scramble_intent,
        }


@dataclass
class IntegratedSimContext:
    """Shared context for integrated simulation."""
    tick: int = 0

    # Sub-simulation states (updated each tick)
    pocket_state: Optional[PocketSimState] = None
    play_state: Optional[PlaySimState] = None

    # Derived pressure state
    pressure_state: Optional[PocketPressureState] = None

    # Field context
    field_context: FieldContext = field(default_factory=FieldContext.own_25_center)

    # Timing constraints
    min_dropback_ticks: int = MIN_DROPBACK_TICKS
    max_time_to_throw: int = MAX_TIME_TO_THROW

    # Termination
    is_complete: bool = False
    result: str = "in_progress"  # "complete", "incomplete", "interception", "sack", "scramble", "throwaway"

    # Outcome details
    target_receiver: Optional[str] = None
    throw_tick: Optional[int] = None
    yards_gained: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "is_complete": self.is_complete,
            "result": self.result,
            "pressure_state": self.pressure_state.to_dict() if self.pressure_state else None,
            "field_context": self.field_context.to_dict(),
            "target_receiver": self.target_receiver,
            "throw_tick": self.throw_tick,
            "yards_gained": self.yards_gained,
        }


# =============================================================================
# Integrated Simulator
# =============================================================================

class IntegratedSimulator:
    """Orchestrates pocket and play simulations with a shared tick loop.

    The integrated simulator runs both simulations in lockstep, allowing
    pressure from blocking to directly affect QB decision-making and throw
    accuracy, while QB actions feed back to the pocket simulation.

    Usage:
        sim = IntegratedSimulator(
            formation=Formation.SPREAD,
            coverage=CoverageScheme.COVER_3,
            concept=RouteConcept.FOUR_VERTS,
            defensive_front=DefensiveFront.FOUR_MAN,
        )
        sim.setup()
        states = sim.run_full()
        print(f"Result: {sim.context.result}")
    """

    def __init__(
        self,
        # Play sim configuration
        formation: Formation = Formation.SPREAD,
        coverage: CoverageScheme = CoverageScheme.COVER_3,
        concept: RouteConcept = RouteConcept.FOUR_VERTS,

        # Pocket sim configuration
        defensive_front: DefensiveFront = DefensiveFront.FOUR_MAN,
        blocking_scheme: Optional[BlockingScheme] = None,
        stunt: Optional[DefensiveStunt] = None,
        dropback_type: DropbackType = DropbackType.SHOTGUN,

        # QB attributes (shared between sims)
        qb_attributes: Optional[QBAttributes] = None,

        # Field context
        field_context: Optional[FieldContext] = None,

        # Variance
        variance_enabled: bool = True,
    ):
        # Store configuration
        self.formation = formation
        self.coverage = coverage
        self.concept = concept
        self.defensive_front = defensive_front
        self.blocking_scheme = blocking_scheme
        self.stunt = stunt
        self.dropback_type = dropback_type
        self.qb_attributes = qb_attributes or QBAttributes()
        self.field_context = field_context or FieldContext.own_25_center()
        self.variance_enabled = variance_enabled

        # Sub-simulators (created in setup)
        self._pocket_sim: Optional[PocketSimulator] = None
        self._play_sim: Optional[PlaySimulator] = None

        # Shared context
        self.context: Optional[IntegratedSimContext] = None

        # Internal tracking
        self._qb_action: QBActionCommand = QBActionCommand()
        self._throw_initiated: bool = False

    def setup(self) -> IntegratedSimContext:
        """Initialize both simulations and create shared context."""

        # Reset internal state flags
        self._throw_initiated = False
        self._qb_action = QBActionCommand()

        # Create pocket simulator
        self._pocket_sim = PocketSimulator(
            qb_depth=7.0,
            defensive_front=self.defensive_front,
            blocking_scheme=self.blocking_scheme,
            stunt=self.stunt,
            dropback_type=self.dropback_type,
            qb_mobility=self.qb_attributes.mobility,
        )
        pocket_state = self._pocket_sim.setup()

        # Create play simulator
        self._play_sim = PlaySimulator(
            formation=self.formation,
            coverage=self.coverage,
            concept=self.concept,
            variance_enabled=self.variance_enabled,
            qb_attributes=self.qb_attributes,
        )
        self._play_sim.setup()
        play_state = self._play_sim.state

        # Apply field context adjustments to receiver alignments
        self._apply_field_context_to_routes()

        # Create shared context
        self.context = IntegratedSimContext(
            tick=0,
            pocket_state=pocket_state,
            play_state=play_state,
            pressure_state=self._extract_pressure_state(),
            field_context=self.field_context,
        )

        return self.context

    def tick(self) -> IntegratedSimContext:
        """Execute one tick of the integrated simulation.

        Order of operations:
        1. Pocket sim tick (blocking, rusher movement, QB pressure response)
        2. Extract pressure state from pocket
        3. Feed pressure to play sim's PressureClock
        4. Play sim tick (routes, coverage, QB decision)
        5. Extract QB action (throw decision)
        6. Feed QB action back to pocket sim (if throwing)
        7. Check termination conditions
        """
        if self.context is None:
            raise RuntimeError("Call setup() first")

        if self.context.is_complete:
            return self.context

        self.context.tick += 1

        # === PHASE 1: Pocket Simulation ===
        if not self._pocket_sim.state.is_complete:
            # Check if throw was initiated - set pocket sim to complete
            if self._throw_initiated:
                self._pocket_sim.state.is_complete = True
            else:
                self._pocket_sim.tick()

        # === PHASE 2: Extract Pressure State ===
        self.context.pressure_state = self._extract_pressure_state()

        # === PHASE 3: Feed External Pressure to Play Sim ===
        # Use the external pressure hook so play_sim uses pocket_sim's pressure
        # Pass full directional pressure state for accuracy bias and decision-making
        pressure = self.context.pressure_state
        self._play_sim.set_external_pressure(
            total=pressure.total,
            eta_ticks=pressure.eta_ticks,
            left=pressure.left,
            right=pressure.right,
            front=pressure.front,
            panic=pressure.panic,
        )

        # === PHASE 4: Play Simulation ===
        # Check if QB has committed to scrambling in pocket sim - if so, skip play sim throws
        qb_scrambling = (
            self._pocket_sim.state.qb_state and
            self._pocket_sim.state.qb_state.scramble_committed
        )

        if not self._play_sim.state.is_complete and not qb_scrambling:
            # Apply pressure modifiers
            self._apply_pressure_modifiers()

            # Tick play sim
            self._play_sim.tick()

        # === PHASE 5: Check for Throw and Wire Back to Pocket Sim ===
        if self._play_sim.state.ball and self._play_sim.state.ball.is_thrown:
            if not self._throw_initiated:
                self._throw_initiated = True
                self._qb_action.throwing = True
                self._qb_action.release_tick = self.context.tick
                self.context.throw_tick = self.context.tick

                # Signal pocket_sim that QB has thrown and finalize its state
                self._pocket_sim.set_qb_throwing()
                self._pocket_sim.state.is_complete = True

                # Determine pocket result based on pressure at throw
                pressure = self.context.pressure_state
                if pressure.panic:
                    self._pocket_sim.state.result = "pressure_throw"  # Got it off under duress
                elif pressure.level in (PressureLevel.HEAVY, PressureLevel.CRITICAL):
                    self._pocket_sim.state.result = "pressure_throw"
                elif pressure.level == PressureLevel.MODERATE:
                    self._pocket_sim.state.result = "pressured"
                else:
                    self._pocket_sim.state.result = "clean_pocket"

        # === PHASE 6: Check Termination ===
        self._check_termination()

        # Update context with latest states
        self.context.pocket_state = self._pocket_sim.state
        self.context.play_state = self._play_sim.state

        return self.context

    def run_full(self, max_ticks: int = 60) -> list[IntegratedSimContext]:
        """Run simulation to completion and return all tick states."""
        if self.context is None:
            self.setup()

        states = []
        for _ in range(max_ticks):
            state = self.tick()
            # Create a snapshot of the context
            states.append(self._snapshot_context())

            if self.context.is_complete:
                break

        return states

    def _snapshot_context(self) -> dict:
        """Create a serializable snapshot of current state."""
        return self.context.to_dict()

    def _extract_pressure_state(self) -> PocketPressureState:
        """Extract pressure state from pocket simulation."""
        pocket_state = self._pocket_sim.state
        qb_state = pocket_state.qb_state

        # Get QB position in pocket sim coords
        qb_pos_pocket = pocket_state.qb.position

        # Convert to unified coordinates
        qb_pos_unified = convert_pocket_vec2_to_unified(qb_pos_pocket)

        # Build a map of rusher -> engagement for speed lookup
        rusher_engagements: dict = {}
        for eng in pocket_state.engagements:
            rusher_engagements[eng.rusher.id] = eng

        # Calculate ETA of nearest rusher using real speeds
        min_eta = float('inf')
        free_rusher_present = False
        epsilon = 0.01  # Avoid division by zero

        for rusher in pocket_state.rushers:
            if rusher.is_down:
                continue

            dist = rusher.position.distance_to(qb_pos_pocket)

            # Determine rusher speed based on state
            if rusher.is_free:
                free_rusher_present = True
                speed = self._pocket_sim.FREE_RUSHER_SPEED
            else:
                # Check engagement state for this rusher
                eng = rusher_engagements.get(rusher.id)
                if eng and eng.state == EngagementState.RUSHER_WINNING:
                    # Winning rusher moves faster - use calculated movement
                    # Base engaged movement with winning bonus
                    advantage = eng.advantage.accumulated_margin if eng.advantage else 0
                    factor = 1.0 + min(1.0, max(0, advantage - 15) / 30)
                    speed = self._pocket_sim.ENGAGED_MOVEMENT * factor
                elif eng and eng.state == EngagementState.SHED:
                    # Shed = essentially free
                    speed = self._pocket_sim.FREE_RUSHER_SPEED
                else:
                    # Neutral or losing - slow progress
                    speed = self._pocket_sim.ENGAGED_MOVEMENT * 0.3

            eta = dist / max(speed, epsilon)
            min_eta = min(min_eta, eta)

        # Get directional pressure values from QBState if available
        if qb_state:
            pressure_left = qb_state.pressure_left
            pressure_right = qb_state.pressure_right
            pressure_front = qb_state.pressure_front
            qb_moving = qb_state.action in (
                QBAction.STEPPING_UP,
                QBAction.SLIDING,
                QBAction.SCRAMBLING,
            )
        else:
            pressure_left = 0.0
            pressure_right = 0.0
            pressure_front = 0.0
            qb_moving = False

        # Calculate total pressure by blending:
        # 1. Directional pressure from QBState (based on rusher distances)
        # 2. ETA urgency (closer = more pressure)
        # 3. Free rusher bonus (unblocked rusher = extra danger)
        directional_pressure = max(pressure_left, pressure_right, pressure_front)

        # ETA urgency: convert ETA ticks to pressure (0-1)
        # ETA <= 3 ticks = 1.0 (panic), ETA >= 20 ticks = 0.0 (clean)
        if min_eta < float('inf'):
            eta_urgency = max(0.0, min(1.0, (20 - min_eta) / 17))
        else:
            eta_urgency = 0.0

        # Free rusher bonus: unblocked rusher adds significant pressure
        free_rusher_bonus = 0.25 if free_rusher_present else 0.0

        # Blend total pressure: max of directional + ETA contribution + free rusher
        # ETA urgency is weighted heavily when close
        total_pressure = min(1.0, max(
            directional_pressure,
            eta_urgency * 0.8,  # ETA alone can drive 80% pressure
        ) + free_rusher_bonus + eta_urgency * 0.2)  # Add urgency bonus

        # Determine pressure level from total
        if total_pressure >= 0.8:
            pressure_level = PressureLevel.CRITICAL
        elif total_pressure >= 0.6:
            pressure_level = PressureLevel.HEAVY
        elif total_pressure >= 0.4:
            pressure_level = PressureLevel.MODERATE
        elif total_pressure >= 0.2:
            pressure_level = PressureLevel.LIGHT
        else:
            pressure_level = PressureLevel.CLEAN

        return PocketPressureState(
            total=total_pressure,
            level=pressure_level,
            eta_ticks=min_eta,
            left=pressure_left,
            right=pressure_right,
            front=pressure_front,
            qb_moving=qb_moving,
            panic=min_eta < PANIC_ETA_THRESHOLD,
            free_rusher=free_rusher_present,
            qb_position=qb_pos_unified,
        )

    def _apply_pressure_modifiers(self) -> None:
        """Apply pressure-based modifiers to play sim behavior."""
        pressure = self.context.pressure_state

        # Handle panic mode - force immediate throw
        if pressure.panic and self.context.tick >= MIN_DROPBACK_TICKS:
            # QB is about to be sacked - panic throw
            if not self._throw_initiated and not self._play_sim.state.qb.has_thrown:
                # Try to force a panic throw to current read
                if self._play_sim.panic_throw():
                    self._throw_initiated = True
                    self._qb_action.throwing = True
                    self._qb_action.release_tick = self.context.tick
                    self.context.throw_tick = self.context.tick

        # Under heavy pressure, QB may skip reads
        # (This is now handled in play_sim._process_qb via _calculate_read_skip_chance)

    def _apply_field_context_to_routes(self) -> None:
        """Adjust receiver alignments, routes, and DB alignments based on field position."""
        if not self._play_sim or not self._play_sim.state:
            return

        field = self.field_context
        play_state = self._play_sim.state

        # Hash position affects receiver splits
        for receiver in play_state.receivers:
            original_x = receiver.position.x

            # Compress routes toward boundary side
            if field.hash_position == HashPosition.RIGHT:
                # Boundary is right, compress right-side receivers
                if original_x > 0:
                    compression = field.get_boundary_compression()
                    receiver.position = Vec2(
                        original_x * compression,
                        receiver.position.y
                    )
                    self._compress_route_waypoints(receiver, compression, "right")

            elif field.hash_position == HashPosition.LEFT:
                # Boundary is left, compress left-side receivers
                if original_x < 0:
                    compression = field.get_boundary_compression()
                    receiver.position = Vec2(
                        original_x * compression,
                        receiver.position.y
                    )
                    self._compress_route_waypoints(receiver, compression, "left")

        # Apply field context to defenders (DB alignments and zone positioning)
        self._apply_field_context_to_defenders()

    def _apply_field_context_to_defenders(self) -> None:
        """Adjust defender alignments and zone positioning based on field position."""
        if not self._play_sim or not self._play_sim.state:
            return

        field = self.field_context
        play_state = self._play_sim.state

        # Zone defenders shade toward field side (away from boundary)
        # Man defenders can play inside leverage on boundary receivers
        for defender in play_state.defenders:
            original_x = defender.position.x

            if field.hash_position == HashPosition.RIGHT:
                # Boundary is right side, field is left
                # Zone defenders shift slightly left (toward field)
                # Man defenders on boundary receivers can play inside leverage
                if hasattr(defender, 'zone_center') and defender.zone_center:
                    # Zone defender - shift zone center toward field
                    shift = -0.5  # Shift half yard toward field (left)
                    defender.zone_center = Vec2(
                        defender.zone_center.x + shift,
                        defender.zone_center.y
                    )
                else:
                    # Man defender on boundary side - play inside leverage
                    if original_x > 0:  # Defender on boundary side
                        # Shift slightly inside (toward center)
                        leverage_shift = -0.3
                        defender.position = Vec2(
                            original_x + leverage_shift,
                            defender.position.y
                        )

            elif field.hash_position == HashPosition.LEFT:
                # Boundary is left side, field is right
                if hasattr(defender, 'zone_center') and defender.zone_center:
                    # Zone defender - shift zone center toward field
                    shift = 0.5  # Shift half yard toward field (right)
                    defender.zone_center = Vec2(
                        defender.zone_center.x + shift,
                        defender.zone_center.y
                    )
                else:
                    # Man defender on boundary side - play inside leverage
                    if original_x < 0:  # Defender on boundary side
                        # Shift slightly inside (toward center)
                        leverage_shift = 0.3
                        defender.position = Vec2(
                            original_x + leverage_shift,
                            defender.position.y
                        )

    def _compress_route_waypoints(
        self,
        receiver,
        factor: float,
        boundary_side: str
    ) -> None:
        """Compress route waypoints horizontally toward the field center."""
        for waypoint in receiver.route:
            if boundary_side == "right" and waypoint.position.x > 0:
                waypoint.position = Vec2(
                    waypoint.position.x * factor,
                    waypoint.position.y
                )
            elif boundary_side == "left" and waypoint.position.x < 0:
                waypoint.position = Vec2(
                    waypoint.position.x * factor,
                    waypoint.position.y
                )

    def _check_termination(self) -> None:
        """Check all termination conditions for the integrated simulation."""

        # === SACK ===
        if self._pocket_sim.state.result == "sack":
            self.context.is_complete = True
            self.context.result = "sack"
            return

        # === THROW RESOLVED ===
        if self._play_sim.state.is_complete:
            self.context.is_complete = True
            play_result = self._play_sim.state.play_result

            if play_result == PlayResult.COMPLETE:
                self.context.result = "complete"
                # Calculate yards gained (receiver position at catch)
                # In unified coords: y=0 is LOS, y>0 is downfield (gain), y<0 is behind LOS (loss)
                if self._play_sim.state.ball and self._play_sim.state.ball.is_caught:
                    catch_y = self._play_sim.state.ball.position.y
                    self.context.yards_gained = round(catch_y, 1)  # Positive = gain, negative = behind LOS
            elif play_result == PlayResult.INTERCEPTION:
                self.context.result = "interception"
            else:
                self.context.result = "incomplete"

            # Record target
            if self._play_sim.state.qb.target_receiver_id:
                self.context.target_receiver = self._play_sim.state.qb.target_receiver_id

            return

        # === SCRAMBLE BEYOND LOS ===
        if self._pocket_sim.state.qb_state:
            if self._pocket_sim.state.qb_state.action == QBAction.SCRAMBLING:
                # Convert QB position to unified coordinates for consistent handling
                qb_pos_pocket = self._pocket_sim.state.qb.position
                qb_pos_unified = convert_pocket_vec2_to_unified(qb_pos_pocket)
                # In unified coords: y=0 is LOS, y>0 is downfield (yards gained)
                if qb_pos_unified.y > 0:  # Crossed LOS (positive y in unified = downfield)
                    self.context.is_complete = True
                    self.context.result = "scramble"
                    self.context.yards_gained = round(qb_pos_unified.y, 1)
                    return

        # === TIME LIMIT ===
        if self.context.tick >= self.context.max_time_to_throw:
            # Force sack if under heavy pressure
            if self.context.pressure_state.level in (
                PressureLevel.HEAVY,
                PressureLevel.CRITICAL
            ):
                self.context.is_complete = True
                self.context.result = "sack"
            else:
                # Throwaway
                self.context.is_complete = True
                self.context.result = "throwaway"
            return


# =============================================================================
# Factory Functions
# =============================================================================

def create_integrated_sim(
    formation: str = "spread",
    coverage: str = "cover_3",
    concept: str = "four_verts",
    defensive_front: str = "4_man",
    field_yard_line: int = 25,
    hash_position: str = "middle",
) -> IntegratedSimulator:
    """Create an integrated simulator with string-based configuration.

    Args:
        formation: "spread", "pro", "i_form", "singleback"
        coverage: "cover_0", "cover_1", "cover_2", "cover_3", "cover_4"
        concept: "four_verts", "smash", "mesh", "flood", "slants"
        defensive_front: "3_man", "4_man", "5_man"
        field_yard_line: 0-100 (0=own goal, 100=opponent goal)
        hash_position: "left", "middle", "right"

    Returns:
        Configured IntegratedSimulator
    """
    # Map strings to enums
    formation_map = {
        "spread": Formation.SPREAD,
        "trips_right": Formation.TRIPS_RIGHT,
        "trips_left": Formation.TRIPS_LEFT,
        "empty": Formation.EMPTY,
        "doubles": Formation.DOUBLES,
    }

    coverage_map = {
        "cover_0": CoverageScheme.COVER_0,
        "cover_1": CoverageScheme.COVER_1,
        "cover_2": CoverageScheme.COVER_2,
        "cover_3": CoverageScheme.COVER_3,
        "cover_4": CoverageScheme.COVER_4,
    }

    concept_map = {
        "four_verts": RouteConcept.FOUR_VERTS,
        "smash": RouteConcept.SMASH,
        "mesh": RouteConcept.MESH,
        "flood": RouteConcept.FLOOD,
        "slants": RouteConcept.SLANTS,
    }

    front_map = {
        "3_man": DefensiveFront.THREE_MAN,
        "4_man": DefensiveFront.FOUR_MAN,
        "5_man": DefensiveFront.FIVE_MAN,
    }

    hash_map = {
        "left": HashPosition.LEFT,
        "middle": HashPosition.MIDDLE,
        "right": HashPosition.RIGHT,
    }

    # Create field context
    field_context = FieldContext.from_yard_line(
        yard_line=field_yard_line,
        hash_position=hash_map.get(hash_position, HashPosition.MIDDLE),
    )

    return IntegratedSimulator(
        formation=formation_map.get(formation, Formation.SPREAD),
        coverage=coverage_map.get(coverage, CoverageScheme.COVER_3),
        concept=concept_map.get(concept, RouteConcept.FOUR_VERTS),
        defensive_front=front_map.get(defensive_front, DefensiveFront.FOUR_MAN),
        field_context=field_context,
    )
