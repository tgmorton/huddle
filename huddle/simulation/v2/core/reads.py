"""Read System - Data structures for declarative AI decision-making.

This module defines the core data structures for the Read System, which transforms
hardcoded decision logic into declarative data. The universal pattern is:
"Watch a key actor, recognize a trigger, execute a predetermined outcome"

The Read System makes:
- AI more realistic (QBs throw based on play design, not just separation)
- Player ratings meaningful (elite awareness/decision-making QBs outperform low-rated)
- Behavior extensible (add new reads via data, not code changes)

Cross-brain benefit: Same system powers QB reads, DB anticipation, LB run fits, OL stunt pickups.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


# =============================================================================
# Enums
# =============================================================================

class BrainType(str, Enum):
    """Which brain type this read applies to."""
    QB = "qb"           # Quarterback reads
    DB = "db"           # Defensive back route anticipation
    LB = "lb"           # Linebacker run fit reads
    OL = "ol"           # Offensive line stunt pickup reads


class KeyActorRole(str, Enum):
    """The role of the key defender/player to read.

    These describe the ROLE the player is playing, not their position.
    The same CB might be the FLAT_CORNER on one play and DEEP_THIRD on another.
    """
    # Zone defenders (coverage-based)
    FLAT_CORNER = "flat_corner"           # CB playing flat zone (Cover 2/4)
    FLAT_DEFENDER = "flat_defender"       # Any flat zone player (CB, LB, S)
    HOOK_CURL_DEFENDER = "hook_curl"      # LB/S in hook/curl zone
    DEEP_THIRD = "deep_third"             # Deep third defender (Cover 3)
    DEEP_HALF = "deep_half"               # Deep half safety (Cover 2)
    MIDDLE_FIELD = "middle_field"         # Single high safety (Cover 1/3)

    # Man coverage
    MAN_DEFENDER = "man_defender"         # Defender in man on the key receiver

    # Run defense
    PLAY_SIDE_LB = "play_side_lb"         # LB to the run play side
    BACKSIDE_LB = "backside_lb"           # LB away from run
    PULLING_GUARD = "pulling_guard"       # Guard pulling on run
    LEAD_BLOCKER = "lead_blocker"         # FB/TE leading on run

    # Pass rush
    EDGE_RUSHER = "edge_rusher"           # DE/OLB rushing edge
    INTERIOR_RUSHER = "interior_rusher"   # DT/NT rushing interior

    # DB-specific (route anticipation)
    ASSIGNED_RECEIVER = "assigned_receiver"  # Receiver the DB is covering
    QB = "qb"                             # Quarterback (for eye reading)
    ROUTE_CROSSER = "route_crosser"       # Receiver crossing through zone
    VERTICAL_THREAT = "vertical_threat"   # Receiver running vertical route
    BALL = "ball"                         # The football (ball in air reads)
    FORMATION = "formation"               # Formation recognition

    # LB-specific (run defense)
    RUN_FLOW = "run_flow"                 # Overall offensive flow direction
    BALL_CARRIER = "ball_carrier"         # RB with the ball
    FULLBACK = "fullback"                 # FB on run plays


class TriggerType(str, Enum):
    """Types of triggers that can activate a read.

    Movement triggers describe what the key actor is doing.
    """
    # Zone triggers (flat defender movement)
    SINKS = "sinks"               # Defender drops deeper (vacate flat)
    WIDENS = "widens"             # Defender expands toward sideline
    SQUATS = "squats"             # Defender sits on route underneath
    JUMPS = "jumps"               # Defender breaks on route aggressively

    # Coverage triggers
    CARRIES_VERTICAL = "carries"  # Defender follows receiver vertically
    PASSES_OFF = "passes_off"     # Defender passes receiver to next zone
    OPENS_HIPS = "opens_hips"     # Defender commits to receiver direction

    # Run defense triggers
    FLOWS_PLAYSIDE = "flows_play" # LB flows to play side
    OVERRUNS = "overruns"         # LB overcommits to play side
    FILLS_GAP = "fills_gap"       # LB fills specific gap
    SPILLS = "spills"             # Forces play outside

    # Timing triggers
    COMMITS_EARLY = "early"       # Defender commits before ball is thrown
    COMMITS_LATE = "late"         # Defender reacts slowly

    # Position triggers
    INSIDE_LEVERAGE = "inside"    # Defender has inside position
    OUTSIDE_LEVERAGE = "outside"  # Defender has outside position
    TRAIL_POSITION = "trail"      # Defender is trailing receiver

    # DB-specific triggers (route anticipation)
    INSIDE_RELEASE = "inside_release"   # Receiver releases inside at LOS
    OUTSIDE_RELEASE = "outside_release" # Receiver releases outside at LOS
    VERTICAL_STEM = "vertical_stem"     # Receiver stems vertical
    DECELERATION = "deceleration"       # Receiver slowing down (break coming)
    AT_BREAK_DEPTH = "at_break_depth"   # Receiver at typical break depth
    HIP_ROTATION = "hip_rotation"       # Receiver's hips rotating (break imminent)
    STARING_DOWN = "staring_down"       # QB staring down a receiver
    ENTERS_ZONE = "enters_zone"         # Receiver entering DB's zone
    INSIDE_MOVE = "inside_move"         # Receiver making inside move at press
    OUTSIDE_MOVE = "outside_move"       # Receiver making outside move at press
    BALL_THROWN = "ball_thrown"         # Ball is in the air
    TRIPS_ALIGNMENT = "trips_alignment" # 3 receivers to one side
    BUNCH_ALIGNMENT = "bunch_alignment" # Receivers bunched together

    # LB-specific triggers (run fit reads)
    GUARD_PULL = "guard_pull"           # Guard pulling (indicates run direction)
    TRAP_BLOCK = "trap_block"           # Trap block pattern
    ZONE_BLOCK = "zone_block"           # Zone blocking scheme
    GAP_BLOCK = "gap_block"             # Gap/power blocking scheme
    FULLBACK_LEAD = "fullback_lead"     # FB leading through hole
    COUNTER_STEP = "counter_step"       # Back taking counter step (misdirection)
    STRETCH_FLOW = "stretch_flow"       # Stretch run flow
    DIVE_FLOW = "dive_flow"             # Inside dive run flow
    PLAY_ACTION = "play_action"         # Play action fake
    SCREEN_SET = "screen_set"           # Screen blocking pattern


@dataclass
class TriggerCondition:
    """A specific trigger that activates a read outcome.

    Attributes:
        trigger_type: What movement/action triggers this
        threshold: Distance/angle threshold for trigger (context-dependent)
        direction: Optional direction qualifier (e.g., "inside", "vertical")
        timing_window: When trigger is valid (min_time, max_time) since snap
    """
    trigger_type: TriggerType
    threshold: float = 1.0  # Default threshold in yards
    direction: Optional[str] = None
    timing_window: tuple[float, float] = (0.0, 10.0)  # Default: always valid

    def __post_init__(self):
        """Ensure timing_window is a tuple."""
        if isinstance(self.timing_window, list):
            self.timing_window = tuple(self.timing_window)


@dataclass
class ReadOutcome:
    """The result when a read is triggered.

    Attributes:
        target_position: Position slot to throw to (e.g., "z", "slot_r", "rb")
        target_route: What route the target is running (for validation)
        priority: Priority of this outcome (1 = primary, 2 = alternate)
        reasoning: Human-readable explanation for traces
        adjustment: Optional adjustment to throw (e.g., "far_shoulder", "back_hip")
    """
    target_position: str
    target_route: str
    priority: int
    reasoning: str
    adjustment: Optional[str] = None


# =============================================================================
# Main Data Structure
# =============================================================================

@dataclass
class ReadDefinition:
    """A complete read definition - the unit of declarative AI data.

    This represents one "if-then" decision:
    "When running [concept] against [coverage], watch [key_actor].
     If they [trigger], throw to [outcome]."

    Attributes:
        id: Unique identifier (e.g., "smash_cover2", "slant_flat_cover3")
        name: Human-readable name
        brain_type: Which brain uses this read (QB, DB, LB, OL)
        play_concept: Play concept this read applies to (e.g., "smash", "flood")
        applicable_coverages: List of coverages this works against (empty = all)

        key_actor_role: What defender to watch
        triggers: List of trigger conditions (any match activates)
        outcomes: Ordered list of outcomes (try in priority order)

        min_awareness: Minimum awareness to use this read
        min_decision_making: Minimum decision-making for correct interpretation
        pressure_disabled_level: Pressure level that disables this read
    """
    # Identity
    id: str
    name: str
    brain_type: BrainType
    play_concept: str

    # Applicability
    applicable_coverages: List[str] = field(default_factory=list)

    # The read itself
    key_actor_role: KeyActorRole = KeyActorRole.FLAT_DEFENDER
    triggers: List[TriggerCondition] = field(default_factory=list)
    outcomes: List[ReadOutcome] = field(default_factory=list)

    # Attribute gates
    min_awareness: int = 60           # Below this: read disabled entirely
    min_decision_making: int = 50     # Below this: random outcome selection
    pressure_disabled_level: str = "heavy"  # At this pressure, read disabled

    def get_primary_outcome(self) -> Optional[ReadOutcome]:
        """Get the primary (priority=1) outcome."""
        for outcome in self.outcomes:
            if outcome.priority == 1:
                return outcome
        return self.outcomes[0] if self.outcomes else None

    def get_alternate_outcomes(self) -> List[ReadOutcome]:
        """Get non-primary outcomes in priority order."""
        return sorted(
            [o for o in self.outcomes if o.priority > 1],
            key=lambda o: o.priority
        )

    def applies_to_coverage(self, coverage: str) -> bool:
        """Check if this read applies to the given coverage."""
        if not self.applicable_coverages:
            return True  # Empty list = applies to all
        return coverage.lower() in [c.lower() for c in self.applicable_coverages]

    def describe(self) -> str:
        """Human-readable description of this read."""
        lines = [
            f"=== {self.name} ===",
            f"ID: {self.id}",
            f"Brain: {self.brain_type.value}",
            f"Concept: {self.play_concept}",
        ]

        if self.applicable_coverages:
            lines.append(f"Coverages: {', '.join(self.applicable_coverages)}")
        else:
            lines.append("Coverages: All")

        lines.append(f"Key Actor: {self.key_actor_role.value}")

        if self.triggers:
            trigger_strs = [f"{t.trigger_type.value}" for t in self.triggers]
            lines.append(f"Triggers: {', '.join(trigger_strs)}")

        lines.append("")
        lines.append("Outcomes:")
        for outcome in sorted(self.outcomes, key=lambda o: o.priority):
            lines.append(f"  {outcome.priority}. {outcome.target_position} ({outcome.target_route})")
            lines.append(f"     -> {outcome.reasoning}")

        lines.append("")
        lines.append("Attribute Gates:")
        lines.append(f"  Min Awareness: {self.min_awareness}")
        lines.append(f"  Min Decision-Making: {self.min_decision_making}")
        lines.append(f"  Disabled at: {self.pressure_disabled_level} pressure")

        return "\n".join(lines)


# =============================================================================
# Attribute Scaling Tables
# =============================================================================

# Awareness affects key actor identification accuracy and processing time
AWARENESS_SCALING = {
    # (min_rating, max_rating): (accuracy, processing_time)
    (90, 100): (0.98, 0.10),  # Elite: 98% accurate, 0.1s processing
    (80, 89):  (0.90, 0.20),  # Very Good: 90% accurate, 0.2s
    (70, 79):  (0.80, 0.30),  # Good: 80% accurate, 0.3s
    (60, 69):  (0.65, 0.40),  # Average: 65% accurate, 0.4s
    (0, 59):   (0.00, 0.00),  # Disabled: read system not available
}

# Decision-making affects trigger interpretation accuracy
DECISION_MAKING_SCALING = {
    # (min_rating, max_rating): (accuracy, can_anticipate)
    (90, 100): (0.95, True),   # Elite: 95% correct, can anticipate
    (80, 89):  (0.85, True),   # Very Good: 85% correct, occasional late
    (70, 79):  (0.70, False),  # Good: 70% correct, sometimes wrong
    (60, 69):  (0.55, False),  # Average: 55% correct, often wrong
    (0, 59):   (0.00, False),  # Random: ignores trigger, random outcome
}

# Poise affects when reads are disabled by pressure
POISE_PRESSURE_THRESHOLDS = {
    # poise_rating: highest_pressure_level_for_reads
    85: "critical",   # Elite poise: reads work even under heavy pressure
    70: "heavy",      # Good poise: reads work up to moderate pressure
    55: "moderate",   # Average poise: reads only in light pressure
    0: "light",       # Low poise: reads only in clean pocket
}


def get_awareness_accuracy(awareness: int) -> tuple[float, float]:
    """Get accuracy and processing time for given awareness rating.

    Returns:
        (accuracy, processing_time) - accuracy 0-1, time in seconds
    """
    for (min_r, max_r), (acc, time) in AWARENESS_SCALING.items():
        if min_r <= awareness <= max_r:
            return (acc, time)
    return (0.0, 0.0)


def get_decision_making_accuracy(decision_making: int) -> tuple[float, bool]:
    """Get interpretation accuracy for given decision-making rating.

    Returns:
        (accuracy, can_anticipate) - accuracy 0-1, whether can anticipate triggers
    """
    for (min_r, max_r), (acc, antic) in DECISION_MAKING_SCALING.items():
        if min_r <= decision_making <= max_r:
            return (acc, antic)
    return (0.0, False)


def get_max_pressure_for_reads(poise: int) -> str:
    """Get the highest pressure level where reads still work.

    Returns:
        Pressure level string (e.g., "heavy", "moderate")
    """
    for threshold, level in sorted(POISE_PRESSURE_THRESHOLDS.items(), reverse=True):
        if poise >= threshold:
            return level
    return "light"
