"""
Core simulation loop for the arms prototype.

Supports both 1v1 and multi-player (double teams, 3v2, etc.) scenarios.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Optional, TYPE_CHECKING
import math
import random

from .vec2 import Vec2
from .player import Player, PlayerRole
from .arm import ArmSide, HandState
from .collision import (
    detect_hand_on_body,
    detect_body_collision,
    resolve_body_collision,
    resolve_hand_fighting,
    resolve_double_team,
    can_split_double,
    HandContact,
)
from .moves import (
    attempt_swim,
    attempt_rip,
    attempt_bull_rush,
    attempt_club,
    attempt_spin,
    attempt_anchor,
    attempt_punch_reset,
    attempt_hand_fight,
    attempt_steer,
    MoveResult,
)
from .assignments import AssignmentTracker, BlockType


@dataclass
class SimulationState:
    """Current state of the simulation."""
    tick: int = 0
    time: float = 0.0
    players: Dict[str, Player] = field(default_factory=dict)
    engagements: List[tuple[str, str]] = field(default_factory=list)  # Pairs of engaged player IDs

    # Shed tracking - rusher IDs who have beaten their block
    shed_players: Dict[str, int] = field(default_factory=dict)  # player_id -> tick when shed

    # Redirect tracking - blocker steering a shed rusher
    # Format: {rusher_id: (outward_dir, strength)} where strength is 0-1
    active_redirects: Dict[str, tuple[Vec2, float]] = field(default_factory=dict)

    # Outcome tracking
    rusher_reached_target: bool = False
    blocker_held: bool = False


@dataclass
class SimulationConfig:
    """Configuration for the simulation."""
    dt: float = 0.05  # 50ms ticks (20 Hz)
    max_ticks: int = 200  # 10 seconds max
    target_position: Vec2 = field(default_factory=lambda: Vec2(0, -5))  # Where rusher wants to go


class Simulation:
    """
    The main simulation runner.

    Handles the physics loop, collision detection, and player updates.
    Works for both 1v1 and multi-player scenarios.
    """

    def __init__(self, config: Optional[SimulationConfig] = None):
        self.config = config or SimulationConfig()
        self.state = SimulationState()
        self._player_intents: Dict[str, Callable[[Player, SimulationState], None]] = {}
        # Optional assignments for multi-player (double teams, etc.)
        self._assignments: Optional[AssignmentTracker] = None

    @property
    def assignments(self) -> Optional[AssignmentTracker]:
        return self._assignments

    def set_assignments(self, assignments: AssignmentTracker) -> None:
        """Set blocking assignments for multi-player scenarios."""
        self._assignments = assignments

    def add_player(self, player: Player) -> None:
        """Add a player to the simulation."""
        self.state.players[player.id] = player

    def set_intent(self, player_id: str,
                   intent_fn: Callable[[Player, SimulationState], None]) -> None:
        """
        Set the AI/intent function for a player.

        The intent function is called each tick to determine what the player
        is trying to do (reach, punch, move, etc.).
        """
        self._player_intents[player_id] = intent_fn

    def tick(self) -> bool:
        """
        Run one simulation tick.

        Returns True if simulation should continue, False if complete.

        Note: Double team handling is done in MultiPlayerSimulation.tick()
        which calls this via super().tick(). The parent class handles only
        core 1v1 physics.
        """
        dt = self.config.dt

        # 1. Run player intents (AI decisions)
        for player_id, intent_fn in self._player_intents.items():
            if player_id in self.state.players:
                intent_fn(self.state.players[player_id], self.state)

        # 1.5 Apply redirects AFTER all intents have set velocities
        # This ensures the OL can steer the DL even though DL intent wants to go to QB
        for player_id, (outward_dir, strength) in self.state.active_redirects.items():
            if player_id in self.state.players:
                player = self.state.players[player_id]
                target = self.config.target_position

                # DL's desired direction (to QB)
                to_target = target - player.position
                if to_target.length() > 0.01:
                    to_target_norm = to_target.normalized()
                else:
                    continue

                # Blend: DL wants to go to QB, OL is pushing outward
                # strength is 0-1 based on contact distance
                redirect_blend = 0.5 * strength  # Up to 50% redirect at full contact

                # New direction is blend of QB direction and outward push
                new_dir = to_target_norm * (1.0 - redirect_blend) + outward_dir * redirect_blend
                if new_dir.length() > 0.01:
                    new_dir = new_dir.normalized()

                # Apply: maintain speed but change direction, and slow down a bit
                speed = player.velocity.length()
                player.velocity = new_dir * speed * 0.85  # Also slow them down (contact resistance)

        # 2. Detect all contacts
        players = list(self.state.players.values())
        all_hand_contacts: Dict[str, List[HandContact]] = {p.id: [] for p in players}

        for i, player_a in enumerate(players):
            for player_b in players[i + 1:]:
                # Skip hand fighting if either player has shed their block
                # (they're disengaged and running free)
                a_shed = player_a.id in self.state.shed_players
                b_shed = player_b.id in self.state.shed_players

                if not (a_shed or b_shed):
                    # Hand-on-body contacts only when engaged
                    a_on_b = detect_hand_on_body(player_a, player_b)
                    b_on_a = detect_hand_on_body(player_b, player_a)

                    all_hand_contacts[player_a.id].extend(a_on_b)
                    all_hand_contacts[player_b.id].extend(b_on_a)

                    # Resolve hand fighting if there are contacts
                    if a_on_b or b_on_a:
                        resolve_hand_fighting(player_a, player_b, a_on_b, b_on_a, dt)

                # Body collisions still happen (can't run through each other)
                # But only apply separation, not momentum transfer when shed
                body_contact = detect_body_collision(player_a, player_b)
                if body_contact:
                    if a_shed or b_shed:
                        # Just separate, don't transfer momentum
                        if body_contact.penetration > 0:
                            separation = body_contact.normal * (body_contact.penetration / 2 + 0.01)
                            player_a.position = player_a.position - separation
                            player_b.position = player_b.position + separation
                    else:
                        resolve_body_collision(player_a, player_b, body_contact, dt)

        # 3. Apply physics updates
        for player in players:
            # Apply friction/drag
            player.velocity = player.velocity * 0.95

            # Blockers resist lateral movement when engaged (anchor)
            # But this is a physical battle - can't just ignore forces
            if player.role == PlayerRole.BLOCKER and player.is_engaged:
                # Project velocity onto the target direction
                to_target = self.config.target_position - player.position
                if to_target.length() > 0.01:
                    forward = to_target.normalized()
                    forward_speed = player.velocity.dot(forward)
                    lateral = player.velocity - forward * forward_speed

                    # Lateral resistance based on balance and pad level
                    # Good balance + low pad level = strong anchor
                    anchor_strength = player.body.balance * player.body.leverage_factor
                    lateral_resistance = 0.3 + 0.5 * anchor_strength  # 0.3 to 0.8

                    # Allow some lateral movement, resist based on anchor strength
                    player.velocity = forward * forward_speed + lateral * (1.0 - lateral_resistance)

            # Clamp velocities
            max_speed = 5.0  # yards/second for linemen
            if player.velocity.length() > max_speed:
                player.velocity = player.velocity.normalized() * max_speed

            # Update player physics
            player.update(dt)

            # Recover balance over time if not engaged
            if not player.is_engaged:
                player.body.balance = min(1.0, player.body.balance + 0.1 * dt)

        # 4. Check end conditions
        self.state.tick += 1
        self.state.time += dt

        # Check if rusher reached target
        for player in players:
            if player.role == PlayerRole.RUSHER:
                dist_to_target = player.position.distance_to(self.config.target_position)
                if dist_to_target < 1.0:
                    self.state.rusher_reached_target = True
                    return False

        # Time limit
        if self.state.tick >= self.config.max_ticks:
            self.state.blocker_held = True
            return False

        return True

    def run(self) -> SimulationState:
        """Run the simulation to completion."""
        while self.tick():
            pass
        return self.state

    def get_frame_data(self) -> dict:
        """Get current state as a dictionary for visualization."""
        frame = {
            "tick": self.state.tick,
            "time": self.state.time,
            "players": {},
        }

        for player_id, player in self.state.players.items():
            # Get foot world positions
            left_foot_pos = player.feet.left.position
            right_foot_pos = player.feet.right.position

            frame["players"][player_id] = {
                "position": {"x": player.position.x, "y": player.position.y},
                "facing": player.facing,
                "pad_level": player.body.pad_level,
                "balance": player.body.balance,
                "left_hand": {
                    "x": player.left_hand_pos.x,
                    "y": player.left_hand_pos.y,
                    "state": player.arms.left.hand_state.value,
                },
                "right_hand": {
                    "x": player.right_hand_pos.x,
                    "y": player.right_hand_pos.y,
                    "state": player.arms.right.hand_state.value,
                },
                "left_shoulder": {
                    "x": player.left_shoulder.x,
                    "y": player.left_shoulder.y,
                },
                "right_shoulder": {
                    "x": player.right_shoulder.x,
                    "y": player.right_shoulder.y,
                },
                "left_foot": {
                    "x": left_foot_pos.x,
                    "y": left_foot_pos.y,
                    "phase": player.feet.left.phase.value,
                    "weight": player.feet.left.weight,
                    "cycle_progress": player.feet.left.cycle_progress,
                    "step_target": {
                        "x": player.feet.left.step_target.x,
                        "y": player.feet.left.step_target.y,
                    } if player.feet.left.step_target else None,
                },
                "right_foot": {
                    "x": right_foot_pos.x,
                    "y": right_foot_pos.y,
                    "phase": player.feet.right.phase.value,
                    "weight": player.feet.right.weight,
                    "cycle_progress": player.feet.right.cycle_progress,
                    "step_target": {
                        "x": player.feet.right.step_target.x,
                        "y": player.feet.right.step_target.y,
                    } if player.feet.right.step_target else None,
                },
                "force_debt": {
                    "x": player.feet.force_debt.x,
                    "y": player.feet.force_debt.y,
                    "magnitude": player.feet.force_debt.length(),
                },
                "stance_width": player.feet.width,
                "stance_balance": player.feet.balance_factor,
                "role": player.role.value,
            }

        return frame


# =============================================================================
# Unified AI Intents - Work for both 1v1 and multi-player
# =============================================================================

def make_blocker_intent(
    target_rusher_id: Optional[str] = None,
    block_type: Optional[BlockType] = None,
    drive_direction: float = 1.0
) -> Callable[[Player, SimulationState], None]:
    """
    Factory function to create a blocker intent.

    Args:
        target_rusher_id: Specific rusher to block (None = find any rusher)
        block_type: DOUBLE_POST, DOUBLE_DRIVE, or SINGLE (None = 1v1 behavior)
        drive_direction: For DOUBLE_DRIVE, which way to push (-1 or 1)

    Returns:
        An intent function that can be passed to sim.set_intent()
    """
    def intent(player: Player, state: SimulationState) -> None:
        _blocker_intent_core(player, state, target_rusher_id, block_type, drive_direction)
    return intent


def blocker_intent(player: Player, state: SimulationState) -> None:
    """
    Default OL intent for 1v1: Finds any rusher and blocks them.
    For multi-player, use make_blocker_intent() to specify targets.
    """
    _blocker_intent_core(player, state, None, None, 1.0)


def _blocker_intent_core(
    player: Player,
    state: SimulationState,
    target_rusher_id: Optional[str],
    block_type: Optional[BlockType],
    drive_direction: float
) -> None:
    """
    Core blocker logic - same for 1v1 and multi-player.

    Real pass pro technique:
    1. Give ground backward to absorb force (pocket naturally forms)
    2. Mirror rusher laterally to stay in front
    3. When beaten, redirect rusher outward (make them take the long way)
    """
    # Find the rusher (specific target or any rusher)
    rusher = None
    if target_rusher_id:
        rusher = state.players.get(target_rusher_id)
    else:
        for p in state.players.values():
            if p.role == PlayerRole.RUSHER:
                rusher = p
                break

    if not rusher:
        return

    target = Vec2(0, -5)  # QB position

    # Check if rusher has shed us (gotten past)
    if rusher.id in state.shed_players:
        # We've been beat! Try to redirect them outward
        player.face_toward(rusher.position)

        # Push them toward the sideline, not toward QB
        rusher_x = rusher.position.x
        outward_dir = Vec2(1.0 if rusher_x >= 0 else -1.0, 0)  # Push toward nearest sideline

        dist_to_rusher = player.position.distance_to(rusher.position)
        if dist_to_rusher < 2.0:
            # Close enough to influence - get hands on them
            player.reach_both_toward(rusher.body.chest_center)

            # OL moves toward rusher to maintain contact
            to_rusher = (rusher.position - player.position).normalized()
            player.velocity = to_rusher * 3.0 + outward_dir * 1.0

            # Register redirect - will be applied in physics step after all intents
            contact_strength = 1.0 - (dist_to_rusher / 2.0)  # 1.0 at contact, 0 at 2yds
            state.active_redirects[rusher.id] = (outward_dir, contact_strength)

            # If we re-engage properly, remove shed status
            if player.is_engaged and dist_to_rusher < 1.0:
                del state.shed_players[rusher.id]
                if rusher.id in state.active_redirects:
                    del state.active_redirects[rusher.id]
        else:
            # Too far for contact - clear redirect
            if rusher.id in state.active_redirects:
                del state.active_redirects[rusher.id]

            if dist_to_rusher < 3.0:
                # Close-ish - sprint to cut off angle to QB
                to_qb = target - rusher.position
                intercept_point = rusher.position + to_qb.normalized() * 1.5
                player.move_toward(intercept_point, speed=4.5)
            else:
                # Too far - just chase, probably won't catch them
                player.move_toward(rusher.position, speed=4.0)
        return

    # Face the rusher
    player.face_toward(rusher.position)
    dist_to_rusher = player.position.distance_to(rusher.position)

    # Vector from player to QB (retreat direction)
    to_qb = target - player.position
    to_qb_norm = to_qb.normalized() if to_qb.length() > 0.1 else Vec2(0, -1)

    # Vector from player to rusher
    to_rusher = rusher.position - player.position
    to_rusher_norm = to_rusher.normalized() if to_rusher.length() > 0.1 else Vec2(0, 1)

    # === ENGAGED BLOCKING ===
    if dist_to_rusher < 2.0:
        # Punch to establish hand control
        if not player.is_engaged:
            player.punch_both()
            player.lower_pad_level(0.05)

        # Stay low to match rusher
        if rusher.body.pad_level < player.body.pad_level:
            player.lower_pad_level(0.02)

        # Hand target - DRIVE blocker aims at outside shoulder, others at center
        if block_type == BlockType.DOUBLE_DRIVE:
            outside_shoulder = rusher.position + Vec2(drive_direction * 0.25, 0)
            player.reach_both_toward(outside_shoulder)
        else:
            player.reach_both_toward(rusher.body.chest_center)

        force_debt = player.feet.force_debt.length()

        # === DOUBLE TEAM: RUN BLOCKING LOGIC ===
        # Per coaching book: "Work hip-to-hip as they sweep the defensive lineman upfield"
        # Run blocking drives INTO the defender, unlike pass pro which retreats
        #
        # The resolve_double_team() function in collision.py handles the physics
        # (velocity, force generation). Here we just set up the intent (stance, steps).
        if block_type in (BlockType.DOUBLE_POST, BlockType.DOUBLE_DRIVE):
            upfield = Vec2(0, 1)  # Positive Y is upfield toward DL side

            # Drive step INTO the rusher - establish forward momentum
            if player.can_generate_power:
                drive_dir = (to_rusher_norm * 0.6 + upfield * 0.4).normalized()
                player.drive_step(drive_dir)

            # Stay very low for maximum drive power
            player.lower_pad_level(0.03)

            # POST blocker: square up and anchor
            # DRIVE blocker: work to seal the playside
            if block_type == BlockType.DOUBLE_DRIVE:
                seal_dir = Vec2(drive_direction * 0.3, 0.7).normalized()
                player.drive_step(seal_dir)

            return  # Skip pass pro logic - collision.py handles velocity

        # === OL COUNTER-MOVES ===
        # Track last counter attempt to prevent spamming
        import random
        last_counter_tick = getattr(state, '_ol_last_counter', {}).get(player.id, -100)
        can_attempt_counter = (state.tick - last_counter_tick) >= 12  # 0.6 second cooldown

        if can_attempt_counter:
            # Assess situation and choose counter
            ol_has_inside = player.has_inside_hands
            dl_has_inside = rusher.has_inside_hands
            under_heavy_pressure = force_debt > 0.3

            result = None

            if under_heavy_pressure:
                # Under heavy pressure - ANCHOR
                result = attempt_anchor(player, rusher)
                if hasattr(state, '_verbose') and state._verbose:
                    print(f"  [Counter] {result.description}")

            elif dl_has_inside and not ol_has_inside:
                # DL winning hands - try to reset or fight back
                if random.random() < 0.6:
                    result = attempt_punch_reset(player, rusher)
                else:
                    arm_side = random.choice([ArmSide.LEFT, ArmSide.RIGHT])
                    result = attempt_hand_fight(player, rusher, arm_side)
                if hasattr(state, '_verbose') and state._verbose:
                    print(f"  [Counter] {result.description}")

            elif ol_has_inside and random.random() < 0.3:
                # OL has control - can try to steer
                rusher_x = rusher.position.x
                direction = "outside" if rusher_x >= 0 else "inside"
                result = attempt_steer(player, rusher, direction)
                if hasattr(state, '_verbose') and state._verbose:
                    print(f"  [Counter] {result.description}")

            elif not ol_has_inside and not dl_has_inside and random.random() < 0.4:
                # Contested - fight for hands
                arm_side = random.choice([ArmSide.LEFT, ArmSide.RIGHT])
                result = attempt_hand_fight(player, rusher, arm_side)
                if hasattr(state, '_verbose') and state._verbose:
                    print(f"  [Counter] {result.description}")

            if result:
                if not hasattr(state, '_ol_last_counter'):
                    state._ol_last_counter = {}
                state._ol_last_counter[player.id] = state.tick

        # === CONTROLLED RETREAT ===
        # Give ground toward QB to absorb force - this forms the pocket
        if force_debt > 0.1:
            # Under pressure - give ground backward to absorb
            retreat_step = to_qb_norm * 0.3
            player.kick_step(retreat_step)

            # Allow some backward velocity (controlled give)
            backward_speed = min(1.5, force_debt * 3.0)
            player.velocity = to_qb_norm * backward_speed

        else:
            # Low pressure - hold ground, mirror laterally
            rusher_lateral = rusher.velocity.x
            if abs(rusher_lateral) > 0.5:
                mirror_step = Vec2(rusher_lateral * 0.3, 0)
                player.kick_step(mirror_step)

        # Don't retreat past a certain point (protect the QB)
        dist_to_qb = player.position.distance_to(target)
        if dist_to_qb < 2.0:
            # Getting too close to QB - must anchor here
            player.velocity = player.velocity * 0.3

    # === PRE-ENGAGEMENT ===
    elif dist_to_rusher < 3.0:
        # Rusher approaching - step to meet them
        player.kick_step(to_rusher_norm)
        player.lower_pad_level(0.03)

    else:
        # Rusher far - hold position
        player.set_feet()


def rusher_intent(player: Player, state: SimulationState) -> None:
    """
    DL intent: Generate force toward target, disrupt blocker's balance.

    The feet system handles continuous stepping. Our job is to:
    - Apply pressure toward the QB
    - Work for hand position
    - Attack when blocker's force debt is high
    """
    import random

    target = Vec2(0, -5)  # QB position

    # Check if we've already shed our block
    if player.id in state.shed_players:
        # We're free! Sprint to QB
        player.face_toward(target)
        player.move_toward(target, speed=5.0)
        player.retract_arms()
        return

    # Find the blocker
    blocker = None
    for p in state.players.values():
        if p.role == PlayerRole.BLOCKER:
            blocker = p
            break

    # Face the target (QB)
    player.face_toward(target)

    if blocker:
        dist_to_blocker = player.position.distance_to(blocker.position)

        if dist_to_blocker < 2.0:
            # === ENGAGED ===

            # Initial punch to establish hands
            if not player.is_engaged:
                player.punch_both()
                player.lower_pad_level(0.05)

            # Try to get inside hands on blocker's chest
            player.reach_both_toward(blocker.body.chest_center)

            # === READ THE BLOCKER ===
            # Blocker compromised when their force debt is high
            blocker_compromised = blocker.feet.force_debt.length() > 0.3

            # Track last move attempt to prevent spamming
            last_move_tick = getattr(state, '_last_move_tick', {}).get(player.id, -100)
            can_attempt_move = (state.tick - last_move_tick) >= 15  # 0.75 second cooldown

            if blocker_compromised and can_attempt_move:
                # Blocker is vulnerable - try a move NOW
                if not hasattr(state, '_last_move_tick'):
                    state._last_move_tick = {}
                state._last_move_tick[player.id] = state.tick

                result = _attempt_pass_rush_move(player, blocker, state)
                if result:
                    if hasattr(state, '_verbose') and state._verbose:
                        print(f"  [Move] {result.description}")
                    if result.shed:
                        state.shed_players[player.id] = state.tick
                        return
            elif state.tick % 25 == 0 and state.tick > 0 and can_attempt_move:
                # Regular move attempt
                result = _attempt_pass_rush_move(player, blocker, state)
                if result:
                    if hasattr(state, '_verbose') and state._verbose:
                        print(f"  [Move] {result.description}")
                    if result.shed:
                        state.shed_players[player.id] = state.tick
                        return

            # === PRESSURE TOWARD TARGET ===
            # Always driving toward QB - this creates force on blocker
            to_target = target - player.position
            if to_target.length() > 0.1:
                # Drive step toward target
                player.drive_step(to_target.normalized())

                # Apply velocity toward target when we can generate power
                if player.can_generate_power:
                    speed = 2.0 if player.has_inside_hands else 1.0
                    player.velocity = to_target.normalized() * speed

            # Lateral pressure to stress blocker's base
            if state.tick % 40 < 20:
                lateral = Vec2(0.2, 0)
            else:
                lateral = Vec2(-0.2, 0)
            # Add lateral component to velocity
            player.velocity = player.velocity + lateral

        else:
            # === APPROACHING ===
            # Close distance aggressively
            to_target = target - player.position
            player.drive_step(to_target.normalized())
            player.move_toward(target, speed=3.0)

    else:
        # No blocker - sprint to target
        player.move_toward(target, speed=4.0)


def _attempt_pass_rush_move(rusher: Player, blocker: Player, state: SimulationState) -> MoveResult:
    """
    Choose and attempt a pass rush move based on player's attributes AND situation.

    Key insight: Different players have different "move arsenals" based on their
    physical profile:
    - High STR players: Bull rush, club (power moves)
    - High AGI players: Swim, spin, rip (finesse moves)
    - Balanced: Situational selection

    For DTs (interior linemen), power moves dominate.
    For edge rushers, finesse moves matter more.
    """
    import random

    # Assess the situation
    has_inside = rusher.has_inside_hands
    blocker_high = blocker.body.pad_level > 0.5
    rusher_lighter = rusher.body.dimensions.mass < blocker.body.dimensions.mass

    # === PLAYER PROFILE DETERMINES MOVE ARSENAL ===
    # Calculate power vs finesse tendency from attributes
    str_rating = rusher.attributes.strength
    agi_rating = rusher.attributes.agility

    # Power tendency: high STR relative to AGI = power player
    # Range: 0 (pure finesse) to 1 (pure power)
    power_tendency = str_rating / (str_rating + agi_rating + 1)  # +1 to avoid div by zero
    finesse_tendency = 1.0 - power_tendency

    # Debug info
    if hasattr(state, '_verbose') and state._verbose:
        print(f"  [{rusher.id}] STR={str_rating:.0f} AGI={agi_rating:.0f} -> power={power_tendency:.2f} finesse={finesse_tendency:.2f}")

    # Weight moves based on BOTH player profile AND situation
    moves = {}

    # === FINESSE MOVES (AGI-heavy) ===
    # Swim - requires arm length and speed
    swim_base = 0.15 * finesse_tendency  # Finesse players prefer swim
    if blocker_high:
        swim_base += 0.25  # Situational bonus
    moves["swim"] = swim_base

    # Rip - balanced but requires some finesse
    rip_base = 0.15 + 0.15 * finesse_tendency
    if rusher.body.pad_level < 0.4:
        rip_base += 0.2  # Situational bonus for being low
    moves["rip"] = rip_base

    # Spin - high risk, pure finesse
    spin_base = 0.05 * finesse_tendency  # Only finesse players really spin
    if blocker.velocity.length() > 1.0:
        spin_base += 0.15  # Blocker over-committed
    moves["spin"] = spin_base

    # === POWER MOVES (STR-heavy) ===
    # Bull rush - pure power
    bull_base = 0.15 * power_tendency  # Power players prefer bull
    if not rusher_lighter and has_inside:
        bull_base += 0.3  # Situational bonus
    elif has_inside:
        bull_base += 0.15
    moves["bull"] = bull_base

    # Club - power move to reset hands
    club_base = 0.15 + 0.15 * power_tendency
    moves["club"] = club_base

    # Ensure all moves have minimum chance (anyone CAN try anything)
    for move in moves:
        moves[move] = max(0.05, moves[move])

    # Normalize weights and pick
    total_weight = sum(moves.values())
    r = random.random() * total_weight
    cumulative = 0

    chosen_move = "bull"  # default
    for move, weight in moves.items():
        cumulative += weight
        if r < cumulative:
            chosen_move = move
            break

    # Execute the move
    arm_side = random.choice([ArmSide.LEFT, ArmSide.RIGHT])

    if chosen_move == "swim":
        return attempt_swim(rusher, blocker, arm_side)
    elif chosen_move == "rip":
        return attempt_rip(rusher, blocker, arm_side)
    elif chosen_move == "club":
        return attempt_club(rusher, blocker, arm_side)
    elif chosen_move == "spin":
        direction = "inside" if random.random() < 0.6 else "outside"
        return attempt_spin(rusher, blocker, direction)
    elif chosen_move == "bull":
        return attempt_bull_rush(rusher, blocker)

    return MoveResult(success=False, description="No move attempted")
