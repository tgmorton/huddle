"""
Pass rush and blocking moves.

These are techniques that change the hand fighting dynamic.

Attributes affect move success:
- STR: Power moves (bull rush, club), resistance to being moved
- AGI: Finesse moves (swim, rip, spin), hand speed for counters
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import math
import random

from .vec2 import Vec2
from .player import Player
from .arm import ArmSide, HandState


class MoveType(str, Enum):
    """Pass rush moves."""
    BULL_RUSH = "bull_rush"     # Power through with both hands (STR heavy)
    SWIM = "swim"               # Arm over the top (AGI heavy)
    RIP = "rip"                 # Arm underneath (balanced)
    CLUB = "club"               # Knock hands away (STR heavy)
    SPIN = "spin"               # Spin around blocker (AGI heavy)
    SPEED_RUSH = "speed_rush"   # Wide arc around edge (AGI heavy)
    SPEED_TO_POWER = "speed_to_power"  # Threaten outside, come inside (balanced)
    GHOST = "ghost"             # Avoid contact entirely (AGI heavy)
    LONG_ARM = "long_arm"       # Keep blocker at distance (STR/reach)


class BlockingCounter(str, Enum):
    """Blocking counters to moves."""
    ANCHOR = "anchor"           # Sink hips, absorb bull (STR)
    MIRROR = "mirror"           # Slide with rusher (AGI)
    PUNCH_RESET = "punch_reset" # Re-establish hands (AGI)
    HAND_FIGHT = "hand_fight"   # Active hand fighting (balanced)
    STEER = "steer"             # Redirect rusher (STR)


@dataclass
class MoveResult:
    """Result of attempting a move."""
    success: bool
    description: str
    shed: bool = False          # Did rusher get free?
    advantage: float = 0.0      # Position advantage gained (-1 to 1)


def attempt_swim(rusher: Player, blocker: Player, arm_side: ArmSide) -> MoveResult:
    """
    Swim move: Throw arm over blocker's shoulder, rip through.

    AGI-heavy move. Success depends on:
    - Rusher's AGI (hand speed to execute)
    - Rusher's arm length vs blocker's
    - Blocker's pad level (high = vulnerable)
    - Blocker's AGI (reaction speed)
    """
    arm = rusher.arms.get_arm(arm_side)
    other_arm = rusher.arms.get_arm(
        ArmSide.RIGHT if arm_side == ArmSide.LEFT else ArmSide.LEFT
    )

    # Base success rate
    success_rate = 0.12

    # AGI comparison is key for swim (hand speed battle)
    agi_diff = rusher.attributes.agility - blocker.attributes.agility
    success_rate += agi_diff / 100 * 0.25  # Up to +/-25%

    # Arm length advantage
    length_diff = rusher.body.dimensions.arm_length - blocker.body.dimensions.arm_length
    success_rate += length_diff * 0.3

    # Blocker pad level (high = easier to swim over)
    success_rate += (blocker.body.pad_level - 0.5) * 0.25

    # Hand position
    if arm.hand_state == HandState.CONTROLLING:
        success_rate += 0.1

    blocker_arm = blocker.arms.get_arm(
        ArmSide.RIGHT if arm_side == ArmSide.LEFT else ArmSide.LEFT
    )
    if blocker_arm.hand_state == HandState.CONTROLLING:
        success_rate -= 0.25

    success_rate = max(0.05, min(0.5, success_rate))

    if random.random() < success_rate:
        # Success! Disengage arm, gain advantage
        arm.hand_state = HandState.FREE
        arm.disengage()
        other_arm.disengage()

        # Move rusher past blocker
        side_desc = "left" if arm_side == ArmSide.LEFT else "right"
        return MoveResult(
            success=True,
            description=f"Beautiful swim move! {rusher.id} throws his {side_desc} arm over and rips through.",
            shed=True,
            advantage=0.5,
        )
    else:
        # Failed - blocker maintained position
        return MoveResult(
            success=False,
            description=f"{rusher.id} tries a swim but {blocker.id} stays square and mirrors.",
            shed=False,
            advantage=-0.1,  # Lost ground
        )


def attempt_rip(rusher: Player, blocker: Player, arm_side: ArmSide) -> MoveResult:
    """
    Rip move: Drive arm underneath blocker's arm and through.

    Balanced STR/AGI move. Success depends on:
    - Rusher's pad level (low = better)
    - Rusher's STR (power to drive through)
    - Rusher's AGI (quickness of execution)
    - Blocker's arm extension (extended = vulnerable)
    """
    arm = rusher.arms.get_arm(arm_side)

    # Base success rate
    success_rate = 0.10

    # Balanced STR + AGI (rip needs both)
    power_rating = rusher.attributes.power_rating
    success_rate += (power_rating - 1.0) * 0.15  # +/-15% based on power

    # Rusher pad level (low is good for rip)
    success_rate += (0.5 - rusher.body.pad_level) * 0.25

    # Blocker arm extension (over-extended = vulnerable)
    blocker_arm = blocker.arms.get_arm(
        ArmSide.RIGHT if arm_side == ArmSide.LEFT else ArmSide.LEFT
    )
    if blocker_arm.extension > 0.7:
        success_rate += 0.15

    # Blocker strength resists
    success_rate -= (blocker.attributes.str_resistance_mult - 1.0) * 0.1

    success_rate = max(0.05, min(0.45, success_rate))

    if random.random() < success_rate:
        arm.hand_state = HandState.FREE
        arm.disengage()

        side_desc = "left" if arm_side == ArmSide.LEFT else "right"
        return MoveResult(
            success=True,
            description=f"Violent rip! {rusher.id} drives his {side_desc} arm under and through, breaking free.",
            shed=True,
            advantage=0.4,
        )
    else:
        return MoveResult(
            success=False,
            description=f"{rusher.id} tries to rip under but {blocker.id} keeps his hands inside.",
            shed=False,
            advantage=-0.1,
        )


def attempt_bull_rush(rusher: Player, blocker: Player) -> MoveResult:
    """
    Bull rush: Drive straight through with power.

    STR-heavy move. Success depends on:
    - Rusher's STR vs blocker's STR (pure power battle)
    - Pad level (low wins)
    - Inside hand position
    """
    # Base success rate - bull rush rarely defeats a set blocker outright
    success_rate = 0.08

    # STR comparison is the main factor
    str_diff = rusher.attributes.strength - blocker.attributes.strength
    success_rate += str_diff / 100 * 0.2  # Up to +/-20%

    # Mass still matters for momentum
    mass_diff = rusher.body.dimensions.mass - blocker.body.dimensions.mass
    success_rate += mass_diff / 200 * 0.1

    # Pad level comparison (lower is better)
    pad_diff = blocker.body.pad_level - rusher.body.pad_level
    success_rate += pad_diff * 0.2

    # Inside hands critical for bull rush
    if rusher.has_inside_hands:
        success_rate += 0.15
    elif blocker.has_inside_hands:
        success_rate -= 0.15

    # Blocker's anchor rating resists bull
    success_rate -= (blocker.attributes.anchor_rating - 1.0) * 0.1

    success_rate = max(0.02, min(0.4, success_rate))

    if random.random() < success_rate:
        # Drive blocker back
        blocker.body.balance -= 0.3
        blocker.body.pad_level = min(1.0, blocker.body.pad_level + 0.2)

        return MoveResult(
            success=True,
            description=f"Power! {rusher.id} gets under {blocker.id}'s pads and drives him back into the pocket.",
            shed=False,  # Not a shed, but gaining ground
            advantage=0.3,
        )
    else:
        return MoveResult(
            success=False,
            description=f"{rusher.id} tries to bull but {blocker.id} anchors down and holds ground.",
            shed=False,
            advantage=0.0,
        )


def attempt_club(rusher: Player, blocker: Player, arm_side: ArmSide) -> MoveResult:
    """
    Club move: Knock blocker's hands away to create opening.

    STR-heavy move - raw power to swat hands away.
    """
    arm = rusher.arms.get_arm(arm_side)
    target_arm_side = ArmSide.RIGHT if arm_side == ArmSide.LEFT else ArmSide.LEFT
    blocker_arm = blocker.arms.get_arm(target_arm_side)

    # Base success rate
    success_rate = 0.40

    # STR comparison
    str_diff = rusher.attributes.strength - blocker.attributes.strength
    success_rate += str_diff / 100 * 0.2

    # AGI helps with timing
    success_rate += (rusher.attributes.agi_hand_speed - 1.0) * 0.1

    # Arm extension affects club power
    success_rate += (arm.extension - 0.3) * 0.15

    success_rate = max(0.2, min(0.7, success_rate))

    if random.random() < success_rate:
        # Knock blocker's hand away
        blocker_arm.hand_state = HandState.FREE
        blocker_arm.disengage()

        side_desc = "left" if arm_side == ArmSide.LEFT else "right"
        return MoveResult(
            success=True,
            description=f"Club! {rusher.id} swipes {blocker.id}'s {side_desc} hand away, resetting the rep.",
            shed=False,
            advantage=0.2,
        )
    else:
        return MoveResult(
            success=False,
            description=f"{rusher.id} swings for the club but {blocker.id} maintains hand placement.",
            shed=False,
            advantage=0.0,
        )


def attempt_spin(rusher: Player, blocker: Player, direction: str = "inside") -> MoveResult:
    """
    Spin move: 360 spin around blocker.

    AGI-heavy move. High risk, high reward.
    """
    # Base success rate - spin is very risky
    success_rate = 0.08

    # AGI is critical for spin (speed to complete before blocker reacts)
    success_rate += (rusher.attributes.agility - 50) / 100 * 0.2

    # Blocker AGI hurts spin (can mirror and catch you)
    success_rate -= (blocker.attributes.agility - 50) / 100 * 0.15

    # Blocker over-committed? Spin works better
    if blocker.velocity.length() > 1.0:
        success_rate += 0.12

    # Inside hands makes spin much harder
    if blocker.has_inside_hands:
        success_rate -= 0.15

    success_rate = max(0.03, min(0.35, success_rate))

    if random.random() < success_rate:
        # Complete spin, get free
        rusher.arms.left.disengage()
        rusher.arms.right.disengage()

        dir_desc = "inside" if direction == "inside" else "around the edge"
        return MoveResult(
            success=True,
            description=f"Spin move! {rusher.id} spins {dir_desc} and {blocker.id} grabs air!",
            shed=True,
            advantage=0.6,
        )
    else:
        # Caught during spin - bad position
        rusher.body.balance -= 0.2

        return MoveResult(
            success=False,
            description=f"{rusher.id} attempts a spin but {blocker.id} stays connected and rides him past the pocket.",
            shed=False,
            advantage=-0.3,
        )


# =============================================================================
# Blocking Counters - OL techniques to win hand fighting
# =============================================================================

def attempt_anchor(blocker: Player, rusher: Player) -> MoveResult:
    """
    Anchor: Sink hips, absorb bull rush.

    STR-heavy counter. Use when being bull rushed.
    """
    # Lower pad level to anchor
    blocker.lower_pad_level(0.15)

    # Anchor success based on STR
    anchor_power = blocker.attributes.anchor_rating
    balance_recovery = 0.1 + 0.1 * (anchor_power - 1.0)
    blocker.body.balance = min(1.0, blocker.body.balance + balance_recovery)

    # Reduce force debt (absorbing the pressure)
    debt_reduction = 0.3 * anchor_power
    blocker.feet.force_debt = blocker.feet.force_debt * (1.0 - debt_reduction)

    return MoveResult(
        success=True,
        description=f"{blocker.id} anchors down",
        advantage=0.1 * anchor_power,
    )


def attempt_punch_reset(blocker: Player, rusher: Player) -> MoveResult:
    """
    Punch reset: Re-establish hands after losing position.

    AGI-heavy counter. Quick hands to regain control.
    """
    blocker.punch_both()

    # AGI determines success (hand speed battle)
    base_rate = 0.35
    agi_bonus = (blocker.attributes.agi_hand_speed - 1.0) * 0.2
    agi_penalty = (rusher.attributes.agi_hand_speed - 1.0) * 0.15

    success_rate = base_rate + agi_bonus - agi_penalty

    # Hard to punch a low rusher
    success_rate += (0.5 - rusher.body.pad_level) * 0.15

    success_rate = max(0.15, min(0.65, success_rate))

    if random.random() < success_rate:
        # Reset both blocker's hands to controlling
        blocker.arms.left.hand_state = HandState.CONTROLLING
        blocker.arms.right.hand_state = HandState.CONTROLLING
        return MoveResult(
            success=True,
            description=f"{blocker.id} resets hands with a sharp punch",
            advantage=0.2,
        )
    else:
        return MoveResult(
            success=False,
            description=f"{blocker.id}'s punch reset blocked",
            advantage=-0.05,
        )


def attempt_hand_fight(blocker: Player, rusher: Player, arm_side: ArmSide) -> MoveResult:
    """
    Hand fight: Active hand battle to win inside position.

    Balanced STR/AGI. The bread and butter of OL technique.
    """
    blocker_arm = blocker.arms.get_arm(arm_side)
    rusher_arm_side = ArmSide.RIGHT if arm_side == ArmSide.LEFT else ArmSide.LEFT
    rusher_arm = rusher.arms.get_arm(rusher_arm_side)

    # Balanced attribute comparison
    blocker_power = blocker.attributes.power_rating
    rusher_power = rusher.attributes.power_rating

    # Base is 50/50, modified by power differential
    success_rate = 0.45
    power_diff = blocker_power - rusher_power
    success_rate += power_diff * 0.2

    # Current hand state matters
    if blocker_arm.hand_state == HandState.CONTROLLED:
        success_rate -= 0.15  # Hard to win from bad position
    if rusher_arm.hand_state == HandState.CONTROLLING:
        success_rate -= 0.1

    success_rate = max(0.2, min(0.7, success_rate))

    if random.random() < success_rate:
        # Win the hand battle
        blocker_arm.hand_state = HandState.CONTROLLING
        rusher_arm.hand_state = HandState.CONTROLLED

        return MoveResult(
            success=True,
            description=f"{blocker.id} wins inside hand",
            advantage=0.15,
        )
    else:
        # Lose the hand battle
        blocker_arm.hand_state = HandState.CONTROLLED
        rusher_arm.hand_state = HandState.CONTROLLING

        return MoveResult(
            success=False,
            description=f"{rusher.id} wins the hand battle",
            advantage=-0.15,
        )


def attempt_steer(blocker: Player, rusher: Player, direction: str = "outside") -> MoveResult:
    """
    Steer: Use hands to redirect rusher's path.

    STR-heavy. Requires inside hands. Used to push rusher wide.
    """
    # Must have at least one hand in control
    if not (blocker.arms.left.hand_state == HandState.CONTROLLING or
            blocker.arms.right.hand_state == HandState.CONTROLLING):
        return MoveResult(
            success=False,
            description=f"{blocker.id} can't steer without hand control",
            advantage=0.0,
        )

    # STR determines steer power
    steer_power = blocker.attributes.str_force_mult
    base_rate = 0.5

    # Rusher STR resists
    resist_factor = rusher.attributes.str_resistance_mult
    success_rate = base_rate + (steer_power - resist_factor) * 0.3

    # Better if rusher has momentum (easier to redirect)
    if rusher.velocity.length() > 1.5:
        success_rate += 0.15

    success_rate = max(0.25, min(0.75, success_rate))

    if random.random() < success_rate:
        # Apply lateral velocity to rusher
        from .vec2 import Vec2
        lateral_dir = Vec2(1.0 if direction == "outside" else -1.0, 0)
        rusher.velocity = rusher.velocity + lateral_dir * 1.5

        return MoveResult(
            success=True,
            description=f"{blocker.id} steers {rusher.id} {direction}",
            advantage=0.2,
        )
    else:
        return MoveResult(
            success=False,
            description=f"{rusher.id} fights through {blocker.id}'s steer attempt",
            advantage=-0.1,
        )


# =============================================================================
# Edge Rush Moves - Speed and finesse on the outside
# =============================================================================

def attempt_speed_rush(rusher: Player, blocker: Player, side: str = "outside") -> MoveResult:
    """
    Speed rush: Win around the edge with pure speed.

    AGI-heavy move. The bread and butter of edge rushers.
    Success depends on:
    - Rusher's AGI vs blocker's AGI (foot race)
    - Rusher's "bend" (ability to corner without losing speed)
    - Blocker's set depth (how far back they've dropped)
    - Whether blocker gets hands on

    Args:
        rusher: The edge rusher
        blocker: The OT
        side: "outside" (wide arc) or "inside" (tighter path)
    """
    from .vec2 import Vec2

    # Base success rate - speed rush is about the foot race
    success_rate = 0.15

    # AGI differential is HUGE for speed rush
    agi_diff = rusher.attributes.agility - blocker.attributes.agility
    success_rate += agi_diff / 100 * 0.35  # Up to +/-35%

    # Bend rating (use AGI as proxy for now - elite bend = high AGI)
    # Bend lets you corner without slowing down
    bend_bonus = (rusher.attributes.agility - 50) / 100 * 0.15
    success_rate += bend_bonus

    # Blocker pad level - upright = easier to run past
    if blocker.body.pad_level > 0.5:
        success_rate += 0.1

    # If blocker has hands on, much harder to speed rush
    if blocker.arms.left.hand_state == HandState.CONTROLLING:
        success_rate -= 0.15
    if blocker.arms.right.hand_state == HandState.CONTROLLING:
        success_rate -= 0.15

    # Inside speed rush is tighter, needs more precision
    if side == "inside":
        success_rate -= 0.05

    success_rate = max(0.05, min(0.55, success_rate))

    if random.random() < success_rate:
        # Success! Get free around the edge
        rusher.arms.left.disengage()
        rusher.arms.right.disengage()

        # Lateral burst
        lateral = 1.0 if side == "outside" else -1.0
        rusher.velocity = rusher.velocity + Vec2(lateral * 2.0, -1.0)

        return MoveResult(
            success=True,
            description=f"Speed! {rusher.id} bends the corner and gets free {side}!",
            shed=True,
            advantage=0.6,
        )
    else:
        return MoveResult(
            success=False,
            description=f"{blocker.id} mirrors {rusher.id}'s speed rush and stays in front.",
            shed=False,
            advantage=-0.05,
        )


def attempt_speed_to_power(rusher: Player, blocker: Player) -> MoveResult:
    """
    Speed-to-power: Threaten outside, then convert to bull rush.

    The counter to tackles who overset to stop speed.
    Requires both AGI (to sell the speed fake) and STR (to convert to power).
    """
    from .vec2 import Vec2

    # Base success rate
    success_rate = 0.12

    # Need both attributes - balanced move
    power_rating = rusher.attributes.power_rating
    success_rate += (power_rating - 1.0) * 0.2

    # Works best if blocker is moving laterally (overcommitted to speed)
    if abs(blocker.velocity.x) > 1.0:
        success_rate += 0.2  # Big bonus - caught them sliding

    # Blocker balance matters
    if blocker.body.balance < 0.7:
        success_rate += 0.1

    # If blocker has inside hands, harder to convert
    if blocker.has_inside_hands:
        success_rate -= 0.15

    success_rate = max(0.05, min(0.45, success_rate))

    if random.random() < success_rate:
        # Convert! Drive blocker back
        blocker.body.balance -= 0.2
        blocker.body.pad_level = min(1.0, blocker.body.pad_level + 0.15)

        # Push blocker toward QB
        push_dir = Vec2(0, -1)
        blocker.velocity = blocker.velocity + push_dir * 2.0

        return MoveResult(
            success=True,
            description=f"Speed-to-power! {rusher.id} sells outside, converts to bull and drives {blocker.id} back!",
            shed=False,  # Not a shed, but gaining ground
            advantage=0.4,
        )
    else:
        return MoveResult(
            success=False,
            description=f"{rusher.id} tries to convert to power but {blocker.id} absorbs it.",
            shed=False,
            advantage=0.0,
        )


def attempt_ghost(rusher: Player, blocker: Player) -> MoveResult:
    """
    Ghost: Avoid contact entirely, slip past untouched.

    Very high risk, very high reward. Pure AGI move.
    Works when blocker overextends or punches at air.
    """
    # Base success rate - very low, this is a home run swing
    success_rate = 0.06

    # Pure AGI move
    agi_diff = rusher.attributes.agility - blocker.attributes.agility
    success_rate += agi_diff / 100 * 0.2

    # Blocker overextended (arms out, off balance)
    left_ext = blocker.arms.left.extension
    right_ext = blocker.arms.right.extension
    if left_ext > 0.8 or right_ext > 0.8:
        success_rate += 0.15  # Punching at air

    if blocker.body.balance < 0.6:
        success_rate += 0.1

    # If blocker has ANY contact, ghost doesn't work
    if blocker.arms.left.hand_state == HandState.CONTROLLING:
        success_rate = 0.02
    if blocker.arms.right.hand_state == HandState.CONTROLLING:
        success_rate = 0.02

    success_rate = max(0.02, min(0.35, success_rate))

    if random.random() < success_rate:
        # Ghost! Slip past untouched
        rusher.arms.left.disengage()
        rusher.arms.right.disengage()

        return MoveResult(
            success=True,
            description=f"Ghost! {rusher.id} slips past {blocker.id} untouched - free run to the QB!",
            shed=True,
            advantage=0.8,  # Huge advantage - no contact means full speed
        )
    else:
        return MoveResult(
            success=False,
            description=f"{rusher.id} tries to ghost but {blocker.id} gets a hand on him.",
            shed=False,
            advantage=-0.1,
        )


def attempt_long_arm(rusher: Player, blocker: Player, arm_side: ArmSide) -> MoveResult:
    """
    Long arm: Keep blocker at arm's length, control the distance.

    Uses reach advantage to prevent blocker from getting hands on chest.
    STR + reach dependent.
    """
    arm = rusher.arms.get_arm(arm_side)

    # Base success rate
    success_rate = 0.25

    # Arm length advantage is key
    length_diff = rusher.body.dimensions.arm_length - blocker.body.dimensions.arm_length
    success_rate += length_diff * 0.4  # Reach matters a lot

    # STR to hold them off
    str_diff = rusher.attributes.strength - blocker.attributes.strength
    success_rate += str_diff / 100 * 0.15

    # Hard to long arm if they already have inside hands
    if blocker.has_inside_hands:
        success_rate -= 0.2

    success_rate = max(0.1, min(0.5, success_rate))

    if random.random() < success_rate:
        # Establish distance control
        arm.extension = 0.9  # Nearly full extension
        arm.hand_state = HandState.CONTROLLING

        # Push blocker to arm's length
        blocker.body.balance -= 0.1

        side_desc = "left" if arm_side == ArmSide.LEFT else "right"
        return MoveResult(
            success=True,
            description=f"{rusher.id} locks out with his {side_desc} arm, keeping {blocker.id} at bay.",
            shed=False,
            advantage=0.25,
        )
    else:
        # Blocker gets inside
        return MoveResult(
            success=False,
            description=f"{blocker.id} gets inside {rusher.id}'s long arm attempt.",
            shed=False,
            advantage=-0.1,
        )


# =============================================================================
# OT-specific counters
# =============================================================================

def attempt_vertical_set(blocker: Player, rusher: Player, depth: float = 0.3) -> MoveResult:
    """
    Vertical set: Deep drop to cut off speed rush angle.

    OT technique - give ground backward to stay in front of speed rusher.
    Trade depth for width.
    """
    from .vec2 import Vec2

    # Give ground backward
    blocker.position = blocker.position + Vec2(0, -depth)
    blocker.lower_pad_level(0.05)

    # Reset feet at new position
    blocker.set_feet()

    # AGI determines how well we mirror
    mirror_quality = blocker.attributes.agi_hand_speed

    return MoveResult(
        success=True,
        description=f"{blocker.id} drops into vertical set, cutting off the angle.",
        advantage=0.1 * mirror_quality,
    )


def attempt_kick_slide(blocker: Player, rusher: Player, direction: float) -> MoveResult:
    """
    Kick-slide: Lateral movement while maintaining leverage.

    The fundamental OT pass protection footwork.
    Direction: -1 for left, +1 for right
    """
    from .vec2 import Vec2

    # Kick step in direction
    kick_success = blocker.kick_step(Vec2(direction, -0.2))

    if kick_success:
        # AGI determines slide speed
        slide_speed = 0.3 * blocker.attributes.agi_step_frequency / 3.0
        blocker.velocity = Vec2(direction * slide_speed, -0.1)

        return MoveResult(
            success=True,
            description=f"{blocker.id} kick-slides to mirror the rush.",
            advantage=0.1,
        )
    else:
        return MoveResult(
            success=False,
            description=f"{blocker.id}'s feet get tangled on the kick-slide.",
            advantage=-0.1,
        )
