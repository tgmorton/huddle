"""Coverage system for v2 simulation.

Handles DB behavior for both man and zone coverage:
- Man coverage: predictive tracking, break reaction, hip flip
- Zone coverage: zone drops, threat detection, pattern matching
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List, Tuple

from ..core.vec2 import Vec2
from ..core.entities import Player, Team, Position
from ..core.clock import Clock
from ..core.events import EventBus, EventType
from ..physics.movement import MovementProfile, MovementSolver, MovementResult


# =============================================================================
# Coverage Types
# =============================================================================

class CoverageType(str, Enum):
    """Type of coverage assignment."""
    MAN = "man"
    ZONE = "zone"


class CoverageScheme(str, Enum):
    """Defensive coverage schemes."""
    COVER_0 = "cover_0"      # Pure man, no deep help
    COVER_1 = "cover_1"      # Man with single high safety
    COVER_2 = "cover_2"      # 2 deep, 5 under zones
    COVER_3 = "cover_3"      # 3 deep, 4 under zones
    COVER_4 = "cover_4"      # Quarters
    COVER_2_MAN = "cover_2_man"  # 2 deep safeties, man under


class ZoneType(str, Enum):
    """Zone coverage areas."""
    # Deep zones
    DEEP_THIRD_L = "deep_third_l"
    DEEP_THIRD_M = "deep_third_m"
    DEEP_THIRD_R = "deep_third_r"
    DEEP_HALF_L = "deep_half_l"
    DEEP_HALF_R = "deep_half_r"
    DEEP_QUARTER_1 = "deep_quarter_1"
    DEEP_QUARTER_2 = "deep_quarter_2"
    DEEP_QUARTER_3 = "deep_quarter_3"
    DEEP_QUARTER_4 = "deep_quarter_4"
    # Underneath zones
    FLAT_L = "flat_l"
    FLAT_R = "flat_r"
    HOOK_L = "hook_l"
    HOOK_R = "hook_r"
    CURL_FLAT_L = "curl_flat_l"
    CURL_FLAT_R = "curl_flat_r"
    MIDDLE = "middle"


class CoveragePhase(str, Enum):
    """Current phase of coverage."""
    PRE_SNAP = "pre_snap"
    BACKPEDAL = "backpedal"       # Reading while retreating
    TRAIL = "trail"               # Behind receiver, chasing
    CLOSING = "closing"           # Driving on receiver
    IN_PHASE = "in_phase"         # Even with receiver
    FLIP_HIPS = "flip_hips"       # Transitioning direction
    ZONE_DROP = "zone_drop"       # Dropping to zone
    ZONE_READ = "zone_read"       # Reading routes in zone
    TRIGGERED = "triggered"       # Breaking on receiver in zone


# =============================================================================
# Zone Boundaries
# =============================================================================

@dataclass
class ZoneBoundary:
    """Defines a zone's coverage area."""
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    anchor: Vec2  # Home position when no threat
    is_deep: bool = False

    def contains(self, pos: Vec2) -> bool:
        """Check if position is in this zone."""
        return (self.min_x <= pos.x <= self.max_x and
                self.min_y <= pos.y <= self.max_y)

    def distance_to(self, pos: Vec2) -> float:
        """Distance from position to nearest zone edge."""
        dx = max(self.min_x - pos.x, 0, pos.x - self.max_x)
        dy = max(self.min_y - pos.y, 0, pos.y - self.max_y)
        return math.sqrt(dx * dx + dy * dy)

    @property
    def center(self) -> Vec2:
        return Vec2((self.min_x + self.max_x) / 2, (self.min_y + self.max_y) / 2)


# Zone definitions - realistic NFL coverage areas
ZONE_BOUNDARIES: Dict[ZoneType, ZoneBoundary] = {
    # Deep thirds (Cover 3)
    ZoneType.DEEP_THIRD_L: ZoneBoundary(-30, -8, 10, 50, Vec2(-16, 12), is_deep=True),
    ZoneType.DEEP_THIRD_M: ZoneBoundary(-10, 10, 12, 50, Vec2(0, 14), is_deep=True),
    ZoneType.DEEP_THIRD_R: ZoneBoundary(8, 30, 10, 50, Vec2(16, 12), is_deep=True),

    # Deep halves (Cover 2)
    ZoneType.DEEP_HALF_L: ZoneBoundary(-30, 0, 10, 50, Vec2(-12, 12), is_deep=True),
    ZoneType.DEEP_HALF_R: ZoneBoundary(0, 30, 10, 50, Vec2(12, 12), is_deep=True),

    # Quarters (Cover 4)
    ZoneType.DEEP_QUARTER_1: ZoneBoundary(-30, -10, 8, 50, Vec2(-16, 10), is_deep=True),
    ZoneType.DEEP_QUARTER_2: ZoneBoundary(-12, 0, 10, 50, Vec2(-6, 12), is_deep=True),
    ZoneType.DEEP_QUARTER_3: ZoneBoundary(0, 12, 10, 50, Vec2(6, 12), is_deep=True),
    ZoneType.DEEP_QUARTER_4: ZoneBoundary(10, 30, 8, 50, Vec2(16, 10), is_deep=True),

    # Flat zones
    ZoneType.FLAT_L: ZoneBoundary(-30, -8, -2, 8, Vec2(-14, 4), is_deep=False),
    ZoneType.FLAT_R: ZoneBoundary(8, 30, -2, 8, Vec2(14, 4), is_deep=False),

    # Hook zones
    ZoneType.HOOK_L: ZoneBoundary(-12, -2, 5, 14, Vec2(-6, 8), is_deep=False),
    ZoneType.HOOK_R: ZoneBoundary(2, 12, 5, 14, Vec2(6, 8), is_deep=False),

    # Curl-flat zones
    ZoneType.CURL_FLAT_L: ZoneBoundary(-25, -5, 0, 12, Vec2(-12, 6), is_deep=False),
    ZoneType.CURL_FLAT_R: ZoneBoundary(5, 25, 0, 12, Vec2(12, 6), is_deep=False),

    # Middle zone
    ZoneType.MIDDLE: ZoneBoundary(-8, 8, 8, 16, Vec2(0, 10), is_deep=False),
}


# =============================================================================
# Coverage Assignment
# =============================================================================

@dataclass
class CoverageAssignment:
    """A defender's coverage assignment."""
    defender_id: str
    coverage_type: CoverageType

    # Man coverage
    man_target_id: Optional[str] = None

    # Zone coverage
    zone_type: Optional[ZoneType] = None

    # State tracking
    phase: CoveragePhase = CoveragePhase.PRE_SNAP
    is_active: bool = False

    # Man coverage state
    has_reacted_to_break: bool = False
    reaction_delay_remaining: int = 0
    pre_break_velocity: Optional[Vec2] = None
    read_confidence: float = 1.0

    # Zone coverage state
    has_triggered: bool = False
    zone_target_id: Optional[str] = None
    is_backpedaling: bool = False

    # Tracking
    anticipated_position: Optional[Vec2] = None
    last_read_velocity: Vec2 = field(default_factory=Vec2.zero)


# =============================================================================
# Coverage System
# =============================================================================

class CoverageSystem:
    """Manages all coverage behavior."""

    # Physics constants
    BASE_LOOKAHEAD_TICKS = 6
    MAX_LOOKAHEAD_TICKS = 12
    BASE_REACTION_DELAY = 5  # Ticks before reacting to break
    FLIP_HIPS_SPEED_PENALTY = 0.45  # Speed retained during hip flip

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.solver = MovementSolver()
        self.assignments: Dict[str, CoverageAssignment] = {}

    def assign_man_coverage(
        self,
        defender: Player,
        receiver_id: str,
        alignment: Vec2,
    ) -> CoverageAssignment:
        """Assign a defender to man coverage on a receiver."""
        assignment = CoverageAssignment(
            defender_id=defender.id,
            coverage_type=CoverageType.MAN,
            man_target_id=receiver_id,
        )
        self.assignments[defender.id] = assignment

        # Set initial position (typically 5-8 yards off)
        defender.pos = alignment

        return assignment

    def assign_zone_coverage(
        self,
        defender: Player,
        zone_type: ZoneType,
        alignment: Vec2,
    ) -> CoverageAssignment:
        """Assign a defender to zone coverage."""
        assignment = CoverageAssignment(
            defender_id=defender.id,
            coverage_type=CoverageType.ZONE,
            zone_type=zone_type,
        )
        self.assignments[defender.id] = assignment

        # Set initial position
        defender.pos = alignment

        return assignment

    def start_coverage(self, clock: Clock):
        """Start all coverage assignments (at snap)."""
        for assignment in self.assignments.values():
            assignment.is_active = True
            if assignment.coverage_type == CoverageType.ZONE:
                assignment.phase = CoveragePhase.ZONE_DROP
                assignment.is_backpedaling = True
            else:
                assignment.phase = CoveragePhase.BACKPEDAL

        self._emit_event(EventType.SNAP, None, "Coverage started", clock)

    def update(
        self,
        defender: Player,
        profile: MovementProfile,
        receivers: List[Player],
        dt: float,
        clock: Clock,
    ) -> Tuple[MovementResult, str]:
        """Update a defender's coverage.

        Args:
            defender: The defending player
            profile: Defender's movement profile
            receivers: List of all receivers
            dt: Time step
            clock: Game clock

        Returns:
            (MovementResult, reasoning_string)
        """
        assignment = self.assignments.get(defender.id)
        if not assignment or not assignment.is_active:
            # No assignment - stay put
            return MovementResult(
                new_pos=defender.pos,
                new_vel=Vec2.zero(),
            ), "No coverage assignment"

        if assignment.coverage_type == CoverageType.MAN:
            return self._update_man_coverage(
                defender, profile, assignment, receivers, dt, clock
            )
        else:
            return self._update_zone_coverage(
                defender, profile, assignment, receivers, dt, clock
            )

    def _update_man_coverage(
        self,
        defender: Player,
        profile: MovementProfile,
        assignment: CoverageAssignment,
        receivers: List[Player],
        dt: float,
        clock: Clock,
    ) -> Tuple[MovementResult, str]:
        """Update man coverage using predictive tracking."""
        # Find target receiver
        target = None
        for rcvr in receivers:
            if rcvr.id == assignment.man_target_id:
                target = rcvr
                break

        if not target:
            return MovementResult(
                new_pos=defender.pos,
                new_vel=Vec2.zero(),
            ), "Target receiver not found"

        reasoning_parts = []

        # Get defender attributes
        man_cov = defender.attributes.man_coverage
        play_rec = defender.attributes.play_recognition

        # Calculate lookahead based on play recognition
        play_rec_factor = play_rec / 100
        distance_to_wr = defender.pos.distance_to(target.pos)

        base_lookahead = self.BASE_LOOKAHEAD_TICKS + (play_rec_factor * 4)
        if distance_to_wr < 1.5:
            base_lookahead *= 0.5
        elif distance_to_wr < 3:
            base_lookahead *= 0.7
        lookahead_ticks = max(3, min(self.MAX_LOOKAHEAD_TICKS, base_lookahead))

        # Detect route break (significant direction change)
        receiver_speed = target.velocity.length()
        just_started_flip = False

        # Check if receiver just made a break (sudden direction change)
        is_breaking = self._detect_route_break(target, assignment)

        if is_breaking:
            if not assignment.has_reacted_to_break and assignment.reaction_delay_remaining == 0:
                # Break just detected! Set reaction delay
                delay_reduction = play_rec_factor * 2
                assignment.reaction_delay_remaining = max(2, int(self.BASE_REACTION_DELAY - delay_reduction))

                # Freeze pre-break velocity - DB will project wrong direction
                if assignment.pre_break_velocity is None:
                    assignment.pre_break_velocity = assignment.last_read_velocity
                assignment.read_confidence = 1.0  # Confidently wrong!
                reasoning_parts.append(f"Break detected! Reaction delay: {assignment.reaction_delay_remaining}")

            if not assignment.has_reacted_to_break:
                assignment.reaction_delay_remaining -= 1

                # During delay, use frozen velocity (wrong projection)
                if assignment.pre_break_velocity:
                    assignment.last_read_velocity = assignment.pre_break_velocity

                if assignment.reaction_delay_remaining <= 0:
                    assignment.has_reacted_to_break = True
                    assignment.phase = CoveragePhase.FLIP_HIPS
                    just_started_flip = True
                    # Now use actual velocity
                    assignment.last_read_velocity = target.velocity
                    assignment.pre_break_velocity = None
                    assignment.read_confidence = 0.5
                    reasoning_parts.append("Flipping hips!")
                    self._emit_event(
                        EventType.COVERAGE_BREAK_REACTION,
                        defender.id,
                        f"{defender.name} reacts to break",
                        clock,
                    )

        else:
            # Normal tracking - update read
            if receiver_speed > 0.1:
                assignment.last_read_velocity = target.velocity
            assignment.read_confidence = min(1.0, assignment.read_confidence + 0.1)
            assignment.pre_break_velocity = None
            assignment.has_reacted_to_break = False

        # Project anticipated position
        projected_pos = target.pos + assignment.last_read_velocity * (lookahead_ticks * dt)

        # Blend projection with actual based on confidence
        if assignment.pre_break_velocity is not None:
            # During break delay - full commitment to wrong direction
            projection_weight = 1.0
        else:
            projection_weight = assignment.read_confidence
            if distance_to_wr < 2:
                projection_weight *= 0.6

        anticipated = target.pos.lerp(projected_pos, projection_weight)
        assignment.anticipated_position = anticipated

        # Calculate movement toward anticipated position
        target_pos = anticipated

        # Apply speed penalties
        effective_max_speed = profile.max_speed

        # Hip flip penalty
        if just_started_flip:
            flip_penalty = self.FLIP_HIPS_SPEED_PENALTY + (man_cov / 100) * 0.15
            effective_max_speed *= flip_penalty
            reasoning_parts.append(f"Flip penalty: {flip_penalty:.0%}")

        # During flip phase, cap speed
        if assignment.phase == CoveragePhase.FLIP_HIPS:
            effective_max_speed *= 0.65

        # Pre-reaction penalty (haven't reacted yet)
        if is_breaking and not assignment.has_reacted_to_break:
            effective_max_speed *= 0.7
            reasoning_parts.append("Pre-reaction slowdown")

        # Solve movement
        result = self.solver.solve(
            defender.pos,
            defender.velocity,
            target_pos,
            profile,
            dt,
            max_speed_override=effective_max_speed,
        )

        # Update phase based on position relative to receiver
        if assignment.phase == CoveragePhase.FLIP_HIPS:
            if assignment.has_reacted_to_break:
                # Transition out of flip after a moment
                assignment.phase = CoveragePhase.TRAIL if defender.pos.y < target.pos.y else CoveragePhase.CLOSING
        else:
            if defender.pos.y < target.pos.y - 1:
                assignment.phase = CoveragePhase.TRAIL
            elif defender.pos.y > target.pos.y + 1:
                assignment.phase = CoveragePhase.CLOSING
            else:
                assignment.phase = CoveragePhase.IN_PHASE

        # Build reasoning
        separation = defender.pos.distance_to(target.pos)
        reasoning_parts.insert(0, f"Man coverage on {target.name}")
        reasoning_parts.append(f"Phase: {assignment.phase.value}")
        reasoning_parts.append(f"Separation: {separation:.1f}yd")

        return result, " | ".join(reasoning_parts)

    def _update_zone_coverage(
        self,
        defender: Player,
        profile: MovementProfile,
        assignment: CoverageAssignment,
        receivers: List[Player],
        dt: float,
        clock: Clock,
    ) -> Tuple[MovementResult, str]:
        """Update zone coverage - pattern read, trigger on threats."""
        zone = ZONE_BOUNDARIES.get(assignment.zone_type)
        if not zone:
            return MovementResult(
                new_pos=defender.pos,
                new_vel=Vec2.zero(),
            ), "Invalid zone assignment"

        reasoning_parts = [f"Zone: {assignment.zone_type.value}"]

        # Find threats in zone
        threat, threat_level = self._find_zone_threat(defender, assignment, zone, receivers)

        # Determine target position
        if threat and threat_level == "in_zone":
            # Receiver in zone - break on them!
            if not assignment.has_triggered:
                assignment.has_triggered = True
                assignment.phase = CoveragePhase.TRIGGERED
                self._emit_event(
                    EventType.ZONE_TRIGGER,
                    defender.id,
                    f"{defender.name} triggers on {threat.name}",
                    clock,
                )

            assignment.zone_target_id = threat.id
            assignment.is_backpedaling = False

            # Predictive tracking
            play_rec_factor = defender.attributes.play_recognition / 100
            lookahead = self.BASE_LOOKAHEAD_TICKS * (0.5 + play_rec_factor * 0.5) * dt
            anticipated = threat.pos + threat.velocity * lookahead
            assignment.anticipated_position = anticipated

            # For deep zones with vertical routes - match path
            if zone.is_deep and threat.velocity.y > 0.5:
                target_pos = Vec2(anticipated.x, max(defender.pos.y, anticipated.y))
            else:
                target_pos = anticipated

            reasoning_parts.append(f"Triggered on {threat.name}")

        elif threat and threat_level == "approaching":
            # Threat approaching - prepare
            assignment.zone_target_id = threat.id
            assignment.is_backpedaling = False

            play_rec_factor = defender.attributes.play_recognition / 100
            lookahead = self.BASE_LOOKAHEAD_TICKS * (0.5 + play_rec_factor * 0.5) * dt
            anticipated = threat.pos + threat.velocity * lookahead
            assignment.anticipated_position = anticipated

            # Stay in zone but shade toward threat
            target_pos = zone.anchor.lerp(anticipated, 0.4)
            reasoning_parts.append(f"Reading {threat.name}")

        else:
            # No threat - drop to zone anchor
            assignment.has_triggered = False
            assignment.zone_target_id = None

            if zone.is_deep:
                assignment.is_backpedaling = True
                assignment.phase = CoveragePhase.ZONE_DROP
            else:
                assignment.phase = CoveragePhase.ZONE_READ

            target_pos = zone.anchor
            reasoning_parts.append("No threat - holding zone")

        # Speed calculation
        zone_cov = defender.attributes.zone_coverage
        zone_factor = (zone_cov / 85) ** 1.5

        if assignment.has_triggered:
            # Full speed when triggered
            effective_max_speed = profile.max_speed * zone_factor
        elif assignment.is_backpedaling:
            # Slower while backpedaling
            effective_max_speed = profile.max_speed * 0.6
        else:
            # Reading speed
            effective_max_speed = profile.max_speed * zone_factor * 0.8

        # Slow down near anchor when no threat
        if not assignment.has_triggered and defender.pos.distance_to(zone.anchor) < 2:
            effective_max_speed *= 0.5

        # Solve movement
        result = self.solver.solve(
            defender.pos,
            defender.velocity,
            target_pos,
            profile,
            dt,
            max_speed_override=effective_max_speed,
        )

        reasoning_parts.append(f"Phase: {assignment.phase.value}")

        return result, " | ".join(reasoning_parts)

    def _detect_route_break(self, receiver: Player, assignment: CoverageAssignment) -> bool:
        """Detect if receiver just made a route break."""
        if receiver.velocity.length() < 0.5:
            return False

        if assignment.last_read_velocity.length() < 0.1:
            return False

        # Compare current direction to last read direction
        current_dir = receiver.velocity.normalized()
        last_dir = assignment.last_read_velocity.normalized()

        angle = current_dir.angle_to(last_dir)

        # Significant direction change = break
        return angle > 0.6  # ~35 degrees

    def _find_zone_threat(
        self,
        defender: Player,
        assignment: CoverageAssignment,
        zone: ZoneBoundary,
        receivers: List[Player],
    ) -> Tuple[Optional[Player], str]:
        """Find the most dangerous receiver threatening this zone."""
        best_receiver = None
        best_threat = "none"
        best_score = -float("inf")

        for rcvr in receivers:
            in_zone = zone.contains(rcvr.pos)
            approaching = False

            dist_to_zone = zone.distance_to(rcvr.pos)
            if dist_to_zone < 10 and not in_zone:
                # Check if moving toward zone
                if rcvr.velocity.y > 0.1 and rcvr.pos.y < zone.max_y:
                    approaching = True
                if abs(rcvr.velocity.x) > 0.1:
                    if (rcvr.velocity.x > 0 and rcvr.pos.x < zone.max_x) or \
                       (rcvr.velocity.x < 0 and rcvr.pos.x > zone.min_x):
                        approaching = True

            if not in_zone and not approaching:
                continue

            # Score this threat
            score = 0.0

            if in_zone:
                score += 100
                dist_to_center = rcvr.pos.distance_to(zone.center)
                score += max(0, 10 - dist_to_center)
            elif approaching:
                score += 50
                score += max(0, 10 - dist_to_zone) * 3

            # Vertical routes more dangerous for deep zones
            if zone.is_deep and rcvr.velocity.y > 0.3:
                score += 20

            # Prefer current target (continuity)
            if assignment.zone_target_id == rcvr.id:
                score += 25

            # Deep zone: prioritize receivers on defender's side
            if zone.is_deep:
                x_proximity = abs(rcvr.pos.x - defender.pos.x)
                score += max(0, 30 - x_proximity * 2)

                # Penalize wrong-side receivers
                zone_center_x = zone.center.x
                if (defender.pos.x > zone_center_x and rcvr.pos.x < zone_center_x) or \
                   (defender.pos.x < zone_center_x and rcvr.pos.x > zone_center_x):
                    score -= 40

            if score > best_score:
                best_score = score
                best_receiver = rcvr
                best_threat = "in_zone" if in_zone else "approaching"

        return best_receiver, best_threat

    def _emit_event(
        self,
        event_type: EventType,
        player_id: Optional[str],
        description: str,
        clock: Clock,
    ):
        """Emit a coverage event."""
        self.event_bus.emit_simple(
            event_type=event_type,
            tick=clock.tick_count,
            time=clock.current_time,
            player_id=player_id,
            description=description,
        )

    def get_assignment(self, defender_id: str) -> Optional[CoverageAssignment]:
        """Get a defender's coverage assignment."""
        return self.assignments.get(defender_id)

    def get_separation(self, defender: Player, receivers: List[Player]) -> float:
        """Get separation between defender and their assignment."""
        assignment = self.assignments.get(defender.id)
        if not assignment:
            return float("inf")

        if assignment.coverage_type == CoverageType.MAN:
            for rcvr in receivers:
                if rcvr.id == assignment.man_target_id:
                    return defender.pos.distance_to(rcvr.pos)
        elif assignment.zone_target_id:
            for rcvr in receivers:
                if rcvr.id == assignment.zone_target_id:
                    return defender.pos.distance_to(rcvr.pos)

        return float("inf")

    def clear_assignments(self):
        """Clear all coverage assignments."""
        self.assignments.clear()
