"""Read Evaluator - The engine that evaluates reads and returns outcomes.

The ReadEvaluator is the generic engine that:
1. Finds the key actor (attribute-gated accuracy)
2. Evaluates the trigger (attribute-gated interpretation)
3. Returns the outcome (with variance for low-skill players)

This is brain-agnostic - it works for QB reads, DB anticipation, LB run fits, etc.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional, Any, Tuple, TYPE_CHECKING

from .reads import (
    ReadDefinition,
    ReadOutcome,
    TriggerCondition,
    TriggerType,
    KeyActorRole,
    get_awareness_accuracy,
    get_decision_making_accuracy,
    get_max_pressure_for_reads,
)
from .variance import is_deterministic, recognition_delay
from .trace import get_trace_system, TraceCategory

if TYPE_CHECKING:
    from .vec2 import Vec2
    from .entities import Player, Position


# =============================================================================
# Evaluation Result
# =============================================================================

@dataclass
class ReadEvaluationResult:
    """Result of evaluating a read.

    Attributes:
        success: Whether the read was successfully evaluated
        outcome: The selected outcome (None if failed)
        key_actor_id: ID of the key actor found
        trigger_matched: Which trigger was matched
        reasoning: Human-readable explanation
        processing_delay: How long the read took to process
        was_random: Whether outcome was randomly selected (low skill)
    """
    success: bool
    outcome: Optional[ReadOutcome] = None
    key_actor_id: Optional[str] = None
    trigger_matched: Optional[TriggerType] = None
    reasoning: str = ""
    processing_delay: float = 0.0
    was_random: bool = False


# =============================================================================
# Key Actor Finder
# =============================================================================

def _find_key_actor(
    key_actor_role: KeyActorRole,
    opponents: List[Any],  # List[PlayerView]
    field_context: Any,    # Field info (LOS, etc.)
    target_receiver_pos: Optional[Any] = None,  # Vec2 of receiver we're reading for
) -> Optional[Any]:
    """Find the key actor (defender) to read based on their role.

    Args:
        key_actor_role: What role to look for
        opponents: List of defensive players
        field_context: Field context (for LOS, zones, etc.)
        target_receiver_pos: Position of receiver we're reading for (for zone reads)

    Returns:
        The defender matching the key actor role, or None
    """
    from .entities import Position

    los_y = getattr(field_context, 'los_y', 0.0)

    for defender in opponents:
        def_pos = getattr(defender, 'position', None)
        pos = getattr(defender, 'pos', None)

        if pos is None:
            continue

        # Depth behind LOS
        depth = los_y - pos.y if los_y else -pos.y

        # Match based on key actor role
        if key_actor_role == KeyActorRole.FLAT_CORNER:
            # CB playing flat zone (near LOS, in flat area)
            if def_pos == Position.CB:
                if depth < 8 and abs(pos.x) > 10:  # Within 8 yds, outside numbers
                    return defender

        elif key_actor_role == KeyActorRole.FLAT_DEFENDER:
            # Any flat zone player (typically at 3-7 yards depth, wide)
            if depth > 2 and depth < 10:
                # Check if in flat area (outside the hashes)
                if target_receiver_pos:
                    # Find defender near the receiver's horizontal position
                    if abs(pos.x - target_receiver_pos.x) < 8:
                        return defender
                elif abs(pos.x) > 5:  # General flat area
                    return defender

        elif key_actor_role == KeyActorRole.HOOK_CURL_DEFENDER:
            # LB/S in hook-curl zone (8-15 yards, inside)
            if def_pos in (Position.MLB, Position.ILB, Position.OLB, Position.SS):
                if depth > 5 and depth < 15 and abs(pos.x) < 15:
                    return defender

        elif key_actor_role == KeyActorRole.DEEP_HALF:
            # Safety playing deep half
            if def_pos in (Position.FS, Position.SS):
                if depth > 12:  # Deep
                    return defender

        elif key_actor_role == KeyActorRole.MIDDLE_FIELD:
            # Single high safety (Cover 1/3)
            if def_pos == Position.FS:
                if depth > 12 and abs(pos.x) < 10:  # Deep and centered
                    return defender

        elif key_actor_role == KeyActorRole.MAN_DEFENDER:
            # Defender in man coverage on the target
            if target_receiver_pos:
                dist = pos.distance_to(target_receiver_pos)
                if dist < 5:  # Within 5 yards of target
                    return defender

        elif key_actor_role == KeyActorRole.PLAY_SIDE_LB:
            # LB to the run play side
            if def_pos in (Position.MLB, Position.ILB, Position.OLB):
                # Would need run direction info - for now return first LB
                return defender

        elif key_actor_role == KeyActorRole.PULLING_GUARD:
            # This would be used by LB/DB reads, not finding defenders
            # Looking for OL movement
            pass

    return None


# =============================================================================
# Trigger Evaluation
# =============================================================================

def _evaluate_trigger(
    trigger: TriggerCondition,
    key_actor: Any,  # PlayerView
    initial_position: Optional[Any] = None,  # Vec2 - where actor started
    current_time: float = 0.0,
    time_since_snap: float = 0.0,
) -> Tuple[bool, str]:
    """Evaluate if a trigger condition is met.

    Args:
        trigger: The trigger condition to check
        key_actor: The defender being read
        initial_position: Where the actor started at snap
        current_time: Current simulation time
        time_since_snap: Time since the snap

    Returns:
        (trigger_matched, reason)
    """
    # Check timing window
    min_time, max_time = trigger.timing_window
    if time_since_snap < min_time or time_since_snap > max_time:
        return False, f"outside timing window ({time_since_snap:.2f}s not in {min_time}-{max_time}s)"

    pos = getattr(key_actor, 'pos', None)
    velocity = getattr(key_actor, 'velocity', None)

    if pos is None:
        return False, "key actor has no position"

    # Get movement info
    if initial_position:
        movement = pos - initial_position
        vertical_movement = movement.y  # Positive = dropped back
        horizontal_movement = abs(movement.x)
    else:
        vertical_movement = 0.0
        horizontal_movement = 0.0

    # Velocity-based detection
    if velocity:
        vertical_velocity = velocity.y
        horizontal_velocity = abs(velocity.x)
    else:
        vertical_velocity = 0.0
        horizontal_velocity = 0.0

    threshold = trigger.threshold

    # Evaluate each trigger type
    if trigger.trigger_type == TriggerType.SINKS:
        # Defender drops deeper (negative Y movement in our coord system)
        # Note: In our coords, positive Y is downfield, so sinking = positive Y
        if vertical_movement > threshold or vertical_velocity > 2.0:
            return True, f"defender sank {vertical_movement:.1f}yd"

    elif trigger.trigger_type == TriggerType.WIDENS:
        # Defender expands toward sideline
        if horizontal_movement > threshold or horizontal_velocity > 2.0:
            return True, f"defender widened {horizontal_movement:.1f}yd"

    elif trigger.trigger_type == TriggerType.SQUATS:
        # Defender sits on route underneath (minimal movement)
        total_movement = abs(vertical_movement) + horizontal_movement
        if velocity:
            speed = velocity.length()
            if total_movement < threshold and speed < 2.0:
                return True, f"defender squatting (moved {total_movement:.1f}yd)"
        elif total_movement < threshold:
            return True, f"defender squatting (moved {total_movement:.1f}yd)"

    elif trigger.trigger_type == TriggerType.JUMPS:
        # Defender breaks on route aggressively
        if velocity:
            speed = velocity.length()
            if speed > 5.0:  # Moving fast
                return True, f"defender jumped route (speed {speed:.1f})"

    elif trigger.trigger_type == TriggerType.CARRIES_VERTICAL:
        # Defender follows receiver vertically
        # Would need receiver position to compare
        if vertical_movement > threshold:
            return True, f"defender carrying vertical ({vertical_movement:.1f}yd)"

    elif trigger.trigger_type == TriggerType.OPENS_HIPS:
        # Defender commits to direction
        # Would need facing/hip direction data
        if velocity and velocity.length() > 3.0:
            return True, "defender committed (hips opened)"

    elif trigger.trigger_type == TriggerType.INSIDE_LEVERAGE:
        # Defender has inside position on receiver
        # Would need receiver position
        return False, "inside leverage check requires receiver position"

    elif trigger.trigger_type == TriggerType.OUTSIDE_LEVERAGE:
        # Defender has outside position on receiver
        return False, "outside leverage check requires receiver position"

    elif trigger.trigger_type == TriggerType.TRAIL_POSITION:
        # Defender is trailing receiver
        return False, "trail position check requires receiver position"

    return False, "trigger not matched"


# =============================================================================
# Main Evaluator
# =============================================================================

class ReadEvaluator:
    """Evaluates reads and returns outcomes with attribute-gating.

    Usage:
        evaluator = ReadEvaluator()

        result = evaluator.evaluate(
            read=smash_cover2_read,
            player_attributes=qb.attributes,
            opponents=defenders,
            field_context=world,
            pressure_level="moderate",
            time_since_snap=2.5,
        )

        if result.success:
            # result.outcome contains the target
            throw_to(result.outcome.target_position)
    """

    def __init__(self):
        self._initial_positions: dict[str, Any] = {}  # defender_id -> Vec2

    def reset_play(self, opponents: List[Any]) -> None:
        """Reset for a new play - capture initial defender positions.

        Call this at snap time to establish baselines for movement triggers.
        """
        self._initial_positions.clear()
        for opp in opponents:
            opp_id = getattr(opp, 'id', None)
            pos = getattr(opp, 'pos', None)
            if opp_id and pos:
                # Store a copy of the position
                self._initial_positions[opp_id] = pos.copy() if hasattr(pos, 'copy') else pos

    def evaluate(
        self,
        read: ReadDefinition,
        player_attributes: Any,  # PlayerAttributes
        opponents: List[Any],    # List[PlayerView]
        field_context: Any,      # WorldState with LOS, etc.
        pressure_level: str = "clean",
        time_since_snap: float = 0.0,
        current_time: float = 0.0,
        target_receiver_pos: Optional[Any] = None,  # Vec2 for zone reads
        player_id: str = "",
        player_name: str = "",
    ) -> ReadEvaluationResult:
        """Evaluate a read and return the outcome.

        Args:
            read: The read definition to evaluate
            player_attributes: Attributes of the player making the read
            opponents: List of defensive players
            field_context: Field context (LOS, etc.)
            pressure_level: Current pressure level string
            time_since_snap: Time since the snap
            current_time: Current simulation time
            target_receiver_pos: Position of receiver for zone reads
            player_id: For tracing
            player_name: For tracing

        Returns:
            ReadEvaluationResult with success, outcome, and reasoning
        """
        trace = get_trace_system()

        # Get player attributes
        awareness = getattr(player_attributes, 'awareness', 75)
        decision_making = getattr(player_attributes, 'decision_making', 75)
        poise = getattr(player_attributes, 'poise', 75)

        # =====================================================================
        # Gate 1: Minimum Awareness
        # =====================================================================
        if awareness < read.min_awareness:
            reason = f"awareness ({awareness}) below minimum ({read.min_awareness})"
            trace.trace(player_id, player_name, TraceCategory.DECISION,
                       f"[READ] {read.id}: DISABLED - {reason}")
            return ReadEvaluationResult(
                success=False,
                reasoning=reason,
            )

        # =====================================================================
        # Gate 2: Pressure Check
        # =====================================================================
        max_pressure = get_max_pressure_for_reads(poise)
        pressure_levels = ["clean", "light", "moderate", "heavy", "critical"]

        # Check if current pressure exceeds what poise allows
        current_idx = pressure_levels.index(pressure_level.lower()) if pressure_level.lower() in pressure_levels else 0
        max_idx = pressure_levels.index(max_pressure) if max_pressure in pressure_levels else 4

        if current_idx > max_idx:
            reason = f"pressure ({pressure_level}) exceeds poise threshold ({max_pressure})"
            trace.trace(player_id, player_name, TraceCategory.DECISION,
                       f"[READ] {read.id}: DISABLED - {reason}")
            return ReadEvaluationResult(
                success=False,
                reasoning=reason,
            )

        # Also check read-specific pressure threshold
        read_max_idx = pressure_levels.index(read.pressure_disabled_level) if read.pressure_disabled_level in pressure_levels else 3
        if current_idx >= read_max_idx:
            reason = f"pressure ({pressure_level}) disables read (threshold: {read.pressure_disabled_level})"
            trace.trace(player_id, player_name, TraceCategory.DECISION,
                       f"[READ] {read.id}: DISABLED - {reason}")
            return ReadEvaluationResult(
                success=False,
                reasoning=reason,
            )

        # =====================================================================
        # Step 1: Find Key Actor (awareness-gated)
        # =====================================================================
        accuracy, processing_time = get_awareness_accuracy(awareness)

        # Add variance to processing time
        if not is_deterministic():
            processing_time = recognition_delay(processing_time, awareness, 0.0)

        # Check if player identified key actor correctly
        if not is_deterministic() and random.random() > accuracy:
            reason = f"failed to identify key actor (awareness {awareness}, {accuracy:.0%} chance)"
            trace.trace(player_id, player_name, TraceCategory.DECISION,
                       f"[READ] {read.id}: FAILED - {reason}")
            return ReadEvaluationResult(
                success=False,
                reasoning=reason,
                processing_delay=processing_time,
            )

        # Find the key actor
        key_actor = _find_key_actor(
            read.key_actor_role,
            opponents,
            field_context,
            target_receiver_pos,
        )

        if key_actor is None:
            reason = f"key actor ({read.key_actor_role.value}) not found"
            trace.trace(player_id, player_name, TraceCategory.DECISION,
                       f"[READ] {read.id}: NO ACTOR - {reason}")
            return ReadEvaluationResult(
                success=False,
                reasoning=reason,
                processing_delay=processing_time,
            )

        key_actor_id = getattr(key_actor, 'id', 'unknown')

        # =====================================================================
        # Step 2: Evaluate Triggers (decision-making-gated)
        # =====================================================================
        dm_accuracy, can_anticipate = get_decision_making_accuracy(decision_making)

        # Get initial position for movement tracking
        initial_pos = self._initial_positions.get(key_actor_id)

        # Evaluate each trigger
        trigger_matched = None
        trigger_reason = ""

        for trigger in read.triggers:
            matched, reason = _evaluate_trigger(
                trigger,
                key_actor,
                initial_pos,
                current_time,
                time_since_snap,
            )
            if matched:
                trigger_matched = trigger.trigger_type
                trigger_reason = reason
                break

        # If no trigger matched, read doesn't apply
        if trigger_matched is None:
            reason = "no trigger condition met"
            trace.trace(player_id, player_name, TraceCategory.DECISION,
                       f"[READ] {read.id}: NO TRIGGER - key actor {key_actor_id}")
            return ReadEvaluationResult(
                success=False,
                key_actor_id=key_actor_id,
                reasoning=reason,
                processing_delay=processing_time,
            )

        # =====================================================================
        # Step 3: Select Outcome (decision-making-gated)
        # =====================================================================
        was_random = False

        # Check if decision-making is too low for correct interpretation
        if decision_making < read.min_decision_making:
            # Random outcome selection
            if read.outcomes:
                outcome = random.choice(read.outcomes)
                was_random = True
                reason = f"random outcome (decision_making {decision_making} < {read.min_decision_making})"
            else:
                return ReadEvaluationResult(
                    success=False,
                    key_actor_id=key_actor_id,
                    trigger_matched=trigger_matched,
                    reasoning="no outcomes defined",
                    processing_delay=processing_time,
                )
        else:
            # Check if player interprets trigger correctly
            if not is_deterministic() and random.random() > dm_accuracy:
                # Wrong interpretation - might select wrong outcome
                if len(read.outcomes) > 1 and random.random() > 0.5:
                    # Select alternate outcome instead of primary
                    alternates = read.get_alternate_outcomes()
                    if alternates:
                        outcome = alternates[0]
                        was_random = True
                        reason = f"misread trigger (decision_making {decision_making})"
                    else:
                        outcome = read.get_primary_outcome()
                        reason = f"correct read: {trigger_reason}"
                else:
                    outcome = read.get_primary_outcome()
                    reason = f"correct read: {trigger_reason}"
            else:
                # Correct interpretation - primary outcome
                outcome = read.get_primary_outcome()
                reason = f"correct read: {trigger_reason}"

        if outcome is None:
            return ReadEvaluationResult(
                success=False,
                key_actor_id=key_actor_id,
                trigger_matched=trigger_matched,
                reasoning="no valid outcome found",
                processing_delay=processing_time,
            )

        # Success!
        full_reason = f"{outcome.reasoning} ({reason})"
        trace.trace(player_id, player_name, TraceCategory.DECISION,
                   f"[READ] {read.id}: {outcome.target_position} ({outcome.target_route}) - {full_reason}")

        return ReadEvaluationResult(
            success=True,
            outcome=outcome,
            key_actor_id=key_actor_id,
            trigger_matched=trigger_matched,
            reasoning=full_reason,
            processing_delay=processing_time,
            was_random=was_random,
        )


# =============================================================================
# Global Instance
# =============================================================================

_evaluator = ReadEvaluator()


def get_read_evaluator() -> ReadEvaluator:
    """Get the global read evaluator instance."""
    return _evaluator


def reset_evaluator_for_play(opponents: List[Any]) -> None:
    """Reset the global evaluator for a new play."""
    _evaluator.reset_play(opponents)
