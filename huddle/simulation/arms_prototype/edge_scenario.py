"""
Edge rush scenario - DE/OLB vs OT.

Different from interior play:
- Wider starting positions
- Speed rush is primary weapon
- OT uses kick-slide, vertical set
- Path to QB is around the corner, not through
- AGI matters much more than interior
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional
import math
import random

from .vec2 import Vec2
from .player import Player, PlayerRole
from .attributes import PhysicalAttributes
from .simulation import Simulation, SimulationConfig, SimulationState
from .arm import ArmSide, HandState
from .moves import (
    attempt_speed_rush,
    attempt_speed_to_power,
    attempt_ghost,
    attempt_long_arm,
    attempt_swim,
    attempt_rip,
    attempt_spin,
    attempt_club,
    attempt_bull_rush,
    attempt_vertical_set,
    attempt_kick_slide,
    attempt_punch_reset,
    attempt_steer,
    MoveResult,
)


def edge_rusher_intent(player: Player, state: SimulationState) -> None:
    """
    Edge rusher AI: Win around the corner with speed, counter when OT oversets.

    Primary weapons:
    1. Speed rush - beat OT to the corner
    2. Speed-to-power - if OT oversets, convert inside
    3. Finesse moves - swim, rip when engaged
    4. Ghost - avoid contact entirely (rare)
    """
    target = Vec2(0, -5)  # QB position

    # Check if we've shed
    if player.id in state.shed_players:
        player.face_toward(target)
        player.move_toward(target, speed=6.0)  # Edge guys are fast
        player.retract_arms()
        return

    # Find the tackle
    tackle = None
    for p in state.players.values():
        if p.role == PlayerRole.BLOCKER:
            tackle = p
            break

    if not tackle:
        player.move_toward(target, speed=5.0)
        return

    # Face toward QB (not blocker - we're trying to get around them)
    player.face_toward(target)

    dist_to_tackle = player.position.distance_to(tackle.position)
    dist_to_qb = player.position.distance_to(target)

    # === TRACK RUSH PHASE ===
    if not hasattr(state, '_edge_phase'):
        state._edge_phase = {}
    if player.id not in state._edge_phase:
        state._edge_phase[player.id] = "approach"

    phase = state._edge_phase[player.id]

    # === MOVE ATTEMPT TIMING ===
    last_move_tick = getattr(state, '_last_move_tick', {}).get(player.id, -100)
    can_attempt_move = (state.tick - last_move_tick) >= 12  # Faster than interior

    # === APPROACH PHASE ===
    if phase == "approach" or dist_to_tackle > 2.5:
        # Sprint toward corner (outside the tackle)
        tackle_x = tackle.position.x
        corner_target = Vec2(tackle_x + 2.5, target.y + 2.0)  # Wide arc

        player.move_toward(corner_target, speed=5.5)

        if dist_to_tackle < 2.5:
            state._edge_phase[player.id] = "attack"
        return

    # === ATTACK PHASE ===
    elif phase == "attack":
        # Engaged with tackle - choose approach

        # Read the tackle's positioning
        tackle_is_sliding = abs(tackle.velocity.x) > 0.8
        tackle_overcommit_outside = tackle.position.x > player.position.x + 0.5
        tackle_has_hands = (tackle.arms.left.hand_state == HandState.CONTROLLING or
                           tackle.arms.right.hand_state == HandState.CONTROLLING)

        if can_attempt_move:
            if not hasattr(state, '_last_move_tick'):
                state._last_move_tick = {}
            state._last_move_tick[player.id] = state.tick

            result = _attempt_edge_move(player, tackle, state, tackle_overcommit_outside)
            if result:
                if hasattr(state, '_verbose') and state._verbose:
                    print(f"  [Edge] {result.description}")
                if result.shed:
                    state.shed_players[player.id] = state.tick
                    return

        # === CONTINUOUS PRESSURE ===
        # Keep working toward the corner
        if not tackle_has_hands:
            # No contact - try to get around
            corner = Vec2(player.position.x + 1.5, target.y)
            player.move_toward(corner, speed=4.5)
        else:
            # Engaged - work hands and drive
            player.reach_both_toward(tackle.body.chest_center)

            # Drive toward QB with lateral component
            to_target = target - player.position
            if to_target.length() > 0.1:
                # Add lateral component to go around
                lateral = Vec2(0.5, 0)
                drive_dir = (to_target.normalized() + lateral).normalized()
                player.drive_step(drive_dir)

                if player.can_generate_power:
                    speed = 1.5 if player.has_inside_hands else 0.8
                    player.velocity = drive_dir * speed


def _attempt_edge_move(
    rusher: Player,
    tackle: Player,
    state: SimulationState,
    tackle_overcommit: bool
) -> Optional[MoveResult]:
    """
    Choose and attempt an edge rush move.

    Edge moves favor AGI over STR compared to interior.
    """
    # Player profile determines move selection
    str_rating = rusher.attributes.strength
    agi_rating = rusher.attributes.agility

    # Edge rushers lean toward finesse
    finesse_tendency = agi_rating / (str_rating + agi_rating + 1)
    power_tendency = 1.0 - finesse_tendency

    # Move weights
    moves = {}

    # === SPEED MOVES (Edge primary) ===
    # Speed rush - the main weapon
    speed_base = 0.25 * finesse_tendency
    if not tackle.is_engaged:
        speed_base += 0.2  # Better chance if no contact
    moves["speed"] = speed_base

    # Ghost - high risk home run
    ghost_base = 0.05 * finesse_tendency
    if tackle.arms.left.extension > 0.7 or tackle.arms.right.extension > 0.7:
        ghost_base += 0.1  # Tackle overextended
    moves["ghost"] = ghost_base

    # === COUNTER MOVES ===
    # Speed-to-power - punish oversetting
    if tackle_overcommit:
        moves["speed_to_power"] = 0.3  # Big opportunity
    else:
        moves["speed_to_power"] = 0.1 * power_tendency

    # === FINESSE MOVES (still work on edge) ===
    # Swim - works well on edge
    swim_base = 0.15 * finesse_tendency
    if tackle.body.pad_level > 0.5:
        swim_base += 0.15
    moves["swim"] = swim_base

    # Rip - inside counter
    moves["rip"] = 0.12 + 0.08 * finesse_tendency

    # Spin - risky but can work
    if tackle.velocity.length() > 1.0:
        moves["spin"] = 0.15 * finesse_tendency
    else:
        moves["spin"] = 0.05

    # === POWER MOVES (less common on edge) ===
    # Long arm - control distance
    moves["long_arm"] = 0.1 + 0.1 * power_tendency

    # Bull - still viable for power edges
    if rusher.has_inside_hands:
        moves["bull"] = 0.15 * power_tendency
    else:
        moves["bull"] = 0.05

    # Ensure minimums
    for move in moves:
        moves[move] = max(0.03, moves[move])

    # Pick a move
    total = sum(moves.values())
    r = random.random() * total
    cumulative = 0

    chosen = "speed"
    for move, weight in moves.items():
        cumulative += weight
        if r < cumulative:
            chosen = move
            break

    # Execute
    arm_side = random.choice([ArmSide.LEFT, ArmSide.RIGHT])

    if chosen == "speed":
        return attempt_speed_rush(rusher, tackle, side="outside")
    elif chosen == "ghost":
        return attempt_ghost(rusher, tackle)
    elif chosen == "speed_to_power":
        return attempt_speed_to_power(rusher, tackle)
    elif chosen == "swim":
        return attempt_swim(rusher, tackle, arm_side)
    elif chosen == "rip":
        return attempt_rip(rusher, tackle, arm_side)
    elif chosen == "spin":
        return attempt_spin(rusher, tackle, direction="inside")
    elif chosen == "long_arm":
        return attempt_long_arm(rusher, tackle, arm_side)
    elif chosen == "bull":
        return attempt_bull_rush(rusher, tackle)

    return None


def tackle_intent(player: Player, state: SimulationState) -> None:
    """
    OT pass protection: Mirror the edge rusher, don't get beat around the corner.

    Technique:
    1. Kick-slide to stay in front
    2. Vertical set to cut off angle
    3. Punch to establish contact
    4. Redirect when beaten
    """
    target = Vec2(0, -5)  # QB position

    # Find the rusher
    rusher = None
    for p in state.players.values():
        if p.role == PlayerRole.RUSHER:
            rusher = p
            break

    if not rusher:
        return

    # Check if rusher has shed
    if rusher.id in state.shed_players:
        # Try to redirect
        player.face_toward(rusher.position)
        dist = player.position.distance_to(rusher.position)

        if dist < 2.5:
            # Get hands on, push outside
            player.reach_both_toward(rusher.body.chest_center)
            outward = Vec2(1.0 if rusher.position.x > 0 else -1.0, 0)
            player.velocity = (rusher.position - player.position).normalized() * 3.0

            # Apply redirect
            if dist < 1.5:
                strength = 1.0 - (dist / 1.5)
                if not hasattr(state, 'active_redirects'):
                    state.active_redirects = {}
                state.active_redirects[rusher.id] = (outward, strength)
        else:
            # Chase
            player.move_toward(rusher.position, speed=4.0)
        return

    # Face the rusher
    player.face_toward(rusher.position)
    dist = player.position.distance_to(rusher.position)

    # Vector analysis
    to_rusher = rusher.position - player.position
    rusher_outside = rusher.position.x > player.position.x

    # === PROTECTION TECHNIQUE ===

    if dist > 3.0:
        # Rusher far - set depth, prepare for speed
        # Vertical set
        attempt_vertical_set(player, rusher, depth=0.2)

    elif dist > 1.5:
        # Approaching - kick-slide to intercept
        # Mirror rusher's lateral movement
        kick_dir = 1.0 if rusher_outside else -1.0

        # Also give ground backward
        player.kick_step(Vec2(kick_dir * 0.3, -0.2))
        player.velocity = Vec2(kick_dir * 2.0, -0.5)

        # Prepare to punch
        player.lower_pad_level(0.03)

    else:
        # Engaged - hand fighting
        if not player.is_engaged:
            player.punch_both()
            player.lower_pad_level(0.05)

        player.reach_both_toward(rusher.body.chest_center)

        # === OT COUNTER MOVES ===
        last_counter = getattr(state, '_ot_last_counter', {}).get(player.id, -100)
        can_counter = (state.tick - last_counter) >= 10

        if can_counter:
            result = _attempt_tackle_counter(player, rusher, state)
            if result:
                if not hasattr(state, '_ot_last_counter'):
                    state._ot_last_counter = {}
                state._ot_last_counter[player.id] = state.tick

                if hasattr(state, '_verbose') and state._verbose:
                    print(f"  [OT] {result.description}")

        # Mirror and give ground
        force_debt = player.feet.force_debt.length()

        if force_debt > 0.15:
            # Under pressure - give ground
            to_qb = (target - player.position).normalized()
            player.kick_step(to_qb * 0.2)
            player.velocity = to_qb * 1.0
        else:
            # Holding ground - mirror laterally
            rusher_lateral = rusher.velocity.x
            if abs(rusher_lateral) > 0.5:
                player.kick_step(Vec2(rusher_lateral * 0.4, 0))

        # Don't give too much ground
        dist_to_qb = player.position.distance_to(target)
        if dist_to_qb < 2.5:
            player.velocity = player.velocity * 0.5


def _attempt_tackle_counter(
    tackle: Player,
    rusher: Player,
    state: SimulationState
) -> Optional[MoveResult]:
    """
    OT counter moves against edge rushers.
    """
    # Assess situation
    rusher_has_inside = rusher.has_inside_hands
    tackle_has_inside = tackle.has_inside_hands
    under_pressure = tackle.feet.force_debt.length() > 0.25

    # Choose counter
    if under_pressure:
        # Under pressure - anchor and reset
        from .moves import attempt_anchor
        return attempt_anchor(tackle, rusher)

    elif rusher_has_inside and not tackle_has_inside:
        # Lost hand position - punch reset
        if random.random() < 0.6:
            return attempt_punch_reset(tackle, rusher)
        else:
            arm_side = random.choice([ArmSide.LEFT, ArmSide.RIGHT])
            from .moves import attempt_hand_fight
            return attempt_hand_fight(tackle, rusher, arm_side)

    elif tackle_has_inside and random.random() < 0.3:
        # Have control - steer outside
        return attempt_steer(tackle, rusher, direction="outside")

    return None


# =============================================================================
# Scenario Factory
# =============================================================================

def create_edge_scenario(
    edge_attrs: PhysicalAttributes = None,
    tackle_attrs: PhysicalAttributes = None,
    pocket_time: float = 3.5,
    side: str = "right",  # Which side of the line (affects starting positions)
) -> Simulation:
    """
    Create an edge rush scenario (DE vs OT).

    Args:
        edge_attrs: Edge rusher attributes (default: average_edge)
        tackle_attrs: OT attributes (default: average_tackle)
        pocket_time: Time until play ends
        side: "right" or "left" side of the line
    """
    config = SimulationConfig(
        dt=0.05,
        max_ticks=int(pocket_time / 0.05),
        target_position=Vec2(0, -5),
    )

    sim = Simulation(config)

    # Defaults
    if edge_attrs is None:
        edge_attrs = PhysicalAttributes.average_edge()
    if tackle_attrs is None:
        tackle_attrs = PhysicalAttributes.average_tackle()

    # Position based on side
    x_mult = 1.0 if side == "right" else -1.0

    # Edge rusher - starts wide
    edge = Player.create_lineman(
        id="EDGE",
        role=PlayerRole.RUSHER,
        position=Vec2(3.5 * x_mult, 2.0),
        facing=-math.pi / 2,
        weight=265,  # Edge guys are lighter
        attributes=edge_attrs,
    )

    # OT - starts at tackle position
    tackle = Player.create_lineman(
        id="OT",
        role=PlayerRole.BLOCKER,
        position=Vec2(2.5 * x_mult, 1.0),
        facing=math.pi,
        weight=310,
        attributes=tackle_attrs,
    )

    sim.add_player(edge)
    sim.add_player(tackle)

    sim.set_intent("EDGE", edge_rusher_intent)
    sim.set_intent("OT", tackle_intent)

    return sim
