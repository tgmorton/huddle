"""
Collision detection and resolution for bodies and arms.

This is where the physics of hand fighting happens.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
import math

from .vec2 import Vec2
from .body import Body
from .arm import Arm, ArmSide, HandState
from .player import Player, PlayerRole

# Import for type hints
from typing import TYPE_CHECKING


@dataclass
class Contact:
    """A detected contact between two players."""
    player_a_id: str
    player_b_id: str
    contact_type: str  # "hand_on_chest", "hand_on_hand", "body_collision"
    position: Vec2     # World position of contact
    normal: Vec2       # Direction of force (from A to B)
    penetration: float # How deep the overlap is


@dataclass
class HandContact:
    """Specific hand-to-body or hand-to-hand contact."""
    attacker_id: str
    attacker_arm: ArmSide
    defender_id: str
    contact_point: Vec2
    is_inside: bool  # True if hand is on chest (inside position)


def detect_hand_on_body(attacker: Player, defender: Player) -> List[HandContact]:
    """
    Detect if attacker's hands are contacting defender's body.

    Returns list of contacts (0, 1, or 2 hands).
    """
    contacts = []

    for side in [ArmSide.LEFT, ArmSide.RIGHT]:
        arm = attacker.arms.get_arm(side)
        hand_pos = (attacker.left_hand_pos if side == ArmSide.LEFT
                    else attacker.right_hand_pos)

        # Check if hand is inside defender's torso bounds
        if defender.body.point_in_torso(hand_pos):
            # It's a contact - determine if inside or outside hands
            # Inside = hand is between defender's shoulders (on chest)
            # Outside = hand is on shoulder/side

            # Project hand onto defender's right vector
            to_hand = hand_pos - defender.body.center
            right_offset = to_hand.dot(defender.body.right_vector)

            # Inside hands = closer to center of chest
            chest_width = defender.body.dimensions.shoulder_width * 0.4
            is_inside = abs(right_offset) < chest_width

            contacts.append(HandContact(
                attacker_id=attacker.id,
                attacker_arm=side,
                defender_id=defender.id,
                contact_point=hand_pos,
                is_inside=is_inside,
            ))

    return contacts


def detect_hand_collision(player_a: Player, player_b: Player) -> List[Tuple[ArmSide, ArmSide, Vec2]]:
    """
    Detect if hands are colliding (hand fighting for position).

    Returns list of (a_arm, b_arm, collision_point) tuples.
    """
    collisions = []
    hand_radius = 0.1  # Approximate hand size

    for a_side in [ArmSide.LEFT, ArmSide.RIGHT]:
        a_hand = (player_a.left_hand_pos if a_side == ArmSide.LEFT
                  else player_a.right_hand_pos)

        for b_side in [ArmSide.LEFT, ArmSide.RIGHT]:
            b_hand = (player_b.left_hand_pos if b_side == ArmSide.LEFT
                      else player_b.right_hand_pos)

            dist = a_hand.distance_to(b_hand)
            if dist < hand_radius * 2:
                mid_point = a_hand.lerp(b_hand, 0.5)
                collisions.append((a_side, b_side, mid_point))

    return collisions


def detect_body_collision(player_a: Player, player_b: Player) -> Optional[Contact]:
    """
    Detect if bodies are overlapping.

    Uses simplified ellipse collision.
    """
    # Quick distance check
    dist = player_a.position.distance_to(player_b.position)
    max_extent = max(
        player_a.body.dimensions.shoulder_width,
        player_a.body.dimensions.torso_depth,
        player_b.body.dimensions.shoulder_width,
        player_b.body.dimensions.torso_depth,
    )

    if dist > max_extent * 1.5:
        return None  # Too far apart

    # More detailed check - treat as rectangles for now
    # Get the axis-aligned bounding boxes
    a_min, a_max = player_a.body.get_bounding_box()
    b_min, b_max = player_b.body.get_bounding_box()

    # Check AABB overlap
    if (a_max.x < b_min.x or b_max.x < a_min.x or
        a_max.y < b_min.y or b_max.y < a_min.y):
        return None  # No overlap

    # Calculate penetration and normal
    # Simplified: use center-to-center direction
    direction = player_b.position - player_a.position
    if direction.length() < 0.01:
        direction = Vec2(1, 0)  # Arbitrary if exactly overlapping

    normal = direction.normalized()

    # Estimate penetration (simplified)
    overlap_x = min(a_max.x, b_max.x) - max(a_min.x, b_min.x)
    overlap_y = min(a_max.y, b_max.y) - max(a_min.y, b_min.y)
    penetration = min(overlap_x, overlap_y)

    contact_point = player_a.position.lerp(player_b.position, 0.5)

    return Contact(
        player_a_id=player_a.id,
        player_b_id=player_b.id,
        contact_type="body_collision",
        position=contact_point,
        normal=normal,
        penetration=penetration,
    )


def resolve_body_collision(player_a: Player, player_b: Player,
                           contact: Contact, dt: float) -> None:
    """
    Push overlapping bodies apart.

    These are HEAVY people - 280-315 lbs each. When they push, things move.
    STR, leverage (pad level), and mass determine who moves whom.
    """
    if contact.penetration <= 0:
        return

    # Only separate if not engaged in blocking.
    # When engaged (blocking), they should maintain contact while applying force.
    both_engaged = player_a.is_engaged and player_b.is_engaged
    one_is_blocker = (player_a.role == PlayerRole.BLOCKER or
                      player_b.role == PlayerRole.BLOCKER)

    if not (both_engaged and one_is_blocker):
        # Separate bodies when not in a blocking engagement
        separation = contact.normal * (contact.penetration / 2 + 0.01)
        player_a.position = player_a.position - separation
        player_b.position = player_b.position + separation

    # === THE LEVERAGE BATTLE ===
    # STR is the primary driver of push power
    # Mass and leverage are multipliers

    a_leverage = player_a.body.leverage_factor  # 0.5 (high) to 1.5 (low)
    b_leverage = player_b.body.leverage_factor

    # Push power = STR_mult * mass * leverage * balance
    a_str_mult = player_a.attributes.str_force_mult  # 0.5 to 1.5
    b_str_mult = player_b.attributes.str_force_mult

    a_push_power = a_str_mult * player_a.body.dimensions.mass * a_leverage * player_a.body.balance
    b_push_power = b_str_mult * player_b.body.dimensions.mass * b_leverage * player_b.body.balance

    # Inside hands give significant advantage
    if player_a.has_inside_hands:
        a_push_power *= 1.4
    if player_b.has_inside_hands:
        b_push_power *= 1.4

    total_power = a_push_power + b_push_power
    if total_power < 0.01:
        return

    # The differential determines who gets pushed
    power_diff = a_push_power - b_push_power
    power_ratio = power_diff / total_power  # -1 to 1

    # Base force - these are HEAVY men pushing each other
    base_force = 200.0

    # The winner pushes the loser
    push_force = base_force * abs(power_ratio)

    if power_ratio > 0:
        # A is winning, push B
        # B's resistance depends on their STR
        b_resist = player_b.attributes.str_resistance_mult
        effective_force = push_force / b_resist
        force_on_b = contact.normal * effective_force
        player_b.apply_force(force_on_b, dt)
        player_b.body.balance = max(0.4, player_b.body.balance - 0.01)
    else:
        # B is winning, push A
        a_resist = player_a.attributes.str_resistance_mult
        effective_force = push_force / a_resist
        force_on_a = -contact.normal * effective_force
        player_a.apply_force(force_on_a, dt)
        player_a.body.balance = max(0.4, player_a.body.balance - 0.01)


def resolve_hand_fighting(player_a: Player, player_b: Player,
                          a_contacts: List[HandContact],
                          b_contacts: List[HandContact],
                          dt: float) -> None:
    """
    Resolve hand fighting between two players.

    The player with inside hands can drive; outside hands get controlled.
    """
    a_inside_count = sum(1 for c in a_contacts if c.is_inside)
    b_inside_count = sum(1 for c in b_contacts if c.is_inside)

    # Determine who has hand control
    if a_inside_count > b_inside_count:
        # A has inside hands - A is controlling
        _apply_hand_control(player_a, player_b, a_contacts, dt)
    elif b_inside_count > a_inside_count:
        # B has inside hands - B is controlling
        _apply_hand_control(player_b, player_a, b_contacts, dt)
    else:
        # Contested - both fighting for position
        _apply_contested_hands(player_a, player_b, a_contacts, b_contacts, dt)


def _apply_hand_control(controller: Player, controlled: Player,
                        contacts: List[HandContact], dt: float) -> None:
    """
    Apply the effect of one player having hand control.

    Inside hands = you can DRIVE. This is where the pocket collapses.
    STR determines drive power, AGI helps maintain control.
    """
    if not contacts:
        return

    # Set arm states and calculate extension based on distance
    for contact in contacts:
        arm = controller.arms.get_arm(contact.attacker_arm)
        arm.hand_state = HandState.CONTROLLING
        arm.engaged_with = controlled.id

        shoulder = (controller.left_shoulder if contact.attacker_arm == ArmSide.LEFT
                    else controller.right_shoulder)
        contact_dist = shoulder.distance_to(contact.contact_point)
        arm.extension = min(1.0, max(0.1, contact_dist / arm.max_length))

    # === DRIVING WITH INSIDE HANDS ===
    # STR is the main driver of push power

    # Power from STR, mass, leverage
    controller_str = controller.attributes.str_force_mult
    controlled_str = controlled.attributes.str_resistance_mult

    controller_power = controller_str * controller.body.dimensions.mass * controller.body.leverage_factor
    controlled_power = controlled_str * controlled.body.dimensions.mass * controlled.body.leverage_factor

    # Bent arms = more drive power
    avg_extension = sum(controller.arms.get_arm(c.attacker_arm).extension
                        for c in contacts) / len(contacts)
    extension_power = 1.0 - abs(avg_extension - 0.5) * 1.5
    extension_power = max(0.4, extension_power)

    # Drive force - controller pushes in their facing direction
    push_direction = controller.body.facing_vector

    # Force scales with STR ratio
    power_ratio = controller_power / max(0.1, controlled_power)
    force_magnitude = 150.0 * extension_power * power_ratio
    force = push_direction * force_magnitude

    controlled.apply_force(force, dt)

    # Controlled player's pad level rises (getting stood up)
    controlled.body.pad_level = min(0.8, controlled.body.pad_level + 0.02 * dt)

    # Controlled player loses balance - faster if weaker
    balance_loss = 0.03 * dt * (controller_str / controlled_str)
    controlled.body.balance = max(0.4, controlled.body.balance - balance_loss)

    # Controller can lower pad level (driving low)
    controller.body.pad_level = max(0.2, controller.body.pad_level - 0.01 * dt)


def _apply_contested_hands(player_a: Player, player_b: Player,
                           a_contacts: List[HandContact],
                           b_contacts: List[HandContact],
                           dt: float) -> None:
    """
    Both players fighting for hand position - no clear winner yet.
    """
    # Both locked in combat
    for contact in a_contacts:
        arm = player_a.arms.get_arm(contact.attacker_arm)
        arm.hand_state = HandState.LOCKED
        arm.engaged_with = player_b.id

    for contact in b_contacts:
        arm = player_b.arms.get_arm(contact.attacker_arm)
        arm.hand_state = HandState.LOCKED
        arm.engaged_with = player_a.id

    # Small forces based on relative power (no clear winner)
    power_diff = player_a.effective_power - player_b.effective_power
    direction = (player_b.position - player_a.position).normalized()

    if abs(power_diff) > 0.1:
        force_magnitude = 20.0 * power_diff
        player_b.apply_force(direction * force_magnitude, dt)
        player_a.apply_force(-direction * force_magnitude, dt)


# =============================================================================
# Double Team Mechanics
# =============================================================================

def resolve_double_team(
    post_blocker: Player,
    drive_blocker: Player,
    rusher: Player,
    drive_direction: float,  # -1 left, +1 right
    dt: float
) -> None:
    """
    Resolve a double team block.

    Per coaching book: "Work hip-to-hip as they sweep the defensive lineman upfield.
    Shoulders together to form one large blocking surface."

    Post blocker: Drive block technique, emphasis on VERTICAL movement, lift defender
    Seal/Drive blocker: Glide step INTO defender, drive near shoulder backward

    Key: Both blockers drive UPFIELD together, not one backward and one lateral.
    """
    # === POSITION CHECKS ===
    post_dist = post_blocker.position.distance_to(rusher.position)
    drive_dist = drive_blocker.position.distance_to(rusher.position)

    # === DRIVE BLOCKER CLOSING ===
    # The drive/seal blocker must close to hip-to-hip with post blocker
    # This is the critical "fit" mechanic - glide step into the defender
    ideal_spacing = 0.6  # Hip-to-hip, shoulders together
    blocker_dist = post_blocker.position.distance_to(drive_blocker.position)

    if blocker_dist > ideal_spacing:
        # Drive blocker closes toward the double team
        # Target: hip-to-hip with post blocker, on rusher's outside number
        target_pos = rusher.position + Vec2(drive_direction * 0.3, 0)
        close_dir = (target_pos - drive_blocker.position)
        if close_dir.length() > 0.1:
            close_dir = close_dir.normalized()
            # Active movement to close the gap - this is the "glide step"
            # Use force rather than direct velocity add to prevent runaway
            close_force = min(150.0, (blocker_dist - ideal_spacing) * 200.0)
            drive_blocker.apply_force(close_dir * close_force, dt)

    # Not close enough yet for combined force
    if drive_dist > 2.0:
        # Drive blocker still closing - post handles alone temporarily
        if post_dist < 2.0:
            # Simple 1v1 push from post
            to_rusher = rusher.position - post_blocker.position
            if to_rusher.length() > 0.01:
                push_dir = to_rusher.normalized()
                post_blocker.reach_both_toward(rusher.body.chest_center)
                rusher.apply_force(push_dir * 80.0, dt)
        return

    # === BOTH BLOCKERS ENGAGED - DOUBLE TEAM ACTIVE ===

    # === FORCE GENERATION ===
    post_str = post_blocker.attributes.str_force_mult
    post_mass = post_blocker.body.dimensions.mass
    post_leverage = post_blocker.body.leverage_factor
    post_power = post_str * post_mass * post_leverage * post_blocker.body.balance

    drive_str = drive_blocker.attributes.str_force_mult
    drive_mass = drive_blocker.body.dimensions.mass
    drive_leverage = drive_blocker.body.leverage_factor
    drive_power = drive_str * drive_mass * drive_leverage * drive_blocker.body.balance

    rusher_str = rusher.attributes.str_resistance_mult
    rusher_mass = rusher.body.dimensions.mass
    rusher_leverage = rusher.body.leverage_factor
    rusher_power = rusher_str * rusher_mass * rusher_leverage * rusher.body.balance

    # Double team combines forces (coordination improves when hip-to-hip)
    coordination = 0.7 + 0.25 * max(0, 1.0 - blocker_dist / ideal_spacing)
    combined_power = (post_power + drive_power) * coordination

    power_ratio = combined_power / max(rusher_power, 0.1)

    # === PUSH DIRECTION: PRIMARILY UPFIELD ===
    # Per book: "sweep the defensive lineman upfield"
    # The goal is VERTICAL movement, with slight lateral wash

    # Upfield direction (positive Y in our coordinate system)
    upfield_dir = Vec2(0, 1)

    # Slight lateral wash component (20% lateral, 80% vertical)
    lateral_dir = Vec2(drive_direction, 0)
    combined_dir = (upfield_dir * 0.8 + lateral_dir * 0.2).normalized()

    # === APPLY FORCES ===
    base_force = 300.0  # Strong double team force

    if power_ratio > 0.8:  # Blockers have advantage
        # Drive rusher upfield
        push_magnitude = base_force * power_ratio
        push_magnitude = min(push_magnitude, 500.0)

        rusher.apply_force(combined_dir * push_magnitude, dt)

        # Blockers advance with the drive
        # Add to existing velocity to preserve closing momentum
        blocker_drive_speed = 0.8 * power_ratio
        drive_velocity = combined_dir * blocker_drive_speed
        post_blocker.velocity = post_blocker.velocity * 0.5 + drive_velocity
        drive_blocker.velocity = drive_blocker.velocity * 0.5 + drive_velocity

        # Rusher loses balance and gets stood up
        balance_loss = 0.05 * dt * power_ratio
        rusher.body.balance = max(0.3, rusher.body.balance - balance_loss)
        rusher.body.pad_level = min(0.9, rusher.body.pad_level + 0.04 * dt)

    else:
        # Elite DT holding ground - rare
        resist_force = base_force * (1.0 - power_ratio) * 0.2
        push_back = -upfield_dir * resist_force
        post_blocker.apply_force(push_back * 0.5, dt)
        drive_blocker.apply_force(push_back * 0.5, dt)

    # === HAND PLACEMENT ===
    # Post blocker: hands on chest/inside number for vertical lift
    post_blocker.reach_both_toward(rusher.body.chest_center)

    # Drive blocker: hands on outside number/shoulder to open defender's shoulders
    outside_shoulder = rusher.position + Vec2(drive_direction * 0.25, 0)
    drive_blocker.reach_both_toward(outside_shoulder)

    # === HIP-TO-HIP MAINTENANCE ===
    # Keep blockers together as they drive
    if blocker_dist > ideal_spacing:
        to_partner = drive_blocker.position - post_blocker.position
        if to_partner.length() > 0.01:
            pull_dir = to_partner.normalized()
            pull_force = 50.0 * (blocker_dist - ideal_spacing)
            post_blocker.apply_force(pull_dir * pull_force, dt)
            drive_blocker.apply_force(-pull_dir * pull_force, dt)

    # === LOW PAD LEVEL ===
    # Both blockers stay low to maximize leverage
    post_blocker.body.pad_level = max(0.3, post_blocker.body.pad_level - 0.02 * dt)
    drive_blocker.body.pad_level = max(0.3, drive_blocker.body.pad_level - 0.02 * dt)


def can_split_double(rusher: Player, post: Player, drive: Player) -> float:
    """
    Calculate chance of rusher splitting the double team.

    Returns probability (0-1) of successfully splitting per tick.

    Splitting doubles is VERY hard - only elite DTs can do it regularly.
    Most double teams should hold for the duration of the play.
    """
    # Rusher attributes
    str_rating = rusher.attributes.strength
    agi_rating = rusher.attributes.agility

    # Base chance is very low - splitting doubles should be rare
    split_chance = 0.01

    # Only elite STR (80+) gives meaningful bonus
    if str_rating > 80:
        str_bonus = (str_rating - 80) / 100 * 0.03  # Up to +3% at 100
        split_chance += str_bonus

    # Gap between blockers - only matters if gap is large (>1.2 yards)
    # Hip-to-hip is 0.6 yards, so 1.2+ means significant separation
    blocker_gap = post.position.distance_to(drive.position)
    if blocker_gap > 1.2:
        split_chance += (blocker_gap - 1.2) * 0.05

    # Blockers not coordinated (different pad levels) - minor factor
    pad_diff = abs(post.body.pad_level - drive.body.pad_level)
    split_chance += pad_diff * 0.03

    # One blocker badly off balance (< 0.4) creates opportunity
    min_balance = min(post.body.balance, drive.body.balance)
    if min_balance < 0.4:
        split_chance += (0.4 - min_balance) * 0.1

    # Cap at reasonable maximum
    return max(0.005, min(0.10, split_chance))
