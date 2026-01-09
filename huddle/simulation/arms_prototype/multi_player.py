"""
Multi-player simulation scenarios.

Handles 2v1 (double teams) and 3v2 (interior line) scenarios.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
import math
import random

from .vec2 import Vec2
from .player import Player, PlayerRole
from .attributes import PhysicalAttributes
from .simulation import Simulation, SimulationConfig, SimulationState, make_blocker_intent
from .assignments import AssignmentTracker, BlockType, DoubleTeam
from .collision import resolve_double_team, can_split_double
from .moves import attempt_swim, attempt_rip, attempt_bull_rush, attempt_club, attempt_spin
from .arm import ArmSide


@dataclass
class MultiPlayerState(SimulationState):
    """Extended state for multi-player scenarios."""
    assignments: AssignmentTracker = field(default_factory=AssignmentTracker)


class MultiPlayerSimulation(Simulation):
    """
    Simulation handling multiple OL vs multiple DL.
    """

    def __init__(self, config: Optional[SimulationConfig] = None):
        super().__init__(config)
        self.state = MultiPlayerState()
        self._assignments = AssignmentTracker()

    @property
    def assignments(self) -> AssignmentTracker:
        return self._assignments

    def tick(self) -> bool:
        """
        Run one tick - uses parent's tick() with double team handling added.

        This ensures multi-player behaves IDENTICALLY to 1v1 for the core physics,
        just with added double team resolution.
        """
        dt = self.config.dt

        # === BEFORE parent tick: Handle double team coordination ===
        for dl_id, double_team in list(self._assignments.double_teams.items()):
            if not double_team.active:
                continue

            post = self.state.players.get(double_team.post_blocker_id)
            drive = self.state.players.get(double_team.drive_blocker_id)
            rusher = self.state.players.get(dl_id)

            if post and drive and rusher:
                double_team.ticks_active += 1
                resolve_double_team(post, drive, rusher, double_team.drive_direction, dt)

                # Check if rusher can split the double
                if double_team.ticks_active > 20:  # Give time to establish
                    split_chance = can_split_double(rusher, post, drive)
                    if random.random() < split_chance * dt:
                        double_team.active = False
                        self.state.shed_players[dl_id] = self.state.tick
                        if hasattr(self.state, '_verbose') and self.state._verbose:
                            print(f"  [SPLIT] {dl_id} splits the double team!")

        # === RUN PARENT'S TICK - same physics as 1v1 ===
        return super().tick()


# =============================================================================
# Multi-Player Intent Functions
# =============================================================================

# Blocker intents now use unified make_blocker_intent() from simulation.py

def multi_rusher_intent(
    player: Player,
    state: SimulationState,
    assignments: AssignmentTracker
) -> None:
    """
    Intent for a rusher facing potential double teams.
    """
    target = Vec2(0, -5)

    # Check if double-teamed
    is_doubled = assignments.is_double_teamed(player.id)

    # Check if shed
    if player.id in state.shed_players:
        player.face_toward(target)
        player.move_toward(target, speed=5.0)
        player.retract_arms()
        return

    player.face_toward(target)

    # Find blockers on me
    blockers_on_me = assignments.get_blockers_on(player.id)

    if is_doubled:
        # === HANDLING DOUBLE TEAM ===
        # Against a double team, the DT must fight for position but typically
        # gets driven back. The collision physics (resolve_double_team) handles
        # the force battle. Here we just set intent/stance.

        # Get lower - fight for leverage
        player.lower_pad_level(0.05)

        # Drive step toward target to generate resistance
        to_target = target - player.position
        if to_target.length() > 0.1:
            player.drive_step(to_target.normalized())

        # DO NOT set velocity here - let collision physics determine outcome
        # The double team force should overcome our intent to move forward

        # Occasional move attempt to try to split (harder vs double)
        if random.random() < 0.02:  # 2% per tick
            for blocker_id in blockers_on_me:
                blocker = state.players.get(blocker_id)
                if blocker:
                    _attempt_pass_rush_move_multi(player, blocker, state)
                    break

    else:
        # === 1v1 or UNBLOCKED ===
        closest_blocker = None
        closest_dist = float('inf')

        for blocker_id in blockers_on_me:
            blocker = state.players.get(blocker_id)
            if blocker:
                dist = player.position.distance_to(blocker.position)
                if dist < closest_dist:
                    closest_dist = dist
                    closest_blocker = blocker

        if closest_blocker and closest_dist < 2.0:
            # Engaged with blocker
            if not player.is_engaged:
                player.punch_both()
                player.lower_pad_level(0.05)

            player.reach_both_toward(closest_blocker.body.chest_center)

            # Move attempt timing
            last_move_tick = getattr(state, '_last_move_tick', {}).get(player.id, -100)
            can_attempt = (state.tick - last_move_tick) >= 15

            blocker_compromised = closest_blocker.feet.force_debt.length() > 0.3

            if blocker_compromised and can_attempt:
                if not hasattr(state, '_last_move_tick'):
                    state._last_move_tick = {}
                state._last_move_tick[player.id] = state.tick

                result = _attempt_pass_rush_move_multi(player, closest_blocker, state)
                if result and result.shed:
                    state.shed_players[player.id] = state.tick
                    return

            elif state.tick % 25 == 0 and can_attempt:
                if not hasattr(state, '_last_move_tick'):
                    state._last_move_tick = {}
                state._last_move_tick[player.id] = state.tick

                result = _attempt_pass_rush_move_multi(player, closest_blocker, state)
                if result and result.shed:
                    state.shed_players[player.id] = state.tick
                    return

            # Push toward target
            to_target = target - player.position
            if to_target.length() > 0.1:
                player.drive_step(to_target.normalized())
                if player.can_generate_power:
                    speed = 2.0 if player.has_inside_hands else 1.0
                    player.velocity = to_target.normalized() * speed

        elif closest_blocker:
            # Approaching
            player.drive_step((target - player.position).normalized())
            player.move_toward(target, speed=3.0)
        else:
            # Unblocked! Sprint
            player.move_toward(target, speed=5.0)


def _attempt_pass_rush_move_multi(rusher: Player, blocker: Player, state) -> Optional:
    """Pass rush move in multi-player context."""
    from .simulation import _attempt_pass_rush_move
    return _attempt_pass_rush_move(rusher, blocker, state)


# =============================================================================
# Scenario Factories
# =============================================================================

def create_double_team_scenario(
    dl_attrs: PhysicalAttributes = None,
    post_attrs: PhysicalAttributes = None,
    drive_attrs: PhysicalAttributes = None,
    pocket_time: float = 3.5,
) -> MultiPlayerSimulation:
    """
    Create a 2 OL vs 1 DL double team scenario.

    Returns configured simulation ready to run.
    """
    config = SimulationConfig(
        dt=0.05,
        max_ticks=int(pocket_time / 0.05),
        target_position=Vec2(0, -5),
    )

    sim = MultiPlayerSimulation(config)

    # Default attributes
    if dl_attrs is None:
        dl_attrs = PhysicalAttributes.average_dt()
    if post_attrs is None:
        post_attrs = PhysicalAttributes.average_ol()
    if drive_attrs is None:
        drive_attrs = PhysicalAttributes.average_ol()

    # Create players
    # DL lined up across from center
    dl = Player.create_lineman(
        id="DT",
        role=PlayerRole.RUSHER,
        position=Vec2(0, 1.5),  # Across LOS
        facing=-math.pi / 2,    # Facing downfield toward QB
        weight=300,
        attributes=dl_attrs,
    )

    # Post blocker (center) - at LOS, head up on DL
    post = Player.create_lineman(
        id="C",
        role=PlayerRole.BLOCKER,
        position=Vec2(0, 0),    # At LOS
        facing=math.pi / 2,     # Facing upfield toward DL
        weight=310,
        attributes=post_attrs,
    )

    # Drive blocker (guard) - at LOS, offset to the side
    drive = Player.create_lineman(
        id="LG",
        role=PlayerRole.BLOCKER,
        position=Vec2(-1.2, 0),  # At LOS, to the left
        facing=math.pi / 2,      # Facing upfield
        weight=315,
        attributes=drive_attrs,
    )

    sim.add_player(dl)
    sim.add_player(post)
    sim.add_player(drive)

    # Set up double team assignment (drive from left = +1 direction)
    sim.assignments.assign_double_team("C", "LG", "DT", drive_direction=1.0)

    # Store assignments in state for intent access
    sim.state.assignments = sim.assignments

    # Set intents using unified system
    sim.set_intent("DT", lambda p, s: multi_rusher_intent(p, s, s.assignments))
    sim.set_intent("C", make_blocker_intent(
        target_rusher_id="DT",
        block_type=BlockType.DOUBLE_POST
    ))
    sim.set_intent("LG", make_blocker_intent(
        target_rusher_id="DT",
        block_type=BlockType.DOUBLE_DRIVE,
        drive_direction=1.0
    ))

    return sim


def create_3v2_scenario(
    dt1_attrs: PhysicalAttributes = None,
    dt2_attrs: PhysicalAttributes = None,
    c_attrs: PhysicalAttributes = None,
    lg_attrs: PhysicalAttributes = None,
    rg_attrs: PhysicalAttributes = None,
    double_team_target: str = "DT1",  # Which DT to double
    pocket_time: float = 3.5,
) -> MultiPlayerSimulation:
    """
    Create a 3 OL vs 2 DL interior line scenario.

    C, LG, RG vs two DTs.
    One DT gets doubled, the other is singled.

    Args:
        dt1_attrs: Left DT attributes
        dt2_attrs: Right DT attributes
        c_attrs: Center attributes
        lg_attrs: Left Guard attributes
        rg_attrs: Right Guard attributes
        double_team_target: "DT1" or "DT2" - who gets doubled
        pocket_time: How long until timeout
    """
    config = SimulationConfig(
        dt=0.05,
        max_ticks=int(pocket_time / 0.05),
        target_position=Vec2(0, -5),
    )

    sim = MultiPlayerSimulation(config)

    # Default to average if not specified
    if dt1_attrs is None:
        dt1_attrs = PhysicalAttributes.average_dt()
    if dt2_attrs is None:
        dt2_attrs = PhysicalAttributes.average_dt()
    if c_attrs is None:
        c_attrs = PhysicalAttributes.average_ol()
    if lg_attrs is None:
        lg_attrs = PhysicalAttributes.average_ol()
    if rg_attrs is None:
        rg_attrs = PhysicalAttributes.average_ol()

    # Create DTs - lined up across the LOS
    # DT1 on left side (in LG-C gap)
    dt1 = Player.create_lineman(
        id="DT1",
        role=PlayerRole.RUSHER,
        position=Vec2(-0.6, 1.5),   # Across LOS, left A-gap
        facing=-math.pi / 2,         # Facing downfield
        weight=300,
        attributes=dt1_attrs,
    )

    # DT2 on right side (in C-RG gap)
    dt2 = Player.create_lineman(
        id="DT2",
        role=PlayerRole.RUSHER,
        position=Vec2(0.6, 1.5),    # Across LOS, right A-gap
        facing=-math.pi / 2,         # Facing downfield
        weight=300,
        attributes=dt2_attrs,
    )

    # Create OL - at the LOS
    center = Player.create_lineman(
        id="C",
        role=PlayerRole.BLOCKER,
        position=Vec2(0, 0),         # At LOS, center
        facing=math.pi / 2,          # Facing upfield
        weight=310,
        attributes=c_attrs,
    )

    lg = Player.create_lineman(
        id="LG",
        role=PlayerRole.BLOCKER,
        position=Vec2(-1.2, 0),      # At LOS, left of center
        facing=math.pi / 2,          # Facing upfield
        weight=315,
        attributes=lg_attrs,
    )

    rg = Player.create_lineman(
        id="RG",
        role=PlayerRole.BLOCKER,
        position=Vec2(1.2, 0),       # At LOS, right of center
        facing=math.pi / 2,          # Facing upfield
        weight=315,
        attributes=rg_attrs,
    )

    sim.add_player(dt1)
    sim.add_player(dt2)
    sim.add_player(center)
    sim.add_player(lg)
    sim.add_player(rg)

    # Set up assignments
    if double_team_target == "DT1":
        # LG + C double DT1, RG singles DT2
        sim.assignments.assign_double_team("C", "LG", "DT1", drive_direction=-1.0)
        sim.assignments.assign_single_block("RG", "DT2")
    else:
        # C + RG double DT2, LG singles DT1
        sim.assignments.assign_double_team("C", "RG", "DT2", drive_direction=1.0)
        sim.assignments.assign_single_block("LG", "DT1")

    # Store assignments in state for intent access
    sim.state.assignments = sim.assignments

    # Set intents using unified system
    sim.set_intent("DT1", lambda p, s: multi_rusher_intent(p, s, s.assignments))
    sim.set_intent("DT2", lambda p, s: multi_rusher_intent(p, s, s.assignments))

    if double_team_target == "DT1":
        # C is POST on DT1, LG is DRIVE on DT1, RG singles DT2
        sim.set_intent("C", make_blocker_intent(
            target_rusher_id="DT1",
            block_type=BlockType.DOUBLE_POST
        ))
        sim.set_intent("LG", make_blocker_intent(
            target_rusher_id="DT1",
            block_type=BlockType.DOUBLE_DRIVE,
            drive_direction=-1.0
        ))
        sim.set_intent("RG", make_blocker_intent(
            target_rusher_id="DT2",
            block_type=BlockType.SINGLE
        ))
    else:
        # C is POST on DT2, RG is DRIVE on DT2, LG singles DT1
        sim.set_intent("C", make_blocker_intent(
            target_rusher_id="DT2",
            block_type=BlockType.DOUBLE_POST
        ))
        sim.set_intent("RG", make_blocker_intent(
            target_rusher_id="DT2",
            block_type=BlockType.DOUBLE_DRIVE,
            drive_direction=1.0
        ))
        sim.set_intent("LG", make_blocker_intent(
            target_rusher_id="DT1",
            block_type=BlockType.SINGLE
        ))

    return sim
