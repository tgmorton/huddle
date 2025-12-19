"""Rusher Brain - Decision-making for RBs and FBs pre-handoff.

The rusher brain controls running backs and fullbacks in:
- Run path execution (pre-handoff)
- Mesh point timing
- Pass protection (blitz pickup)
- Route running (receiving)
- Lead blocking (FB)

After handoff, control transfers to the Ballcarrier Brain.

Phases: PRE_SNAP → PATH/PROTECTION/ROUTE → MESH → (Ballcarrier Brain or continue)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List

from ..orchestrator import WorldState, BrainDecision, PlayerView, PlayPhase
from ..core.vec2 import Vec2
from ..core.entities import Position, Team


# =============================================================================
# Rusher Enums
# =============================================================================

class RusherAssignment(str, Enum):
    """Current assignment type."""
    RUN_PATH = "run_path"
    PASS_PROTECTION = "pass_protection"
    ROUTE = "route"
    LEAD_BLOCK = "lead_block"
    MOTION = "motion"


class PathPhase(str, Enum):
    """Phase of run path execution."""
    SETUP = "setup"
    APPROACH = "approach"
    MESH = "mesh"
    POST_MESH = "post_mesh"


class ProtectionPhase(str, Enum):
    """Phase of pass protection."""
    SCAN = "scan"
    IDENTIFIED = "identified"
    ENGAGED = "engaged"
    FREE = "free"


# =============================================================================
# Internal State
# =============================================================================

@dataclass
class RusherState:
    """Tracked state for rusher decision-making."""
    assignment: RusherAssignment = RusherAssignment.RUN_PATH
    path_phase: PathPhase = PathPhase.SETUP
    protection_phase: ProtectionPhase = ProtectionPhase.SCAN
    mesh_complete: bool = False
    blitz_target_id: Optional[str] = None
    route_phase: str = ""
    is_lead_blocker: bool = False


_rusher_states: dict[str, RusherState] = {}


def _get_state(player_id: str) -> RusherState:
    if player_id not in _rusher_states:
        _rusher_states[player_id] = RusherState()
    return _rusher_states[player_id]


def _reset_state(player_id: str) -> None:
    _rusher_states[player_id] = RusherState()


# =============================================================================
# Helper Functions
# =============================================================================

def _find_qb(world: WorldState) -> Optional[PlayerView]:
    """Find the QB."""
    for tm in world.teammates:
        if tm.position == Position.QB:
            return tm
    return None


def _find_blitzer(world: WorldState) -> Optional[PlayerView]:
    """Find an unblocked blitzer."""
    my_pos = world.me.pos

    for opp in world.opponents:
        if opp.position in (Position.MLB, Position.OLB, Position.ILB, Position.SS, Position.CB):
            # Check if rushing
            if opp.velocity.y < -2 or opp.pos.y < world.los_y - 1:
                dist = opp.pos.distance_to(my_pos)
                if dist < 8:
                    return opp

    return None


def _get_mesh_point(world: WorldState) -> Vec2:
    """Calculate mesh point for handoff."""
    qb = _find_qb(world)

    if qb:
        # Mesh point is slightly behind and to the side of QB
        offset = Vec2(1.5, -1) if world.me.pos.x > 0 else Vec2(-1.5, -1)
        return qb.pos + offset

    # Default mesh point
    return Vec2(0, world.los_y - 4)


def _is_ball_being_handed(world: WorldState) -> bool:
    """Check if QB is handing off."""
    qb = _find_qb(world)

    if qb and qb.has_ball:
        my_dist = world.me.pos.distance_to(qb.pos)
        if my_dist < 2.0:
            return True

    return False


def _find_lead_block_target(world: WorldState) -> Optional[PlayerView]:
    """Find defender to lead block."""
    my_pos = world.me.pos

    # Look for defender in or near the hole
    for opp in world.opponents:
        if opp.position in (Position.MLB, Position.ILB, Position.OLB, Position.SS):
            dist = opp.pos.distance_to(my_pos)
            if dist < 5 and opp.pos.y > world.los_y:
                return opp

    return None


def _get_route_target(world: WorldState, route_type: str) -> Vec2:
    """Get target for route running."""
    my_pos = world.me.pos
    los = world.los_y

    # Simplified route targets
    if "flat" in route_type.lower() or "swing" in route_type.lower():
        side = 1 if my_pos.x >= 0 else -1
        return Vec2(side * 10, los + 3)

    elif "wheel" in route_type.lower():
        side = 1 if my_pos.x >= 0 else -1
        return Vec2(side * 12, los + 15)

    elif "angle" in route_type.lower():
        return Vec2(-my_pos.x * 0.5, los + 8)

    elif "check" in route_type.lower():
        return Vec2(my_pos.x, los + 5)

    # Default: flat route
    side = 1 if my_pos.x >= 0 else -1
    return Vec2(side * 8, los + 4)


# =============================================================================
# Main Brain Function
# =============================================================================

def rusher_brain(world: WorldState) -> BrainDecision:
    """Rusher brain - for RBs and FBs before receiving ball.

    Args:
        world: Complete world state

    Returns:
        BrainDecision with action and reasoning
    """
    state = _get_state(world.me.id)

    # Reset at start of play
    if world.tick == 0 or world.time_since_snap < 0.1:
        _reset_state(world.me.id)
        state = _get_state(world.me.id)

        # Determine assignment based on play call
        if "protect" in world.assignment.lower():
            state.assignment = RusherAssignment.PASS_PROTECTION
        elif "route" in world.assignment.lower() or "flat" in world.assignment.lower():
            state.assignment = RusherAssignment.ROUTE
        elif "lead" in world.assignment.lower() or world.me.position == Position.FB:
            state.assignment = RusherAssignment.LEAD_BLOCK
            state.is_lead_blocker = True
        else:
            state.assignment = RusherAssignment.RUN_PATH

    # If we have the ball, we should be using ballcarrier brain
    if world.me.has_ball:
        return BrainDecision(
            move_target=world.me.pos + Vec2(0, 5),
            move_type="sprint",
            intent="has_ball",
            reasoning="Have ball (should use ballcarrier brain)",
        )

    # =========================================================================
    # Pass Protection
    # =========================================================================
    if state.assignment == RusherAssignment.PASS_PROTECTION:
        # Scan for blitzers
        blitzer = _find_blitzer(world)

        if blitzer:
            state.protection_phase = ProtectionPhase.IDENTIFIED
            state.blitz_target_id = blitzer.id

            dist = world.me.pos.distance_to(blitzer.pos)

            if dist < 2.0:
                state.protection_phase = ProtectionPhase.ENGAGED
                return BrainDecision(
                    move_target=blitzer.pos,
                    move_type="run",
                    action="block",
                    target_id=blitzer.id,
                    intent="engaged",
                    reasoning=f"Engaged with blitzer",
                )

            return BrainDecision(
                move_target=blitzer.pos,
                move_type="run",
                action="pick_up",
                target_id=blitzer.id,
                intent="pick_up_blitz",
                reasoning=f"Picking up blitzer ({dist:.1f}yd)",
            )

        # No blitzer - scan
        state.protection_phase = ProtectionPhase.SCAN

        # Position near QB
        qb = _find_qb(world)
        protect_pos = qb.pos + Vec2(2, 1) if qb else Vec2(2, world.los_y - 5)

        return BrainDecision(
            move_target=protect_pos,
            move_type="run",
            intent="scan",
            reasoning="Scanning for blitz, protecting QB",
        )

    # =========================================================================
    # Route Running
    # =========================================================================
    if state.assignment == RusherAssignment.ROUTE:
        route_type = world.assignment

        # Check if ball in air to us
        if world.ball.is_in_flight and world.ball.intended_receiver_id == world.me.id:
            if world.ball.flight_target:
                return BrainDecision(
                    move_target=world.ball.flight_target,
                    move_type="sprint",
                    intent="catch",
                    reasoning="Ball in air, tracking",
                )

        # Run route
        route_target = _get_route_target(world, route_type)

        return BrainDecision(
            move_target=route_target,
            move_type="sprint",
            intent="route",
            reasoning=f"Running route ({route_type})",
        )

    # =========================================================================
    # Lead Blocking (FB)
    # =========================================================================
    if state.assignment == RusherAssignment.LEAD_BLOCK:
        # Find target to block
        target = _find_lead_block_target(world)

        if target:
            dist = world.me.pos.distance_to(target.pos)

            return BrainDecision(
                move_target=target.pos,
                move_type="sprint",
                action="lead_block",
                target_id=target.id,
                intent="lead_block",
                reasoning=f"Lead blocking on {target.position.value}",
            )

        # No target - head to hole
        hole_pos = Vec2(3, world.los_y + 3)  # Simplified

        return BrainDecision(
            move_target=hole_pos,
            move_type="sprint",
            intent="find_work",
            reasoning="Lead blocking, looking for work",
        )

    # =========================================================================
    # Run Path (Default)
    # =========================================================================

    # Setup phase
    if world.time_since_snap < 0.3:
        state.path_phase = PathPhase.SETUP

        # Initial steps
        initial_target = world.me.pos + Vec2(0, 1)

        return BrainDecision(
            move_target=initial_target,
            move_type="run",
            intent="setup",
            reasoning="Taking initial steps",
        )

    # Approach phase - heading to mesh
    mesh_point = _get_mesh_point(world)
    dist_to_mesh = world.me.pos.distance_to(mesh_point)

    if dist_to_mesh > 1.5:
        state.path_phase = PathPhase.APPROACH

        return BrainDecision(
            move_target=mesh_point,
            move_type="sprint",
            intent="approach_mesh",
            reasoning=f"Approaching mesh point ({dist_to_mesh:.1f}yd)",
        )

    # At mesh point
    state.path_phase = PathPhase.MESH

    if _is_ball_being_handed(world):
        return BrainDecision(
            intent="receive_handoff",
            reasoning="At mesh point, receiving handoff",
        )

    # Fake or waiting
    if not state.mesh_complete:
        return BrainDecision(
            move_target=mesh_point,
            move_type="run",
            intent="mesh",
            reasoning="At mesh, awaiting handoff",
        )

    # Post-mesh (fake)
    state.path_phase = PathPhase.POST_MESH

    # Continue fake path
    fake_target = mesh_point + Vec2(3, 3)

    return BrainDecision(
        move_target=fake_target,
        move_type="run",
        intent="sell_fake",
        reasoning="Selling fake, continuing path",
    )
