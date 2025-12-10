"""
Pocket collapse simulation with engagement-based blocking.

Models 5 OL vs variable DL (3-5 rushers) with a stationary QB.
Supports blocking assignments (man, zone) and tracks animation states.

Coordinate System (pocket_sim internal):
    x = lateral (negative = left, positive = right)
    y = depth (0 = LOS, positive = toward backfield/QB)

Note: This differs from the unified coordinate system where y-positive
is downfield. Use convert_pocket_to_unified() when integrating.
"""

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

# Use shared Vec2 implementation
from .shared import Vec2


# =============================================================================
# Enums
# =============================================================================

class EngagementState(str, Enum):
    """State of a blocker-rusher engagement."""
    PRE_SNAP = "pre_snap"
    ENGAGED = "engaged"
    RUSHER_WINNING = "rusher_winning"
    BLOCKER_WINNING = "blocker_winning"
    SHED = "shed"
    PANCAKE = "pancake"


class PlayerRole(str, Enum):
    """Player positions."""
    # Offense
    QB = "qb"
    LT = "lt"  # Left Tackle
    LG = "lg"  # Left Guard
    C = "c"    # Center
    RG = "rg"  # Right Guard
    RT = "rt"  # Right Tackle
    # Defense
    LE = "le"   # Left End
    DT_L = "dt_l"  # Left Defensive Tackle (4-man front)
    NT = "nt"   # Nose Tackle (3-man front)
    DT_R = "dt_r"  # Right Defensive Tackle (4-man front)
    RE = "re"   # Right End
    # Blitzers
    BLITZ_L = "blitz_l"
    BLITZ_R = "blitz_r"


class AnimationState(str, Enum):
    """Current animation state for sprite rendering."""
    # Common
    STANCE = "stance"
    # Blocker animations
    PASS_SET = "pass_set"
    ENGAGED_NEUTRAL = "engaged_neutral"
    ENGAGED_WINNING = "engaged_winning"
    ENGAGED_LOSING = "engaged_losing"
    PANCAKE_BLOCK = "pancake"
    BEATEN = "beaten"
    # Rusher animations
    RUSH_BURST = "rush_burst"
    BULL_RUSH = "bull_rush"
    SWIM_MOVE = "swim_move"
    SPIN_MOVE = "spin_move"
    RIP_MOVE = "rip_move"
    SHED_FREE = "shed_free"
    PURSUE = "pursue"
    SACK = "sack"
    PANCAKED = "pancaked"
    # Stunt animations
    STUNT_CRASH = "stunt_crash"   # Penetrator crashing inside
    STUNT_LOOP = "stunt_loop"     # Looper circling around
    STUNT_HOLD = "stunt_hold"     # Waiting for stunt timing
    # QB animations
    DROPBACK = "dropback"
    POCKET_SET = "pocket_set"
    PRESSURED = "pressured"
    STEP_UP = "step_up"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    SCRAMBLE = "scramble"
    THROWING = "throwing"
    THROW_COMPLETE = "throw_complete"
    SACKED = "sacked"


class AssignmentType(str, Enum):
    """Type of blocking assignment."""
    MAN = "man"       # Block specific rusher
    ZONE = "zone"     # Block anyone in zone
    HELP = "help"     # Double-team assist on specific rusher
    FREE = "free"     # No assignment - help nearest or watch gap


class GapSide(str, Enum):
    """Which side a free blocker should watch/help."""
    LEFT = "left"
    RIGHT = "right"
    INSIDE = "inside"  # Help center/guards
    OUTSIDE = "outside"  # Help tackles


class DefensiveFront(str, Enum):
    """Defensive front configuration."""
    THREE_MAN = "3_man"   # LE, NT, RE
    FOUR_MAN = "4_man"    # LE, DT_L, DT_R, RE
    FIVE_MAN = "5_man"    # 4-man + 1 blitzer


class StuntType(str, Enum):
    """Type of defensive line stunt."""
    NONE = "none"
    ET_LEFT = "et_left"     # Left End crashes in, Left DT loops out
    ET_RIGHT = "et_right"   # Right End crashes in, Right DT loops out
    TE_LEFT = "te_left"     # Left DT penetrates, Left End loops behind
    TE_RIGHT = "te_right"   # Right DT penetrates, Right End loops behind
    TT_TWIST = "tt_twist"   # Interior DTs exchange gaps


class StuntPhase(str, Enum):
    """Phase of a stunt execution."""
    PRE_STUNT = "pre_stunt"       # Before stunt begins
    PENETRATOR_GO = "penetrator"  # First rusher penetrates/crashes
    LOOPER_GO = "looper"          # Second rusher loops around
    COMPLETE = "complete"         # Stunt finished, normal rush


class QBAction(str, Enum):
    """Current QB action in the pocket."""
    SETTING = "setting"           # Initial dropback/set
    SCANNING = "scanning"         # In pocket, looking for receivers
    STEPPING_UP = "stepping_up"   # Moving forward to avoid edge pressure
    SLIDING = "sliding"           # Moving laterally to avoid pressure
    SCRAMBLING = "scrambling"     # Pocket collapsed, trying to escape
    THROWING = "throwing"         # In throwing motion
    THROW_AWAY = "throw_away"     # Throwing ball away under pressure
    SACKED = "sacked"             # Got sacked


class PressureLevel(str, Enum):
    """QB's perceived pressure level."""
    CLEAN = "clean"               # No pressure
    LIGHT = "light"               # Some pressure, can still throw
    MODERATE = "moderate"         # Need to move soon
    HEAVY = "heavy"               # Must move or throw now
    CRITICAL = "critical"         # About to be sacked


class RusherMove(str, Enum):
    """Pass rush moves with associated characteristics."""
    BULL_RUSH = "bull_rush"      # Power move: 5-7 ticks duration
    SWIM = "swim"                # Finesse: 3-4 ticks
    SPIN = "spin"                # High risk/reward: 2-3 ticks
    RIP = "rip"                  # Hybrid: 4-5 ticks
    LONG_ARM = "long_arm"        # Counter to double team: 4-6 ticks


class BlockerResponse(str, Enum):
    """Blocker counter-techniques."""
    ANCHOR = "anchor"            # Set feet, absorb power
    MIRROR = "mirror"            # Lateral movement, stay in front
    RE_FIT = "re_fit"            # Reset hands after being beat
    RE_LEVERAGE = "re_leverage"  # Counter spin/rip with leverage change
    PUNCH = "punch"              # Aggressive hand strike


class RushLane(str, Enum):
    """Pass rush lanes for containment."""
    FAR_LEFT = "far_left"        # Outside left tackle
    LEFT_EDGE = "left_edge"      # Left tackle area
    LEFT_B = "left_b"            # Between LT and LG
    LEFT_A = "left_a"            # Between LG and C
    CENTER = "center"            # Over center
    RIGHT_A = "right_a"          # Between C and RG
    RIGHT_B = "right_b"          # Between RG and RT
    RIGHT_EDGE = "right_edge"    # Right tackle area
    FAR_RIGHT = "far_right"      # Outside right tackle


# =============================================================================
# Engagement Model Constants
# =============================================================================

# Move durations (min, max ticks)
MOVE_DURATIONS: dict[RusherMove, tuple[int, int]] = {
    RusherMove.BULL_RUSH: (5, 7),
    RusherMove.SWIM: (3, 4),
    RusherMove.SPIN: (2, 3),
    RusherMove.RIP: (4, 5),
    RusherMove.LONG_ARM: (4, 6),
}

# Move matchup matrix: rusher move vs blocker response
# Positive = rusher advantage, negative = blocker advantage
MOVE_MATCHUP_MATRIX: dict[RusherMove, dict[BlockerResponse, float]] = {
    RusherMove.BULL_RUSH: {
        BlockerResponse.ANCHOR: -5.0,       # Anchor counters bull rush
        BlockerResponse.MIRROR: 3.0,        # Bull beats lateral movement
        BlockerResponse.RE_FIT: 2.0,        # Power beats hand reset
        BlockerResponse.RE_LEVERAGE: 0.0,   # Neutral
        BlockerResponse.PUNCH: -2.0,        # Punch disrupts bull
    },
    RusherMove.SWIM: {
        BlockerResponse.ANCHOR: 4.0,        # Swim beats anchored blocker
        BlockerResponse.MIRROR: -3.0,       # Mirror counters swim
        BlockerResponse.RE_FIT: -2.0,       # Re-fit catches swim
        BlockerResponse.RE_LEVERAGE: 1.0,   # Slight advantage
        BlockerResponse.PUNCH: 5.0,         # Swim evades punch
    },
    RusherMove.SPIN: {
        BlockerResponse.ANCHOR: 6.0,        # Spin beats stationary
        BlockerResponse.MIRROR: 2.0,        # Spin beats lateral (surprise)
        BlockerResponse.RE_FIT: -4.0,       # Re-fit catches spin
        BlockerResponse.RE_LEVERAGE: -6.0,  # Re-leverage destroys spin
        BlockerResponse.PUNCH: 3.0,         # Spin evades punch
    },
    RusherMove.RIP: {
        BlockerResponse.ANCHOR: 2.0,        # Rip gets under anchor
        BlockerResponse.MIRROR: 0.0,        # Neutral
        BlockerResponse.RE_FIT: 3.0,        # Rip beats reset
        BlockerResponse.RE_LEVERAGE: -3.0,  # Re-leverage counters rip
        BlockerResponse.PUNCH: -1.0,        # Punch disrupts rip
    },
    RusherMove.LONG_ARM: {
        BlockerResponse.ANCHOR: 4.0,        # Long arm creates space
        BlockerResponse.MIRROR: 2.0,        # Long arm controls
        BlockerResponse.RE_FIT: 0.0,        # Neutral
        BlockerResponse.RE_LEVERAGE: 3.0,   # Long arm beats leverage
        BlockerResponse.PUNCH: -4.0,        # Punch inside long arm
    },
}

# Optimal blocker response for each rusher move
OPTIMAL_RESPONSES: dict[RusherMove, BlockerResponse] = {
    RusherMove.BULL_RUSH: BlockerResponse.ANCHOR,
    RusherMove.SWIM: BlockerResponse.MIRROR,
    RusherMove.SPIN: BlockerResponse.RE_LEVERAGE,
    RusherMove.RIP: BlockerResponse.RE_LEVERAGE,
    RusherMove.LONG_ARM: BlockerResponse.PUNCH,
}

# Lane X-positions (relative to center)
LANE_POSITIONS: dict[RushLane, float] = {
    RushLane.FAR_LEFT: -4.5,
    RushLane.LEFT_EDGE: -3.0,
    RushLane.LEFT_B: -2.25,
    RushLane.LEFT_A: -0.75,
    RushLane.CENTER: 0.0,
    RushLane.RIGHT_A: 0.75,
    RushLane.RIGHT_B: 2.25,
    RushLane.RIGHT_EDGE: 3.0,
    RushLane.FAR_RIGHT: 4.5,
}

# Accumulated advantage thresholds
ACCUMULATED_SHED_THRESHOLD = 65.0     # Rusher sheds block (requires sustained winning)
ACCUMULATED_PANCAKE_THRESHOLD = -90.0  # Blocker pancakes rusher (very rare)
ACCUMULATED_WINNING_THRESHOLD = 12.0   # "Winning" state

# Advantage mechanics
ADVANTAGE_DECAY = 0.92                # Per-tick decay (slower = harder to accumulate quickly)
MOMENTUM_BONUS_RUSHER = 2.0           # Bonus per consecutive winning tick (rusher)
MOMENTUM_BONUS_BLOCKER = 2.0          # Bonus per consecutive winning tick (blocker)
MAX_MOMENTUM_TICKS = 5                # Cap on consecutive win bonus

# Time-based fatigue/pressure creep - blockers tire, rushers gain advantage over time
FATIGUE_START_TICK = 18               # When fatigue starts affecting blockers
FATIGUE_RUSHER_BONUS_PER_TICK = 1.0   # Rusher advantage bonus per tick after fatigue starts
MAX_FATIGUE_BONUS = 15.0              # Cap on total fatigue bonus

# Base rusher advantage - DL knows the snap count and can attack first
BASE_RUSHER_ADVANTAGE = 1.5           # Small inherent rusher edge per tick

# Double team mechanics
BASE_DOUBLE_TEAM_BONUS = 15.0
MAX_DOUBLE_TEAM_BONUS = 22.0
MIN_DOUBLE_TEAM_BONUS = 5.0
COORDINATION_DECAY_PER_TICK = 0.02

# Free rusher pathing
EDGE_ARC_WIDTH = 2.5                  # Yards of arc for edge rushers
INTERIOR_ARC_WIDTH = 0.8              # Yards for interior
ARC_SPEED_PENALTY = 0.85              # Speed reduction while arcing
STRAIGHT_LINE_THRESHOLD = 3.0         # Go straight when this close


# =============================================================================
# Data Classes
# =============================================================================

# Vec2 is now imported from .shared


@dataclass
class PlayerAttributes:
    """Attributes relevant to blocking/rushing."""
    strength: int = 75
    speed: int = 75
    agility: int = 75
    pass_block: int = 75
    awareness: int = 75
    block_shedding: int = 75
    power_moves: int = 75
    finesse_moves: int = 75


@dataclass
class EngagementAdvantage:
    """Tracks accumulated advantage in a blocker-rusher engagement.

    Positive values favor the rusher, negative favor the blocker.
    Values accumulate over time with decay, creating momentum.
    """
    accumulated_margin: float = 0.0       # Current accumulated advantage
    last_tick_margin: float = 0.0         # Most recent tick's contest result
    consecutive_wins: int = 0             # Ticks in a row one side has won
    winning_side: Optional[str] = None    # "rusher" or "blocker" or None
    peak_rusher_advantage: float = 0.0    # Highest rusher advantage reached
    peak_blocker_advantage: float = 0.0   # Lowest (most negative) advantage
    ticks_engaged: int = 0                # How long engaged

    def to_dict(self) -> dict:
        return {
            "accumulated_margin": round(self.accumulated_margin, 2),
            "last_tick_margin": round(self.last_tick_margin, 2),
            "consecutive_wins": self.consecutive_wins,
            "winning_side": self.winning_side,
            "ticks_engaged": self.ticks_engaged,
        }


@dataclass
class MoveState:
    """Tracks current move execution for a rusher."""
    current_move: RusherMove = RusherMove.BULL_RUSH
    move_start_tick: int = 0
    move_duration: int = 5                # How many ticks this move lasts
    ticks_in_move: int = 0

    # Move selection weights (learned from success/failure)
    move_preferences: dict = field(default_factory=lambda: {
        RusherMove.BULL_RUSH: 1.0,
        RusherMove.SWIM: 1.0,
        RusherMove.SPIN: 1.0,
        RusherMove.RIP: 1.0,
        RusherMove.LONG_ARM: 0.5,  # Lower default - only vs double teams
    })

    last_move_success: bool = False

    def to_dict(self) -> dict:
        return {
            "current_move": self.current_move.value,
            "move_duration": self.move_duration,
            "ticks_in_move": self.ticks_in_move,
        }


@dataclass
class DoubleTeamState:
    """Tracks double team dynamics."""
    primary_blocker_role: PlayerRole
    help_blocker_role: PlayerRole

    # Advantage distribution (sums to 1.0)
    primary_contribution: float = 0.6
    help_contribution: float = 0.4

    # Split tracking
    rusher_splitting: bool = False       # Is rusher trying to split?
    split_progress: float = 0.0          # 0.0 to 1.0 (1.0 = split successful)

    # Blocker coordination
    coordination_score: float = 1.0      # Degrades if rusher splits

    def to_dict(self) -> dict:
        return {
            "primary_role": self.primary_blocker_role.value,
            "help_role": self.help_blocker_role.value,
            "coordination": round(self.coordination_score, 2),
            "split_progress": round(self.split_progress, 2),
        }


@dataclass
class RusherPath:
    """Tracks free rusher's path to QB."""
    target_position: Vec2 = field(default_factory=Vec2)
    assigned_lane: RushLane = RushLane.CENTER
    current_lane: RushLane = RushLane.CENTER

    # Arc parameters
    arc_width: float = 0.0
    arc_phase: float = 0.0               # 0.0 to 1.0 progress

    # Speed modifiers
    base_speed: float = 0.3
    current_speed: float = 0.3

    # Containment
    must_contain: bool = False
    contain_x: float = 0.0

    def to_dict(self) -> dict:
        return {
            "assigned_lane": self.assigned_lane.value,
            "arc_phase": round(self.arc_phase, 2),
            "must_contain": self.must_contain,
        }


@dataclass
class Player:
    """A player in the pocket simulation."""
    id: UUID = field(default_factory=uuid4)
    role: PlayerRole = PlayerRole.NT
    position: Vec2 = field(default_factory=Vec2)
    attributes: PlayerAttributes = field(default_factory=PlayerAttributes)

    # State
    is_free: bool = False
    is_down: bool = False

    # Animation
    animation: AnimationState = AnimationState.STANCE
    facing: Vec2 = field(default_factory=lambda: Vec2(1, 0))  # Direction facing

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "role": self.role.value,
            "position": self.position.to_dict(),
            "is_free": self.is_free,
            "is_down": self.is_down,
            "animation": self.animation.value,
            "facing": self.facing.to_dict(),
        }


@dataclass
class BlockingAssignment:
    """A single blocking assignment for one blocker."""
    blocker_role: PlayerRole
    assignment_type: AssignmentType
    target_role: Optional[PlayerRole] = None  # For MAN/HELP assignments
    zone_center: Optional[Vec2] = None        # For ZONE assignments
    zone_width: float = 2.0                   # Zone width in yards
    help_side: Optional[GapSide] = None       # For FREE assignments - which side to watch/help

    def to_dict(self) -> dict:
        return {
            "blocker_role": self.blocker_role.value,
            "assignment_type": self.assignment_type.value,
            "target_role": self.target_role.value if self.target_role else None,
            "zone_center": self.zone_center.to_dict() if self.zone_center else None,
            "help_side": self.help_side.value if self.help_side else None,
        }


@dataclass
class BlockingScheme:
    """Complete blocking scheme for the offensive line."""
    name: str
    assignments: list[BlockingAssignment]

    def get_assignment(self, blocker_role: PlayerRole) -> Optional[BlockingAssignment]:
        """Get assignment for a specific blocker."""
        for assignment in self.assignments:
            if assignment.blocker_role == blocker_role:
                return assignment
        return None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "assignments": [a.to_dict() for a in self.assignments],
        }


@dataclass
class DefensiveStunt:
    """A coordinated defensive line stunt."""
    stunt_type: StuntType
    penetrator_role: PlayerRole    # First mover (crashes/penetrates)
    looper_role: PlayerRole        # Second mover (loops around)
    phase: StuntPhase = StuntPhase.PRE_STUNT
    start_tick: int = 3            # When penetrator starts (after snap)
    loop_delay: int = 5            # Ticks after penetrator before looper goes

    # Path targets for the looper (relative to start position)
    loop_path: list[Vec2] = field(default_factory=list)
    current_path_index: int = 0

    def to_dict(self) -> dict:
        return {
            "stunt_type": self.stunt_type.value,
            "penetrator_role": self.penetrator_role.value,
            "looper_role": self.looper_role.value,
            "phase": self.phase.value,
        }


class DropbackType(str, Enum):
    """Type of QB dropback."""
    THREE_STEP = "3_step"    # Quick pass - 3-5 yards
    FIVE_STEP = "5_step"     # Standard pass - 5-7 yards
    SEVEN_STEP = "7_step"    # Deep pass - 7-9 yards
    SHOTGUN = "shotgun"      # Already in position - no dropback


# Dropback configuration: (target_depth, ticks_to_complete)
DROPBACK_CONFIG: dict[DropbackType, tuple[float, int]] = {
    DropbackType.THREE_STEP: (4.0, 6),    # 4 yards deep, 6 ticks (~0.6s)
    DropbackType.FIVE_STEP: (6.0, 10),    # 6 yards deep, 10 ticks (~1.0s)
    DropbackType.SEVEN_STEP: (8.0, 14),   # 8 yards deep, 14 ticks (~1.4s)
    DropbackType.SHOTGUN: (7.0, 0),       # Already at depth, no dropback
}


@dataclass
class QBState:
    """Tracks QB's current state in the pocket."""
    action: QBAction = QBAction.SETTING
    pressure_level: PressureLevel = PressureLevel.CLEAN
    throw_timer: int = 0           # Ticks until throw (0 = not throwing)
    throw_target_tick: int = 30    # When QB wants to throw (3 seconds)
    escape_direction: Optional[Vec2] = None  # Direction QB is trying to escape

    # Pressure tracking
    pressure_left: float = 0.0     # Pressure from left side (0-1)
    pressure_right: float = 0.0    # Pressure from right side (0-1)
    pressure_front: float = 0.0    # Pressure up the middle (0-1)

    # Movement limits
    initial_position: Optional[Vec2] = None
    max_stepup: float = 3.0        # Max yards QB can step up
    max_slide: float = 4.0         # Max yards QB can slide laterally

    # Dropback state
    dropback_type: DropbackType = DropbackType.SHOTGUN
    dropback_complete: bool = True        # True if dropback finished
    dropback_target_depth: float = 7.0    # Target y position after dropback
    dropback_ticks_remaining: int = 0     # Ticks left in dropback

    # Scramble state
    scramble_committed: bool = False      # QB has committed to scrambling (can't go back)
    scramble_ticks: int = 0               # Ticks spent scrambling
    scramble_target: Optional[Vec2] = None  # Target point for scramble
    mobility: int = 75                    # QB mobility rating (affects scramble speed)

    def to_dict(self) -> dict:
        return {
            "action": self.action.value,
            "pressure_level": self.pressure_level.value,
            "throw_timer": self.throw_timer,
            "throw_target_tick": self.throw_target_tick,
            "pressure_left": round(self.pressure_left, 2),
            "pressure_right": round(self.pressure_right, 2),
            "pressure_front": round(self.pressure_front, 2),
            "dropback_type": self.dropback_type.value,
            "dropback_complete": self.dropback_complete,
            "scramble_committed": self.scramble_committed,
            "scramble_ticks": self.scramble_ticks,
            "mobility": self.mobility,
        }


@dataclass
class Engagement:
    """A blocker-rusher engagement with accumulated advantage tracking."""
    blockers: list[Player]  # Can be 1-2 blockers (for double teams)
    rusher: Player
    contact_point: Vec2
    state: EngagementState = EngagementState.PRE_SNAP
    rush_direction: Vec2 = field(default_factory=Vec2)

    # Current move being used by rusher (animation)
    rush_move: AnimationState = AnimationState.RUSH_BURST

    # NEW: Accumulated advantage system
    advantage: EngagementAdvantage = field(default_factory=EngagementAdvantage)

    # NEW: Move state machine
    move_state: MoveState = field(default_factory=MoveState)
    current_blocker_response: BlockerResponse = BlockerResponse.ANCHOR

    # NEW: Double team state (if applicable)
    double_team_state: Optional[DoubleTeamState] = None

    # Stats (legacy compatibility)
    rusher_wins: int = 0
    blocker_wins: int = 0
    neutral: int = 0

    @property
    def is_double_team(self) -> bool:
        return len(self.blockers) > 1

    def to_dict(self) -> dict:
        return {
            "blocker_ids": [str(b.id) for b in self.blockers],
            "blocker_roles": [b.role.value for b in self.blockers],
            "rusher_id": str(self.rusher.id),
            "rusher_role": self.rusher.role.value,
            "contact_point": self.contact_point.to_dict(),
            "state": self.state.value,
            "rush_direction": self.rush_direction.to_dict(),
            "rush_move": self.rush_move.value,
            "is_double_team": self.is_double_team,
            "advantage": self.advantage.to_dict(),
            "move_state": self.move_state.to_dict(),
            "blocker_response": self.current_blocker_response.value,
            "double_team": self.double_team_state.to_dict() if self.double_team_state else None,
        }


@dataclass
class PocketSimState:
    """Full state of the pocket simulation."""
    qb: Player
    blockers: list[Player]
    rushers: list[Player]
    engagements: list[Engagement]
    blocking_scheme: BlockingScheme
    defensive_front: DefensiveFront
    stunt: Optional[DefensiveStunt] = None
    qb_state: Optional[QBState] = None

    tick: int = 0
    is_complete: bool = False
    result: str = "in_progress"

    def to_dict(self) -> dict:
        return {
            "qb": self.qb.to_dict(),
            "blockers": [b.to_dict() for b in self.blockers],
            "rushers": [r.to_dict() for r in self.rushers],
            "engagements": [e.to_dict() for e in self.engagements],
            "blocking_scheme": self.blocking_scheme.to_dict(),
            "defensive_front": self.defensive_front.value,
            "stunt": self.stunt.to_dict() if self.stunt else None,
            "qb_state": self.qb_state.to_dict() if self.qb_state else None,
            "tick": self.tick,
            "is_complete": self.is_complete,
            "result": self.result,
        }


# =============================================================================
# Blocking Schemes
# =============================================================================

def create_man_protection(front: DefensiveFront) -> BlockingScheme:
    """Create basic man protection scheme."""
    if front == DefensiveFront.THREE_MAN:
        return BlockingScheme(
            name="Man Protection (3-man)",
            assignments=[
                BlockingAssignment(PlayerRole.LT, AssignmentType.MAN, PlayerRole.LE),
                BlockingAssignment(PlayerRole.LG, AssignmentType.FREE),  # Check blitz
                BlockingAssignment(PlayerRole.C, AssignmentType.MAN, PlayerRole.NT),
                BlockingAssignment(PlayerRole.RG, AssignmentType.FREE),  # Check blitz
                BlockingAssignment(PlayerRole.RT, AssignmentType.MAN, PlayerRole.RE),
            ]
        )
    elif front == DefensiveFront.FOUR_MAN:
        return BlockingScheme(
            name="Man Protection (4-man)",
            assignments=[
                BlockingAssignment(PlayerRole.LT, AssignmentType.MAN, PlayerRole.LE),
                BlockingAssignment(PlayerRole.LG, AssignmentType.MAN, PlayerRole.DT_L),
                BlockingAssignment(PlayerRole.C, AssignmentType.FREE),
                BlockingAssignment(PlayerRole.RG, AssignmentType.MAN, PlayerRole.DT_R),
                BlockingAssignment(PlayerRole.RT, AssignmentType.MAN, PlayerRole.RE),
            ]
        )
    else:  # FIVE_MAN
        return BlockingScheme(
            name="Man Protection (5-man)",
            assignments=[
                BlockingAssignment(PlayerRole.LT, AssignmentType.MAN, PlayerRole.LE),
                BlockingAssignment(PlayerRole.LG, AssignmentType.MAN, PlayerRole.DT_L),
                BlockingAssignment(PlayerRole.C, AssignmentType.MAN, PlayerRole.BLITZ_L),
                BlockingAssignment(PlayerRole.RG, AssignmentType.MAN, PlayerRole.DT_R),
                BlockingAssignment(PlayerRole.RT, AssignmentType.MAN, PlayerRole.RE),
            ]
        )


def create_slide_protection(slide_left: bool = True) -> BlockingScheme:
    """Create slide protection scheme - line slides one direction."""
    if slide_left:
        return BlockingScheme(
            name="Slide Left",
            assignments=[
                BlockingAssignment(PlayerRole.LT, AssignmentType.ZONE, zone_center=Vec2(-4, 0.5)),
                BlockingAssignment(PlayerRole.LG, AssignmentType.ZONE, zone_center=Vec2(-2, 0.5)),
                BlockingAssignment(PlayerRole.C, AssignmentType.ZONE, zone_center=Vec2(-0.5, 0.5)),
                BlockingAssignment(PlayerRole.RG, AssignmentType.ZONE, zone_center=Vec2(1, 0.5)),
                BlockingAssignment(PlayerRole.RT, AssignmentType.MAN, PlayerRole.RE),  # Anchor
            ]
        )
    else:
        return BlockingScheme(
            name="Slide Right",
            assignments=[
                BlockingAssignment(PlayerRole.LT, AssignmentType.MAN, PlayerRole.LE),  # Anchor
                BlockingAssignment(PlayerRole.LG, AssignmentType.ZONE, zone_center=Vec2(-1, 0.5)),
                BlockingAssignment(PlayerRole.C, AssignmentType.ZONE, zone_center=Vec2(0.5, 0.5)),
                BlockingAssignment(PlayerRole.RG, AssignmentType.ZONE, zone_center=Vec2(2, 0.5)),
                BlockingAssignment(PlayerRole.RT, AssignmentType.ZONE, zone_center=Vec2(4, 0.5)),
            ]
        )


def create_double_team_scheme(front: DefensiveFront) -> BlockingScheme:
    """Create scheme with double team on interior DL."""
    if front == DefensiveFront.THREE_MAN:
        # Double the NT with C+RG, LG watches left
        return BlockingScheme(
            name="Double NT",
            assignments=[
                BlockingAssignment(PlayerRole.LT, AssignmentType.MAN, PlayerRole.LE),
                BlockingAssignment(PlayerRole.LG, AssignmentType.FREE, help_side=GapSide.LEFT),
                BlockingAssignment(PlayerRole.C, AssignmentType.MAN, PlayerRole.NT),
                BlockingAssignment(PlayerRole.RG, AssignmentType.HELP, PlayerRole.NT),  # Double team NT
                BlockingAssignment(PlayerRole.RT, AssignmentType.MAN, PlayerRole.RE),
            ]
        )
    elif front == DefensiveFront.FOUR_MAN:
        # Double the left DT with LG+C, RG watches right
        return BlockingScheme(
            name="Double DT",
            assignments=[
                BlockingAssignment(PlayerRole.LT, AssignmentType.MAN, PlayerRole.LE),
                BlockingAssignment(PlayerRole.LG, AssignmentType.MAN, PlayerRole.DT_L),
                BlockingAssignment(PlayerRole.C, AssignmentType.HELP, PlayerRole.DT_L),  # Double team
                BlockingAssignment(PlayerRole.RG, AssignmentType.MAN, PlayerRole.DT_R),
                BlockingAssignment(PlayerRole.RT, AssignmentType.MAN, PlayerRole.RE),
            ]
        )
    else:  # FIVE_MAN - can't really double, need all blockers
        return BlockingScheme(
            name="Max Protect",
            assignments=[
                BlockingAssignment(PlayerRole.LT, AssignmentType.MAN, PlayerRole.LE),
                BlockingAssignment(PlayerRole.LG, AssignmentType.MAN, PlayerRole.DT_L),
                BlockingAssignment(PlayerRole.C, AssignmentType.MAN, PlayerRole.BLITZ_L),
                BlockingAssignment(PlayerRole.RG, AssignmentType.MAN, PlayerRole.DT_R),
                BlockingAssignment(PlayerRole.RT, AssignmentType.MAN, PlayerRole.RE),
            ]
        )


# =============================================================================
# Defensive Stunts
# =============================================================================

def create_et_stunt(side: str = "left") -> DefensiveStunt:
    """
    Create E-T stunt: End crashes inside, Tackle loops outside.

    The end attacks the guard's outside shoulder while the tackle
    loops around the end to attack the tackle.
    """
    if side == "left":
        return DefensiveStunt(
            stunt_type=StuntType.ET_LEFT,
            penetrator_role=PlayerRole.LE,    # End crashes inside
            looper_role=PlayerRole.DT_L,      # Tackle loops outside
            start_tick=2,
            loop_delay=4,
            # Looper path: step back, then loop wide around
            loop_path=[
                Vec2(0, -0.3),     # Step back
                Vec2(-1.5, 0),     # Loop wide left
                Vec2(-2.5, 1.5),   # Attack outside shoulder of LT
            ],
        )
    else:
        return DefensiveStunt(
            stunt_type=StuntType.ET_RIGHT,
            penetrator_role=PlayerRole.RE,
            looper_role=PlayerRole.DT_R,
            start_tick=2,
            loop_delay=4,
            loop_path=[
                Vec2(0, -0.3),
                Vec2(1.5, 0),
                Vec2(2.5, 1.5),
            ],
        )


def create_te_stunt(side: str = "left") -> DefensiveStunt:
    """
    Create T-E stunt: Tackle penetrates, End loops behind.

    The tackle attacks the A/B gap aggressively while the end
    loops behind to attack the opposite gap.
    """
    if side == "left":
        return DefensiveStunt(
            stunt_type=StuntType.TE_LEFT,
            penetrator_role=PlayerRole.DT_L,  # Tackle penetrates
            looper_role=PlayerRole.LE,        # End loops inside
            start_tick=2,
            loop_delay=3,
            loop_path=[
                Vec2(0.5, -0.2),   # Step toward center
                Vec2(1.5, 0.5),    # Loop behind tackle
                Vec2(1.0, 2.0),    # Attack A-gap
            ],
        )
    else:
        return DefensiveStunt(
            stunt_type=StuntType.TE_RIGHT,
            penetrator_role=PlayerRole.DT_R,
            looper_role=PlayerRole.RE,
            start_tick=2,
            loop_delay=3,
            loop_path=[
                Vec2(-0.5, -0.2),
                Vec2(-1.5, 0.5),
                Vec2(-1.0, 2.0),
            ],
        )


def create_tt_twist() -> DefensiveStunt:
    """
    Create T-T twist: Interior tackles exchange gaps.

    Left DT crashes right, Right DT loops left behind him.
    Designed to confuse center-guard communication.
    """
    return DefensiveStunt(
        stunt_type=StuntType.TT_TWIST,
        penetrator_role=PlayerRole.DT_L,  # Crashes right across center
        looper_role=PlayerRole.DT_R,      # Loops left behind
        start_tick=2,
        loop_delay=4,
        loop_path=[
            Vec2(-0.5, -0.2),   # Step back and left
            Vec2(-1.5, 0.3),    # Continue left
            Vec2(-2.0, 1.5),    # Attack left A-gap
        ],
    )


# =============================================================================
# Main Simulator
# =============================================================================

class PocketSimulator:
    """
    Simulates a pocket with 5 OL vs variable DL and a QB.

    Layout (top-down, looking from above, offense going up):

              QB              <- QB in backfield (y positive = toward own endzone)
        LT  LG  C  RG  RT     <- Blockers behind LOS
        LE  DT     DT  RE     <- Rushers at LOS (4-man front example)

    Coordinate system:
        x = lateral (negative = left, positive = right)
        y = depth (0 = LOS, positive = toward QB/offense backfield)
    """

    # Field layout
    BLOCKER_DEPTH = 1.0    # Yards behind LOS (gives room for pocket to form)
    RUSHER_DEPTH = -0.5    # Yards in front of LOS (DL alignment)
    LINEMAN_SPACING = 1.5  # Yards between linemen

    # Simulation parameters
    MAX_TICKS = 50
    TICK_MS = 100

    # Movement speeds (yards per tick)
    ENGAGED_MOVEMENT = 0.20         # Base movement when engaged (visible pocket collapse)
    FREE_RUSHER_SPEED = 0.40        # Free rusher chasing QB

    # Contest thresholds
    SHED_THRESHOLD = 20.0
    PANCAKE_THRESHOLD = -25.0
    WINNING_THRESHOLD = 8.0
    DOUBLE_TEAM_BONUS = 15.0  # Bonus for blocker in double team

    # Pressure/sack distance
    PRESSURE_DISTANCE = 2.0
    SACK_DISTANCE = 0.5

    # Stunt movement speeds
    STUNT_CRASH_SPEED = 0.25   # Penetrator crash speed
    STUNT_LOOP_SPEED = 0.2     # Looper path speed

    # QB movement speeds
    QB_STEPUP_SPEED = 0.15     # Yards per tick when stepping up
    QB_SLIDE_SPEED = 0.12      # Yards per tick when sliding
    QB_SCRAMBLE_SPEED_BASE = 0.28   # Base scramble speed (yards/tick) ~16 mph
    QB_SCRAMBLE_SPEED_MAX = 0.45    # Max scramble speed for mobile QBs ~22 mph

    # QB pressure thresholds (distance in yards)
    QB_PRESSURE_LIGHT = 4.0    # Light pressure distance
    QB_PRESSURE_MODERATE = 3.0 # Moderate pressure
    QB_PRESSURE_HEAVY = 2.0    # Heavy pressure
    QB_PRESSURE_CRITICAL = 1.0 # Critical - must act now

    # Scramble decision thresholds
    SCRAMBLE_HEAVY_PRESSURE_CHANCE = 0.25  # Chance to scramble under heavy pressure per tick
    SCRAMBLE_COMMIT_TICKS = 3              # Ticks of scrambling before committed
    SCRAMBLE_LANE_WIDTH = 2.0              # Width of escape lane in yards (narrower = more lanes available)

    # Pursuit constants
    PURSUIT_SPEED = 0.25       # Free rusher pursuit speed (yards/tick) - DL is slower than mobile QB
    PURSUIT_ANGLE_FACTOR = 0.7 # How much to lead the QB

    def __init__(
        self,
        qb_depth: float = 7.0,
        defensive_front: DefensiveFront = DefensiveFront.FOUR_MAN,
        blocking_scheme: Optional[BlockingScheme] = None,
        stunt: Optional[DefensiveStunt] = None,
        dropback_type: DropbackType = DropbackType.SHOTGUN,
        qb_mobility: int = 75,
    ):
        """Initialize the pocket simulation.

        Args:
            qb_depth: Final QB depth (used for shotgun, overridden by dropback for others)
            defensive_front: 3-man, 4-man, or 5-man front
            blocking_scheme: Custom blocking assignments (auto-generated if None)
            stunt: Defensive line stunt to run
            dropback_type: Type of QB dropback (3-step, 5-step, 7-step, or shotgun)
            qb_mobility: QB mobility rating 1-99 (affects scramble speed)
        """
        self.qb_depth = qb_depth
        self.defensive_front = defensive_front
        self.blocking_scheme = blocking_scheme
        self.stunt = stunt
        self.dropback_type = dropback_type
        self.qb_mobility = qb_mobility
        self.state: Optional[PocketSimState] = None
        self._looper_start_pos: Optional[Vec2] = None  # Store looper's starting position

    def setup(
        self,
        blocker_attrs: Optional[dict[str, PlayerAttributes]] = None,
        rusher_attrs: Optional[dict[str, PlayerAttributes]] = None,
    ) -> PocketSimState:
        """Set up the initial pocket formation."""
        blocker_attrs = blocker_attrs or {}
        rusher_attrs = rusher_attrs or {}

        # Get dropback configuration
        dropback_config = DROPBACK_CONFIG[self.dropback_type]
        target_depth, dropback_ticks = dropback_config

        # Determine starting QB position based on dropback type
        if self.dropback_type == DropbackType.SHOTGUN:
            # Shotgun: QB starts at full depth, no dropback needed
            qb_start_y = self.qb_depth
            dropback_complete = True
        else:
            # Under center: QB starts just behind center, will drop back
            qb_start_y = 1.5  # Just behind center
            dropback_complete = False

        # Create QB
        qb = Player(
            role=PlayerRole.QB,
            position=Vec2(0, qb_start_y),
            animation=AnimationState.DROPBACK if not dropback_complete else AnimationState.POCKET_SET,
            facing=Vec2(0, -1),  # Facing downfield
        )

        # Create 5 OL
        blockers = self._create_blockers(blocker_attrs)

        # Create rushers based on front
        rushers = self._create_rushers(rusher_attrs)

        # Create or use provided blocking scheme
        scheme = self.blocking_scheme or create_man_protection(self.defensive_front)

        # Resolve assignments and create engagements
        engagements = self._resolve_assignments(blockers, rushers, scheme, qb)

        # Store looper's starting position for stunt path calculation
        if self.stunt:
            looper = next((r for r in rushers if r.role == self.stunt.looper_role), None)
            if looper:
                self._looper_start_pos = Vec2(looper.position.x, looper.position.y)

        # Create QB state with dropback info
        qb_state = QBState(
            initial_position=Vec2(qb.position.x, qb.position.y),
            throw_target_tick=30,  # ~3 seconds to throw
            dropback_type=self.dropback_type,
            dropback_complete=dropback_complete,
            dropback_target_depth=target_depth,
            dropback_ticks_remaining=dropback_ticks,
            mobility=self.qb_mobility,
        )

        self.state = PocketSimState(
            qb=qb,
            blockers=blockers,
            rushers=rushers,
            engagements=engagements,
            blocking_scheme=scheme,
            defensive_front=self.defensive_front,
            stunt=self.stunt,
            qb_state=qb_state,
        )

        return self.state

    def _create_blockers(self, attrs: dict[str, PlayerAttributes]) -> list[Player]:
        """Create the 5 offensive linemen."""
        positions = [
            (PlayerRole.LT, -2 * self.LINEMAN_SPACING),
            (PlayerRole.LG, -1 * self.LINEMAN_SPACING),
            (PlayerRole.C, 0),
            (PlayerRole.RG, 1 * self.LINEMAN_SPACING),
            (PlayerRole.RT, 2 * self.LINEMAN_SPACING),
        ]

        blockers = []
        for role, x_offset in positions:
            blockers.append(Player(
                role=role,
                position=Vec2(x_offset, self.BLOCKER_DEPTH),
                attributes=attrs.get(role.value, self._default_ol_attrs(role)),
                animation=AnimationState.STANCE,
                facing=Vec2(0, -1),
            ))
        return blockers

    def _create_rushers(self, attrs: dict[str, PlayerAttributes]) -> list[Player]:
        """Create rushers based on defensive front."""
        rushers = []

        if self.defensive_front == DefensiveFront.THREE_MAN:
            configs = [
                (PlayerRole.LE, -2.5 * self.LINEMAN_SPACING),
                (PlayerRole.NT, 0),
                (PlayerRole.RE, 2.5 * self.LINEMAN_SPACING),
            ]
        elif self.defensive_front == DefensiveFront.FOUR_MAN:
            configs = [
                (PlayerRole.LE, -2.5 * self.LINEMAN_SPACING),
                (PlayerRole.DT_L, -0.75 * self.LINEMAN_SPACING),
                (PlayerRole.DT_R, 0.75 * self.LINEMAN_SPACING),
                (PlayerRole.RE, 2.5 * self.LINEMAN_SPACING),
            ]
        else:  # FIVE_MAN
            configs = [
                (PlayerRole.LE, -2.5 * self.LINEMAN_SPACING),
                (PlayerRole.DT_L, -0.75 * self.LINEMAN_SPACING),
                (PlayerRole.BLITZ_L, 0),  # A-gap blitzer
                (PlayerRole.DT_R, 0.75 * self.LINEMAN_SPACING),
                (PlayerRole.RE, 2.5 * self.LINEMAN_SPACING),
            ]

        for role, x_offset in configs:
            rushers.append(Player(
                role=role,
                position=Vec2(x_offset, self.RUSHER_DEPTH),
                attributes=attrs.get(role.value, self._default_dl_attrs(role)),
                animation=AnimationState.STANCE,
                facing=Vec2(0, 1),  # Facing the offense
            ))

        return rushers

    def _resolve_assignments(
        self,
        blockers: list[Player],
        rushers: list[Player],
        scheme: BlockingScheme,
        qb: Player,
    ) -> list[Engagement]:
        """Resolve blocking assignments into engagements."""
        engagements = []
        assigned_rushers: set[PlayerRole] = set()
        assigned_blockers: set[PlayerRole] = set()
        blocker_by_role = {b.role: b for b in blockers}
        rusher_by_role = {r.role: r for r in rushers}
        engagement_by_rusher: dict[PlayerRole, Engagement] = {}

        # If there's a stunt, the looper starts unengaged to execute the loop
        stunt_looper_role = self.stunt.looper_role if self.stunt else None
        if stunt_looper_role:
            # Mark looper as "assigned" so blockers don't pick them up initially
            assigned_rushers.add(stunt_looper_role)

        # First pass: MAN assignments (primary blocker)
        for assignment in scheme.assignments:
            if assignment.assignment_type != AssignmentType.MAN:
                continue

            blocker = blocker_by_role.get(assignment.blocker_role)
            target_rusher = rusher_by_role.get(assignment.target_role)

            # Skip if target is the stunt looper (they start free)
            if target_rusher and target_rusher.role == stunt_looper_role:
                continue

            if blocker and target_rusher and target_rusher.role not in assigned_rushers:
                eng = self._create_engagement([blocker], target_rusher, qb)
                engagements.append(eng)
                assigned_rushers.add(target_rusher.role)
                assigned_blockers.add(blocker.role)
                engagement_by_rusher[target_rusher.role] = eng

        # Second pass: HELP assignments (join existing engagements for double teams)
        for assignment in scheme.assignments:
            if assignment.assignment_type != AssignmentType.HELP:
                continue

            blocker = blocker_by_role.get(assignment.blocker_role)
            if not blocker or blocker.role in assigned_blockers:
                continue

            # Find the engagement to join
            target_eng = engagement_by_rusher.get(assignment.target_role)
            if target_eng:
                # Add blocker to existing engagement (double team)
                target_eng.blockers.append(blocker)
                assigned_blockers.add(blocker.role)

        # Third pass: ZONE assignments
        for assignment in scheme.assignments:
            if assignment.assignment_type != AssignmentType.ZONE:
                continue

            blocker = blocker_by_role.get(assignment.blocker_role)
            if not blocker or blocker.role in assigned_blockers:
                continue

            # Find closest unassigned rusher in zone
            best_rusher = None
            best_dist = float('inf')

            for rusher in rushers:
                if rusher.role in assigned_rushers:
                    continue

                # Check if rusher is in zone
                if assignment.zone_center:
                    dist = rusher.position.distance_to(assignment.zone_center)
                    if dist < assignment.zone_width and dist < best_dist:
                        best_dist = dist
                        best_rusher = rusher

            if best_rusher:
                eng = self._create_engagement([blocker], best_rusher, qb)
                engagements.append(eng)
                assigned_rushers.add(best_rusher.role)
                assigned_blockers.add(blocker.role)
                engagement_by_rusher[best_rusher.role] = eng

        # Fourth pass: FREE blockers - help nearest or pick up unassigned
        free_assignments = [
            a for a in scheme.assignments
            if a.assignment_type == AssignmentType.FREE
            and a.blocker_role in blocker_by_role
            and a.blocker_role not in assigned_blockers
        ]

        for assignment in free_assignments:
            blocker = blocker_by_role[assignment.blocker_role]

            # First check: any unassigned rushers coming our way?
            unassigned_rushers = [r for r in rushers if r.role not in assigned_rushers]

            if unassigned_rushers:
                # Pick up the closest unassigned rusher
                closest = min(unassigned_rushers, key=lambda r: blocker.position.distance_to(r.position))
                eng = self._create_engagement([blocker], closest, qb)
                engagements.append(eng)
                assigned_rushers.add(closest.role)
                assigned_blockers.add(blocker.role)
                engagement_by_rusher[closest.role] = eng
            else:
                # No unassigned rushers - help nearest engaged rusher (double team)
                nearest_eng = self._find_nearest_engagement(blocker, engagements, assignment.help_side)
                if nearest_eng and len(nearest_eng.blockers) < 2:
                    nearest_eng.blockers.append(blocker)
                    assigned_blockers.add(blocker.role)

        # Mark any remaining unblocked rushers as free
        for rusher in rushers:
            if rusher.role not in assigned_rushers:
                rusher.is_free = True
                rusher.animation = AnimationState.PURSUE

        return engagements

    def _find_nearest_engagement(
        self,
        blocker: Player,
        engagements: list[Engagement],
        help_side: Optional[GapSide],
    ) -> Optional[Engagement]:
        """Find nearest engagement for a free blocker to help with."""
        if not engagements:
            return None

        candidates = engagements

        # Filter by help_side if specified
        if help_side == GapSide.LEFT:
            # Only help engagements to the left of this blocker
            candidates = [e for e in engagements if e.rusher.position.x < blocker.position.x]
        elif help_side == GapSide.RIGHT:
            candidates = [e for e in engagements if e.rusher.position.x > blocker.position.x]
        elif help_side == GapSide.INSIDE:
            # Help engagements closer to center
            candidates = [e for e in engagements if abs(e.rusher.position.x) < abs(blocker.position.x)]
        elif help_side == GapSide.OUTSIDE:
            candidates = [e for e in engagements if abs(e.rusher.position.x) > abs(blocker.position.x)]

        if not candidates:
            candidates = engagements  # Fall back to all if no matches

        # Find nearest that isn't already a double team
        single_blocks = [e for e in candidates if len(e.blockers) < 2]
        if not single_blocks:
            return None

        return min(single_blocks, key=lambda e: blocker.position.distance_to(e.contact_point))

    def _create_engagement(
        self,
        blockers: list[Player],
        rusher: Player,
        qb: Player,
    ) -> Engagement:
        """Create an engagement between blocker(s) and rusher."""
        # Contact point is between them
        blocker_pos = blockers[0].position
        if len(blockers) > 1:
            # Average position for double team
            blocker_pos = Vec2(
                sum(b.position.x for b in blockers) / len(blockers),
                sum(b.position.y for b in blockers) / len(blockers),
            )

        contact = Vec2(
            (blocker_pos.x + rusher.position.x) / 2,
            (blocker_pos.y + rusher.position.y) / 2,
        )

        # Rush direction toward QB
        rush_dir = (qb.position - rusher.position).normalized()

        return Engagement(
            blockers=blockers,
            rusher=rusher,
            contact_point=contact,
            rush_direction=rush_dir,
        )

    def _default_ol_attrs(self, role: PlayerRole) -> PlayerAttributes:
        """Get default attributes for an OL by position."""
        if role in (PlayerRole.LT, PlayerRole.RT):
            return PlayerAttributes(
                strength=78, speed=62, agility=68,
                pass_block=82, awareness=75,
            )
        elif role in (PlayerRole.LG, PlayerRole.RG):
            return PlayerAttributes(
                strength=82, speed=58, agility=62,
                pass_block=78, awareness=72,
            )
        else:  # Center
            return PlayerAttributes(
                strength=80, speed=60, agility=65,
                pass_block=80, awareness=82,
            )

    def _default_dl_attrs(self, role: PlayerRole) -> PlayerAttributes:
        """Get default attributes for a DL by position."""
        if role in (PlayerRole.LE, PlayerRole.RE):
            return PlayerAttributes(
                strength=76, speed=80, agility=78,
                block_shedding=80, power_moves=72, finesse_moves=82,
            )
        elif role in (PlayerRole.DT_L, PlayerRole.DT_R, PlayerRole.NT):
            return PlayerAttributes(
                strength=88, speed=62, agility=60,
                block_shedding=78, power_moves=85, finesse_moves=62,
            )
        else:  # Blitzer
            return PlayerAttributes(
                strength=72, speed=82, agility=80,
                block_shedding=75, power_moves=70, finesse_moves=78,
            )

    def tick(self) -> PocketSimState:
        """Execute one simulation tick."""
        if self.state is None:
            raise RuntimeError("Call setup() first")

        if self.state.is_complete:
            return self.state

        self.state.tick += 1

        # Process stunt if active
        stunt_rushers = set()
        if self.state.stunt:
            stunt_rushers = self._process_stunt()

        # Process each engagement (skip stunt participants still executing stunt)
        for engagement in self.state.engagements:
            if engagement.rusher.role not in stunt_rushers:
                self._process_engagement(engagement)

        # Move free rushers toward QB (skip stunt participants still executing)
        for rusher in self.state.rushers:
            if rusher.is_free and not rusher.is_down and rusher.role not in stunt_rushers:
                self._move_free_rusher(rusher)

        # Process QB behavior (pressure detection, movement, throw timer)
        self._process_qb()

        # Check win conditions
        self._check_win_conditions()

        return self.state

    def _process_stunt(self) -> set[PlayerRole]:
        """
        Process the defensive stunt phases.
        Returns set of rusher roles currently executing the stunt (don't process normally).
        """
        stunt = self.state.stunt
        if not stunt or stunt.phase == StuntPhase.COMPLETE:
            return set()

        stunt_rushers = set()
        penetrator = next((r for r in self.state.rushers if r.role == stunt.penetrator_role), None)
        looper = next((r for r in self.state.rushers if r.role == stunt.looper_role), None)

        if not penetrator or not looper:
            stunt.phase = StuntPhase.COMPLETE
            return set()

        tick = self.state.tick

        # Phase transitions
        if stunt.phase == StuntPhase.PRE_STUNT and tick >= stunt.start_tick:
            stunt.phase = StuntPhase.PENETRATOR_GO
            penetrator.animation = AnimationState.STUNT_CRASH
            looper.animation = AnimationState.STUNT_HOLD

        if stunt.phase == StuntPhase.PENETRATOR_GO and tick >= stunt.start_tick + stunt.loop_delay:
            stunt.phase = StuntPhase.LOOPER_GO
            looper.animation = AnimationState.STUNT_LOOP

        # Execute stunt movements
        if stunt.phase == StuntPhase.PENETRATOR_GO:
            # Penetrator crashes - moves toward opposite gap
            stunt_rushers.add(penetrator.role)
            stunt_rushers.add(looper.role)  # Looper holds during this phase

            # Move penetrator on crash path (toward inside)
            crash_dir = self._get_stunt_crash_direction(stunt)
            if not penetrator.is_free and not self._is_engaged(penetrator):
                penetrator.position = penetrator.position + (crash_dir * self.STUNT_CRASH_SPEED)
                penetrator.facing = crash_dir

        elif stunt.phase == StuntPhase.LOOPER_GO:
            stunt_rushers.add(looper.role)

            # Move looper along path
            if not looper.is_free and not self._is_engaged(looper) and self._looper_start_pos:
                if stunt.current_path_index < len(stunt.loop_path):
                    # Calculate target position (relative to start)
                    target_offset = stunt.loop_path[stunt.current_path_index]
                    target = Vec2(
                        self._looper_start_pos.x + target_offset.x,
                        self._looper_start_pos.y + target_offset.y,
                    )

                    # Move toward target
                    direction = (target - looper.position).normalized()
                    looper.position = looper.position + (direction * self.STUNT_LOOP_SPEED)
                    looper.facing = direction

                    # Check if reached waypoint
                    if looper.position.distance_to(target) < 0.2:
                        stunt.current_path_index += 1

                        # Check if stunt complete
                        if stunt.current_path_index >= len(stunt.loop_path):
                            stunt.phase = StuntPhase.COMPLETE
                            looper.is_free = True
                            looper.animation = AnimationState.PURSUE
                else:
                    stunt.phase = StuntPhase.COMPLETE
                    looper.is_free = True
                    looper.animation = AnimationState.PURSUE

        return stunt_rushers

    def _get_stunt_crash_direction(self, stunt: DefensiveStunt) -> Vec2:
        """Get the crash direction for the penetrator."""
        # Penetrator crashes toward the opposite side (inside)
        if stunt.stunt_type in (StuntType.ET_LEFT, StuntType.TE_LEFT):
            return Vec2(0.5, 1).normalized()  # Crash right and upfield
        elif stunt.stunt_type in (StuntType.ET_RIGHT, StuntType.TE_RIGHT):
            return Vec2(-0.5, 1).normalized()  # Crash left and upfield
        else:  # TT_TWIST - penetrator goes right
            return Vec2(0.7, 1).normalized()

    def _is_engaged(self, rusher: Player) -> bool:
        """Check if a rusher is currently engaged with a blocker."""
        for eng in self.state.engagements:
            if eng.rusher.role == rusher.role and eng.state not in (EngagementState.SHED, EngagementState.PANCAKE):
                return True
        return False

    def _process_engagement(self, eng: Engagement) -> None:
        """Process one blocker-rusher engagement with accumulated advantage."""
        rusher = eng.rusher

        # Skip if rusher already free or down
        if rusher.is_free or rusher.is_down:
            return

        # First tick = engage
        if eng.state == EngagementState.PRE_SNAP:
            eng.state = EngagementState.ENGAGED
            for blocker in eng.blockers:
                blocker.animation = AnimationState.PASS_SET
            rusher.animation = AnimationState.RUSH_BURST

            # Initialize double team state if applicable
            if eng.is_double_team and eng.double_team_state is None:
                eng.double_team_state = DoubleTeamState(
                    primary_blocker_role=eng.blockers[0].role,
                    help_blocker_role=eng.blockers[1].role,
                )

        # Increment engagement time
        eng.advantage.ticks_engaged += 1
        eng.move_state.ticks_in_move += 1

        # Check if current move has expired - select new move
        if eng.move_state.ticks_in_move >= eng.move_state.move_duration:
            new_move = self._select_rusher_move(rusher, eng)
            eng.move_state.current_move = new_move
            eng.move_state.ticks_in_move = 0

            # Set new duration
            min_dur, max_dur = MOVE_DURATIONS[new_move]
            eng.move_state.move_duration = random.randint(min_dur, max_dur)

        # Select blocker response based on rusher's move
        eng.current_blocker_response = self._select_blocker_response(
            eng.blockers, eng.move_state.current_move, eng.advantage
        )

        # Calculate this tick's contest
        tick_margin = self._calculate_tick_contest(
            rusher, eng.blockers,
            eng.move_state.current_move,
            eng.current_blocker_response
        )

        # Apply double team bonus (with split mechanics)
        if eng.is_double_team and eng.double_team_state:
            dt_bonus = self._calculate_double_team_bonus(
                eng.double_team_state,
                eng.move_state.current_move
            )
            tick_margin -= dt_bonus  # Negative for rusher = bonus for blocker

            # Process split attempt
            self._process_split_attempt(eng, eng.move_state.current_move)

        # Store last tick margin
        eng.advantage.last_tick_margin = tick_margin

        # Apply time-based fatigue bonus for rushers
        # Blockers tire over time, giving rushers an increasing advantage
        tick = self.state.tick
        if tick > FATIGUE_START_TICK:
            fatigue_ticks = tick - FATIGUE_START_TICK
            fatigue_bonus = min(MAX_FATIGUE_BONUS, fatigue_ticks * FATIGUE_RUSHER_BONUS_PER_TICK)
            tick_margin += fatigue_bonus  # Bonus goes to rusher (positive)

        # Calculate decay
        decay = ADVANTAGE_DECAY

        # ACCUMULATE ADVANTAGE
        eng.advantage.accumulated_margin = (
            eng.advantage.accumulated_margin * decay + tick_margin
        )

        # Track momentum
        if tick_margin > 3:
            if eng.advantage.winning_side == "rusher":
                eng.advantage.consecutive_wins += 1
            else:
                eng.advantage.winning_side = "rusher"
                eng.advantage.consecutive_wins = 1
        elif tick_margin < -3:
            if eng.advantage.winning_side == "blocker":
                eng.advantage.consecutive_wins += 1
            else:
                eng.advantage.winning_side = "blocker"
                eng.advantage.consecutive_wins = 1
        else:
            eng.advantage.winning_side = None
            eng.advantage.consecutive_wins = 0

        # Apply momentum bonus (capped at MAX_MOMENTUM_TICKS)
        # Rusher momentum is higher than blocker (pancakes should be rare)
        consecutive_capped = min(MAX_MOMENTUM_TICKS, eng.advantage.consecutive_wins)
        if eng.advantage.winning_side == "rusher":
            momentum_bonus = consecutive_capped * MOMENTUM_BONUS_RUSHER
            eng.advantage.accumulated_margin += momentum_bonus
        elif eng.advantage.winning_side == "blocker":
            momentum_bonus = consecutive_capped * MOMENTUM_BONUS_BLOCKER
            eng.advantage.accumulated_margin -= momentum_bonus

        # Track peaks
        eng.advantage.peak_rusher_advantage = max(
            eng.advantage.peak_rusher_advantage,
            eng.advantage.accumulated_margin
        )
        eng.advantage.peak_blocker_advantage = min(
            eng.advantage.peak_blocker_advantage,
            eng.advantage.accumulated_margin
        )

        # Check for shed or pancake (using ACCUMULATED threshold)
        accumulated = eng.advantage.accumulated_margin

        if accumulated >= ACCUMULATED_SHED_THRESHOLD:
            eng.state = EngagementState.SHED
            rusher.is_free = True
            rusher.animation = AnimationState.SHED_FREE
            rusher.position = Vec2(eng.contact_point.x, eng.contact_point.y)
            for blocker in eng.blockers:
                blocker.animation = AnimationState.BEATEN
            return

        if accumulated <= ACCUMULATED_PANCAKE_THRESHOLD:
            eng.state = EngagementState.PANCAKE
            rusher.is_down = True
            rusher.animation = AnimationState.PANCAKED
            for blocker in eng.blockers:
                blocker.animation = AnimationState.PANCAKE_BLOCK
            return

        # Update engagement state and animations based on accumulated margin
        if accumulated > ACCUMULATED_WINNING_THRESHOLD:
            eng.state = EngagementState.RUSHER_WINNING
            eng.rusher_wins += 1
            eng.rush_move = self._move_to_animation(eng.move_state.current_move)
            rusher.animation = eng.rush_move
            for blocker in eng.blockers:
                blocker.animation = AnimationState.ENGAGED_LOSING
        elif accumulated < -ACCUMULATED_WINNING_THRESHOLD:
            eng.state = EngagementState.BLOCKER_WINNING
            eng.blocker_wins += 1
            rusher.animation = AnimationState.ENGAGED_NEUTRAL
            for blocker in eng.blockers:
                blocker.animation = AnimationState.ENGAGED_WINNING
        else:
            eng.state = EngagementState.ENGAGED
            eng.neutral += 1
            rusher.animation = AnimationState.ENGAGED_NEUTRAL
            for blocker in eng.blockers:
                blocker.animation = AnimationState.ENGAGED_NEUTRAL

        # Move the contact point based on accumulated advantage
        movement = self._calculate_movement(accumulated)
        delta = eng.rush_direction * movement
        eng.contact_point = eng.contact_point + delta

        # Move players with engagement
        self._update_player_positions(eng)

    def _select_rusher_move(self, rusher: Player, eng: Engagement) -> RusherMove:
        """Select next move when current move expires."""
        attrs = rusher.attributes
        move_state = eng.move_state
        advantage = eng.advantage

        # Base weights from attributes
        weights: dict[RusherMove, float] = {}

        # Power moves (bull rush)
        weights[RusherMove.BULL_RUSH] = (
            attrs.power_moves * 0.5 + attrs.strength * 0.4 +
            move_state.move_preferences.get(RusherMove.BULL_RUSH, 1.0) * 10
        )

        # Finesse moves (swim, spin, rip)
        finesse_base = attrs.finesse_moves * 0.5 + attrs.speed * 0.25 + attrs.agility * 0.25
        weights[RusherMove.SWIM] = finesse_base + move_state.move_preferences.get(RusherMove.SWIM, 1.0) * 10
        weights[RusherMove.SPIN] = (
            finesse_base * 0.8 + attrs.agility * 0.2 +
            move_state.move_preferences.get(RusherMove.SPIN, 1.0) * 10
        )
        weights[RusherMove.RIP] = (
            attrs.power_moves * 0.3 + attrs.finesse_moves * 0.3 + attrs.block_shedding * 0.4 +
            move_state.move_preferences.get(RusherMove.RIP, 1.0) * 10
        )

        # Long arm (only if being double teamed or losing badly)
        if eng.is_double_team or advantage.accumulated_margin < -20:
            weights[RusherMove.LONG_ARM] = (
                attrs.strength * 0.4 + attrs.finesse_moves * 0.3 +
                move_state.move_preferences.get(RusherMove.LONG_ARM, 0.5) * 10
            )
        else:
            weights[RusherMove.LONG_ARM] = 0.0

        # Situational adjustments
        if advantage.accumulated_margin > 10:
            # Winning - stick with power/consistent
            weights[RusherMove.BULL_RUSH] *= 1.3
            weights[RusherMove.SPIN] *= 0.7  # Less risky moves
        elif advantage.accumulated_margin < -10:
            # Losing - try finesse/high-variance
            weights[RusherMove.SPIN] *= 1.4
            weights[RusherMove.SWIM] *= 1.2
            weights[RusherMove.BULL_RUSH] *= 0.8

        # Add noise and select
        for move in weights:
            weights[move] += random.gauss(0, 8)

        return max(weights, key=lambda m: weights[m])

    def _select_blocker_response(
        self,
        blockers: list[Player],
        rusher_move: RusherMove,
        advantage: EngagementAdvantage
    ) -> BlockerResponse:
        """Select blocker response based on rusher's move and situation."""
        if not blockers:
            return BlockerResponse.ANCHOR

        # Best blocker's attributes (for decision-making)
        best_blocker = max(blockers, key=lambda b: b.attributes.awareness)
        attrs = best_blocker.attributes

        # Awareness determines how well blocker "reads" the move
        read_accuracy = attrs.awareness / 100.0

        optimal = OPTIMAL_RESPONSES[rusher_move]

        # High awareness = more likely to pick optimal
        if random.random() < read_accuracy * 0.7:
            return optimal

        # Otherwise, weight by attributes
        weights = {
            BlockerResponse.ANCHOR: attrs.strength * 0.5 + attrs.pass_block * 0.3,
            BlockerResponse.MIRROR: attrs.agility * 0.4 + attrs.pass_block * 0.4,
            BlockerResponse.RE_FIT: attrs.awareness * 0.4 + attrs.pass_block * 0.3,
            BlockerResponse.RE_LEVERAGE: attrs.awareness * 0.5 + attrs.strength * 0.3,
            BlockerResponse.PUNCH: attrs.pass_block * 0.5 + attrs.strength * 0.3,
        }

        # Situational: if losing, more likely to re-fit
        if advantage.accumulated_margin > 15:
            weights[BlockerResponse.RE_FIT] *= 1.5
            weights[BlockerResponse.RE_LEVERAGE] *= 1.3

        for resp in weights:
            weights[resp] += random.gauss(0, 5)

        return max(weights, key=lambda r: weights[r])

    def _calculate_tick_contest(
        self,
        rusher: Player,
        blockers: list[Player],
        move: RusherMove,
        response: BlockerResponse
    ) -> float:
        """Calculate single-tick contest result."""
        attrs = rusher.attributes

        # Base rusher score (move-dependent)
        if move == RusherMove.BULL_RUSH:
            rusher_score = attrs.power_moves * 0.5 + attrs.strength * 0.4 + attrs.block_shedding * 0.1
        elif move == RusherMove.LONG_ARM:
            rusher_score = attrs.strength * 0.4 + attrs.finesse_moves * 0.3 + attrs.block_shedding * 0.3
        else:  # Finesse moves
            rusher_score = attrs.finesse_moves * 0.5 + attrs.speed * 0.2 + attrs.agility * 0.2 + attrs.block_shedding * 0.1

        # Base blocker score (response-dependent)
        blocker_score = self._calc_blocker_score_with_response(blockers, response)

        # Move vs Response matchup modifier
        matchup_modifier = MOVE_MATCHUP_MATRIX[move][response]

        # Noise (reduced compared to old system - momentum handles variance)
        noise = random.gauss(0, 4.0)

        # Base rusher advantage (DL knows snap count, attacks first)
        return (rusher_score + matchup_modifier + BASE_RUSHER_ADVANTAGE) - blocker_score + noise

    def _calc_blocker_score_with_response(
        self,
        blockers: list[Player],
        response: BlockerResponse
    ) -> float:
        """Calculate blocker score modified by response."""
        if not blockers:
            return 0

        # Use best blocker's score
        best = max(blockers, key=lambda b: b.attributes.pass_block)
        attrs = best.attributes

        base_score = attrs.pass_block * 0.4 + attrs.strength * 0.3 + attrs.awareness * 0.15 + attrs.agility * 0.15

        # Response modifiers
        if response == BlockerResponse.ANCHOR:
            base_score += attrs.strength * 0.1
        elif response == BlockerResponse.MIRROR:
            base_score += attrs.agility * 0.1
        elif response == BlockerResponse.PUNCH:
            base_score += attrs.pass_block * 0.1

        return base_score

    def _calculate_double_team_bonus(
        self,
        dt_state: DoubleTeamState,
        rusher_move: RusherMove
    ) -> float:
        """Calculate blocker bonus from double team."""
        # Coordination multiplier (1.0 = perfect, decays when split)
        coordination_mult = dt_state.coordination_score

        # Move-specific modifiers
        if rusher_move == RusherMove.LONG_ARM:
            coordination_mult *= 0.7  # Long arm designed for doubles
        elif rusher_move == RusherMove.SPIN:
            coordination_mult *= 0.8  # Spin can split doubles
        elif rusher_move == RusherMove.BULL_RUSH:
            coordination_mult *= 1.2  # Bull rush into double is futile

        bonus = BASE_DOUBLE_TEAM_BONUS * coordination_mult
        return max(MIN_DOUBLE_TEAM_BONUS, min(MAX_DOUBLE_TEAM_BONUS, bonus))

    def _process_split_attempt(self, eng: Engagement, rusher_move: RusherMove) -> None:
        """Process rusher's attempt to split the double team."""
        if not eng.is_double_team or not eng.double_team_state:
            return

        dt_state = eng.double_team_state
        rusher = eng.rusher

        # Determine if rusher is attempting to split
        splitting_moves = {RusherMove.LONG_ARM, RusherMove.SPIN, RusherMove.RIP}

        if rusher_move in splitting_moves:
            dt_state.rusher_splitting = True

            # Split progress based on advantage and attributes
            split_factor = (
                rusher.attributes.finesse_moves * 0.004 +
                rusher.attributes.strength * 0.002 +
                (eng.advantage.accumulated_margin / 100) * 0.05
            )

            # Long arm is specifically good at splitting
            if rusher_move == RusherMove.LONG_ARM:
                split_factor *= 1.5

            dt_state.split_progress = min(1.0, dt_state.split_progress + max(0, split_factor))

            # Degrade coordination as split progresses
            dt_state.coordination_score = max(
                0.3,
                dt_state.coordination_score - (COORDINATION_DECAY_PER_TICK * dt_state.split_progress)
            )
        else:
            # Not splitting - coordination slowly recovers
            dt_state.rusher_splitting = False
            dt_state.coordination_score = min(1.0, dt_state.coordination_score + 0.01)
            dt_state.split_progress = max(0.0, dt_state.split_progress - 0.02)

    def _move_to_animation(self, move: RusherMove) -> AnimationState:
        """Convert RusherMove to AnimationState."""
        mapping = {
            RusherMove.BULL_RUSH: AnimationState.BULL_RUSH,
            RusherMove.SWIM: AnimationState.SWIM_MOVE,
            RusherMove.SPIN: AnimationState.SPIN_MOVE,
            RusherMove.RIP: AnimationState.RIP_MOVE,
            RusherMove.LONG_ARM: AnimationState.BULL_RUSH,  # No specific animation
        }
        return mapping.get(move, AnimationState.RUSH_BURST)

    def _calculate_movement(self, accumulated: float) -> float:
        """Calculate contact point movement based on accumulated advantage.

        In reality, blockers are almost always giving ground - the question is
        how much. Even a "neutral" engagement still moves toward the QB.
        Only dominant blocking (pancake territory) truly stops the rush.
        """
        base_movement = self.ENGAGED_MOVEMENT

        if accumulated > ACCUMULATED_WINNING_THRESHOLD:
            # Rusher pushing hard - accelerated collapse
            factor = 1.3 + min(1.2, (accumulated - ACCUMULATED_WINNING_THRESHOLD) / 20)
            return base_movement * factor
        elif accumulated < -ACCUMULATED_WINNING_THRESHOLD:
            # Blocker winning - pocket collapse slows but doesn't stop
            # Only go negative (push rusher back) near pancake territory
            if accumulated < -60:
                factor = 0.1  # Near-stalemate when dominating
            else:
                factor = 0.5  # Still pushing toward QB even when "winning"
            return base_movement * factor
        else:
            # Neutral - pocket collapses at good pace
            return base_movement * 1.0

    def _update_player_positions(self, eng: Engagement) -> None:
        """Update player positions based on engagement."""
        offset = eng.rush_direction * 0.3
        if eng.is_double_team:
            # Offset double-team blockers laterally so they're side-by-side
            lateral = Vec2(-eng.rush_direction.y, eng.rush_direction.x)  # Perpendicular
            for i, blocker in enumerate(eng.blockers):
                side = -0.4 if i == 0 else 0.4  # Left and right of center
                blocker.position = eng.contact_point + offset + (lateral * side)
        else:
            for blocker in eng.blockers:
                blocker.position = eng.contact_point + offset
        eng.rusher.position = eng.contact_point - offset

    def _select_rush_move(self, rusher: Player) -> AnimationState:
        """Select which rush move the rusher uses this tick (legacy method)."""
        attrs = rusher.attributes

        # Weight moves by attributes
        power_weight = attrs.power_moves + attrs.strength * 0.5
        finesse_weight = attrs.finesse_moves + attrs.speed * 0.3 + attrs.agility * 0.3

        total = power_weight + finesse_weight

        if random.random() < power_weight / total:
            return AnimationState.BULL_RUSH
        else:
            # Pick a finesse move
            moves = [AnimationState.SWIM_MOVE, AnimationState.SPIN_MOVE, AnimationState.RIP_MOVE]
            return random.choice(moves)

    def _calc_rusher_score(self, attrs: PlayerAttributes, move: AnimationState) -> float:
        """Calculate rusher's contest score based on move (legacy method)."""
        if move == AnimationState.BULL_RUSH:
            return attrs.power_moves * 0.5 + attrs.strength * 0.4 + attrs.block_shedding * 0.1
        else:
            return attrs.finesse_moves * 0.5 + attrs.speed * 0.2 + attrs.agility * 0.2 + attrs.block_shedding * 0.1

    def _calc_blocker_score(self, blockers: list[Player]) -> float:
        """Calculate combined blocker score (legacy method)."""
        if not blockers:
            return 0

        # Use best blocker's score
        scores = []
        for blocker in blockers:
            attrs = blocker.attributes
            score = (
                attrs.pass_block * 0.5
                + attrs.strength * 0.3
                + attrs.awareness * 0.1
                + attrs.agility * 0.1
            )
            scores.append(score)

        return max(scores)

    def _move_free_rusher(self, rusher: Player) -> None:
        """Move a free rusher toward the QB."""
        qb_pos = self.state.qb.position
        direction = (qb_pos - rusher.position).normalized()

        rusher.position = rusher.position + (direction * self.FREE_RUSHER_SPEED)
        rusher.animation = AnimationState.PURSUE
        rusher.facing = direction

    def _process_qb(self) -> None:
        """Process QB behavior: dropback, pressure detection, movement, throw timer."""
        qb = self.state.qb
        qbs = self.state.qb_state
        if not qbs:
            return

        # Skip if already sacked or threw
        if qbs.action in (QBAction.SACKED, QBAction.THROWING):
            return

        # 1. Handle dropback if not complete
        if not qbs.dropback_complete:
            self._process_dropback()
            # During dropback, only calculate pressure but don't act on it yet
            self._calculate_pressure()
            self._update_pressure_level()
            return  # QB can't throw until dropback is complete

        # 2. Calculate pressure from all directions
        self._calculate_pressure()

        # 3. Update pressure level
        self._update_pressure_level()

        # 4. Update action based on tick and pressure
        if self.state.tick <= 5 and qbs.dropback_type == DropbackType.SHOTGUN:
            # Initial setting phase (only for shotgun, others are in dropback)
            qbs.action = QBAction.SETTING
            qb.animation = AnimationState.POCKET_SET
        elif qbs.scramble_committed:
            # QB has committed to scrambling - continue running, don't throw
            qbs.action = QBAction.SCRAMBLING
            qb.animation = AnimationState.SCRAMBLE
            qbs.scramble_ticks += 1  # Keep incrementing ticks for direction reassessment
        elif self.state.tick >= qbs.throw_target_tick and qbs.pressure_level in (PressureLevel.CLEAN, PressureLevel.LIGHT):
            # Throw the ball if clean/light pressure and time to throw (and not scrambling)
            qbs.action = QBAction.THROWING
            qb.animation = AnimationState.THROWING
            self.state.is_complete = True
            self.state.result = "throw"
            return
        else:
            # Decide action based on pressure
            self._decide_qb_action()

        # 5. Move QB based on action
        self._move_qb()

    def _process_dropback(self) -> None:
        """Process QB dropback movement."""
        qb = self.state.qb
        qbs = self.state.qb_state

        if qbs.dropback_complete:
            return

        # Calculate how much to move this tick
        if qbs.dropback_ticks_remaining > 0:
            # Calculate yards per tick to reach target
            current_y = qb.position.y
            remaining_distance = qbs.dropback_target_depth - current_y
            yards_per_tick = remaining_distance / qbs.dropback_ticks_remaining

            # Move QB back
            new_y = current_y + yards_per_tick
            qb.position = Vec2(qb.position.x, new_y)
            qb.animation = AnimationState.DROPBACK

            qbs.dropback_ticks_remaining -= 1

            # Check if dropback complete
            if qbs.dropback_ticks_remaining <= 0:
                qbs.dropback_complete = True
                qb.animation = AnimationState.POCKET_SET
                qbs.action = QBAction.SCANNING
                # Update initial position to the new pocket position for movement limits
                qbs.initial_position = Vec2(qb.position.x, qb.position.y)
        else:
            # No ticks remaining - complete immediately (shouldn't happen)
            qbs.dropback_complete = True
            qb.animation = AnimationState.POCKET_SET
            qbs.action = QBAction.SCANNING

    def _calculate_pressure(self) -> None:
        """Calculate pressure coming from each direction."""
        qb = self.state.qb
        qbs = self.state.qb_state
        qb_pos = qb.position

        # Reset pressure values
        qbs.pressure_left = 0.0
        qbs.pressure_right = 0.0
        qbs.pressure_front = 0.0

        for rusher in self.state.rushers:
            if rusher.is_down:
                continue

            dist = rusher.position.distance_to(qb_pos)
            if dist > self.QB_PRESSURE_LIGHT:
                continue  # Too far to be pressure

            # Calculate pressure value (1.0 at sack distance, 0.0 at light threshold)
            pressure = 1.0 - (dist - self.SACK_DISTANCE) / (self.QB_PRESSURE_LIGHT - self.SACK_DISTANCE)
            pressure = max(0.0, min(1.0, pressure))

            # Determine direction of pressure
            dx = rusher.position.x - qb_pos.x  # Positive = rusher on right
            dy = qb_pos.y - rusher.position.y  # Positive = rusher in front (closer to LOS)

            # Classify pressure direction
            if abs(dx) > abs(dy) * 0.5:  # More lateral than forward
                if dx < 0:
                    qbs.pressure_left = max(qbs.pressure_left, pressure)
                else:
                    qbs.pressure_right = max(qbs.pressure_right, pressure)
            else:
                qbs.pressure_front = max(qbs.pressure_front, pressure)

    def _update_pressure_level(self) -> None:
        """Update QB's overall pressure level."""
        qbs = self.state.qb_state
        qb_pos = self.state.qb.position

        # Find closest rusher
        min_dist = float('inf')
        for rusher in self.state.rushers:
            if not rusher.is_down:
                dist = rusher.position.distance_to(qb_pos)
                min_dist = min(min_dist, dist)

        # Set pressure level based on closest rusher
        if min_dist <= self.QB_PRESSURE_CRITICAL:
            qbs.pressure_level = PressureLevel.CRITICAL
        elif min_dist <= self.QB_PRESSURE_HEAVY:
            qbs.pressure_level = PressureLevel.HEAVY
        elif min_dist <= self.QB_PRESSURE_MODERATE:
            qbs.pressure_level = PressureLevel.MODERATE
        elif min_dist <= self.QB_PRESSURE_LIGHT:
            qbs.pressure_level = PressureLevel.LIGHT
        else:
            qbs.pressure_level = PressureLevel.CLEAN

    def _decide_qb_action(self) -> None:
        """Decide what action QB should take based on pressure."""
        qb = self.state.qb
        qbs = self.state.qb_state

        # If already committed to scrambling, stay scrambling
        if qbs.scramble_committed:
            qbs.action = QBAction.SCRAMBLING
            qb.animation = AnimationState.SCRAMBLE
            return

        # If critical pressure, must scramble
        if qbs.pressure_level == PressureLevel.CRITICAL:
            qbs.action = QBAction.SCRAMBLING
            qb.animation = AnimationState.SCRAMBLE
            return

        # If already scrambling, continue and check for commit
        if qbs.action == QBAction.SCRAMBLING:
            qbs.scramble_ticks += 1
            if qbs.scramble_ticks >= self.SCRAMBLE_COMMIT_TICKS:
                qbs.scramble_committed = True
            qb.animation = AnimationState.SCRAMBLE
            return

        # If heavy pressure, may scramble or need to move
        if qbs.pressure_level == PressureLevel.HEAVY:
            # Check if there's an open escape lane - mobile QBs more likely to see it
            mobility_factor = (qbs.mobility - 50) / 50  # -1 to +1 range
            scramble_chance = self.SCRAMBLE_HEAVY_PRESSURE_CHANCE * (1 + mobility_factor * 0.5)

            # Check for open lanes
            best_lane = self._find_best_escape_lane()
            if best_lane and random.random() < scramble_chance:
                # Decide to scramble
                qbs.action = QBAction.SCRAMBLING
                qbs.escape_direction = best_lane
                qbs.scramble_ticks = 1
                qb.animation = AnimationState.SCRAMBLE
                return

            # Otherwise slide or step up
            if qbs.pressure_left > qbs.pressure_right:
                # Pressure from left, slide right
                qbs.action = QBAction.SLIDING
                qbs.escape_direction = Vec2(1, 0)
                qb.animation = AnimationState.SLIDE_RIGHT
            elif qbs.pressure_right > qbs.pressure_left:
                # Pressure from right, slide left
                qbs.action = QBAction.SLIDING
                qbs.escape_direction = Vec2(-1, 0)
                qb.animation = AnimationState.SLIDE_LEFT
            else:
                # Pressure from front/center, step up
                qbs.action = QBAction.STEPPING_UP
                qbs.escape_direction = Vec2(0, -1)  # Forward (toward LOS)
                qb.animation = AnimationState.STEP_UP
            return

        # If moderate pressure, consider stepping up
        if qbs.pressure_level == PressureLevel.MODERATE:
            if qbs.pressure_front < max(qbs.pressure_left, qbs.pressure_right):
                # Edge pressure, step up
                qbs.action = QBAction.STEPPING_UP
                qbs.escape_direction = Vec2(0, -1)
                qb.animation = AnimationState.STEP_UP
            else:
                # Stay scanning but show pressured
                qbs.action = QBAction.SCANNING
                qb.animation = AnimationState.PRESSURED
            return

        # Light or clean - stay in pocket scanning
        qbs.action = QBAction.SCANNING
        qb.animation = AnimationState.POCKET_SET

    def _move_qb(self) -> None:
        """Move QB based on current action."""
        qb = self.state.qb
        qbs = self.state.qb_state

        if qbs.action == QBAction.STEPPING_UP:
            # Move forward (toward LOS)
            new_y = qb.position.y - self.QB_STEPUP_SPEED

            # Check limits
            if qbs.initial_position:
                min_y = qbs.initial_position.y - qbs.max_stepup
                new_y = max(new_y, min_y)

            qb.position = Vec2(qb.position.x, new_y)

        elif qbs.action == QBAction.SLIDING:
            if qbs.escape_direction:
                new_x = qb.position.x + (qbs.escape_direction.x * self.QB_SLIDE_SPEED)

                # Check limits
                if qbs.initial_position:
                    min_x = qbs.initial_position.x - qbs.max_slide
                    max_x = qbs.initial_position.x + qbs.max_slide
                    new_x = max(min_x, min(max_x, new_x))

                qb.position = Vec2(new_x, qb.position.y)

        elif qbs.action == QBAction.SCRAMBLING:
            # Calculate mobility-based scramble speed
            # Mobility 50 = base speed, 99 = max speed
            mobility_factor = (qbs.mobility - 50) / 49  # 0 to 1 for mobility 50-99
            mobility_factor = max(0, min(1, mobility_factor))
            scramble_speed = self.QB_SCRAMBLE_SPEED_BASE + (
                (self.QB_SCRAMBLE_SPEED_MAX - self.QB_SCRAMBLE_SPEED_BASE) * mobility_factor
            )

            # Find best escape direction based on lanes and pressure
            escape_dir = self._find_escape_direction()
            if escape_dir:
                qb.position = qb.position + (escape_dir * scramble_speed)

            # Update defenders to pursue
            self._update_pursuit()

    def _find_best_escape_lane(self) -> Optional[Vec2]:
        """Find the best escape lane for scrambling.

        Returns direction vector if a good lane exists, None if trapped.
        """
        qb_pos = self.state.qb.position
        qbs = self.state.qb_state

        # Check lanes in order of preference:
        # 1. Toward LOS on weak side (potential run)
        # 2. Laterally away from pressure
        # 3. Backward away from pressure

        # Define lane directions to check (x, y) in pocket coords
        # y negative = toward LOS (good for running), y positive = deeper in backfield
        # Prioritize routes that get to LOS faster (more y-component)
        lanes = [
            (Vec2(0.0, -1.0), "straight_up"),      # Straight toward LOS - fastest to gain yards
            (Vec2(-0.5, -0.87), "left_upfield"),   # Left and toward LOS (~60 degrees)
            (Vec2(0.5, -0.87), "right_upfield"),   # Right and toward LOS (~60 degrees)
            (Vec2(-0.87, -0.5), "left_angle"),     # More lateral left (~30 degrees)
            (Vec2(0.87, -0.5), "right_angle"),     # More lateral right (~30 degrees)
        ]

        best_lane = None
        best_clearance = 0.0

        for direction, name in lanes:
            direction = direction.normalized()
            clearance = self._calculate_lane_clearance(qb_pos, direction)

            # Weight toward LOS lanes higher (better for scramble runs)
            if direction.y < 0:
                clearance *= 1.3

            # Penalize going deeper into backfield
            if direction.y > 0:
                clearance *= 0.7

            if clearance > best_clearance:
                best_clearance = clearance
                best_lane = direction

        # Only return lane if there's minimum clearance
        if best_clearance >= self.SCRAMBLE_LANE_WIDTH:
            return best_lane
        return None

    def _calculate_lane_clearance(self, qb_pos: Vec2, direction: Vec2) -> float:
        """Calculate how clear a lane is in the given direction.

        Returns estimated yards of clearance before hitting a defender.
        """
        max_check_distance = 8.0  # Check up to 8 yards ahead
        min_clearance = max_check_distance

        for rusher in self.state.rushers:
            if rusher.is_down:
                continue

            # Vector from QB to rusher
            to_rusher = rusher.position - qb_pos
            dist_to_rusher = to_rusher.length()

            if dist_to_rusher < 0.5:
                # Rusher right on top of QB - no clearance
                return 0.0

            # Check if rusher is roughly in this lane direction
            # using dot product to see if rusher is "ahead" in this direction
            dot = direction.dot(to_rusher.normalized())

            if dot > 0.3:  # Rusher is somewhat in this direction
                # Calculate perpendicular distance to lane line
                # (how far off the lane path the rusher is)
                perp_dist = abs(direction.cross(to_rusher))

                # If rusher is close to the lane path, they block it
                if perp_dist < self.SCRAMBLE_LANE_WIDTH:
                    # Clearance is distance along lane to this rusher
                    along_lane = direction.dot(to_rusher)
                    if along_lane > 0:  # Rusher is ahead, not behind
                        min_clearance = min(min_clearance, along_lane)

        return min_clearance

    def _find_escape_direction(self) -> Vec2:
        """Find the best escape direction for a scrambling QB."""
        qb_pos = self.state.qb.position
        qbs = self.state.qb_state

        # Field boundaries (sidelines) - approximately 26.67 yards from center
        SIDELINE_LIMIT = 25.0  # Leave some margin

        # Check if near sideline and need to adjust
        near_right_sideline = qb_pos.x > SIDELINE_LIMIT - 3
        near_left_sideline = qb_pos.x < -(SIDELINE_LIMIT - 3)

        # If near sideline, force direction away or straight upfield
        if near_right_sideline:
            # Can't keep going right, go upfield or cut back left
            return Vec2(-0.3, -0.95).normalized()
        if near_left_sideline:
            # Can't keep going left, go upfield or cut back right
            return Vec2(0.3, -0.95).normalized()

        # Periodically reassess the best lane (every 5 ticks or first tick)
        reassess = qbs.scramble_ticks == 1 or qbs.scramble_ticks % 5 == 0

        if reassess or qbs.escape_direction is None:
            # Find best lane dynamically
            best_lane = self._find_best_escape_lane()
            if best_lane:
                qbs.escape_direction = best_lane
            else:
                # Fallback: escape opposite of highest pressure
                if qbs.pressure_left > qbs.pressure_right:
                    qbs.escape_direction = Vec2(0.5, -0.87).normalized()  # Right and mostly toward LOS
                elif qbs.pressure_right > qbs.pressure_left:
                    qbs.escape_direction = Vec2(-0.5, -0.87).normalized()  # Left and mostly toward LOS
                else:
                    qbs.escape_direction = Vec2(0, -1)  # Straight toward LOS

        # Adjust for pursuit
        adjusted = self._adjust_escape_for_pursuit(qbs.escape_direction)
        if adjusted:
            return adjusted

        return qbs.escape_direction

    def _adjust_escape_for_pursuit(self, current_dir: Vec2) -> Optional[Vec2]:
        """Adjust escape direction to avoid pursuing defenders."""
        qb_pos = self.state.qb.position

        # Find closest pursuing defender
        closest_dist = float('inf')
        closest_rusher = None

        for rusher in self.state.rushers:
            if rusher.is_down:
                continue
            dist = rusher.position.distance_to(qb_pos)
            if dist < closest_dist:
                closest_dist = dist
                closest_rusher = rusher

        if closest_rusher is None or closest_dist > 5.0:
            return current_dir

        # If defender is close and in our path, adjust
        to_rusher = (closest_rusher.position - qb_pos).normalized()
        dot = current_dir.dot(to_rusher)

        if dot > 0.5:  # Heading toward defender
            # Rotate away from defender
            # Use cross product to determine which way to turn
            cross = current_dir.cross(to_rusher)
            if cross > 0:
                # Turn left
                return Vec2(-current_dir.y, current_dir.x).normalized()
            else:
                # Turn right
                return Vec2(current_dir.y, -current_dir.x).normalized()

        return current_dir

    def _update_pursuit(self) -> None:
        """Update free rusher positions to pursue scrambling QB."""
        qb = self.state.qb
        qbs = self.state.qb_state

        if qbs.action != QBAction.SCRAMBLING:
            return

        for rusher in self.state.rushers:
            if not rusher.is_free or rusher.is_down:
                continue

            # Calculate pursuit angle - lead the QB
            qb_velocity = qbs.escape_direction or Vec2(0, -1)

            # Predict where QB will be in a few ticks
            mobility_factor = (qbs.mobility - 50) / 49
            mobility_factor = max(0, min(1, mobility_factor))
            qb_speed = self.QB_SCRAMBLE_SPEED_BASE + (
                (self.QB_SCRAMBLE_SPEED_MAX - self.QB_SCRAMBLE_SPEED_BASE) * mobility_factor
            )

            predicted_qb_pos = qb.position + (qb_velocity * qb_speed * 3)  # 3 ticks ahead

            # Pursuit direction toward predicted position
            to_qb = predicted_qb_pos - rusher.position
            if to_qb.length() > 0.1:
                pursuit_dir = to_qb.normalized()
                # Move at pursuit speed
                rusher.position = rusher.position + (pursuit_dir * self.PURSUIT_SPEED)
                rusher.animation = AnimationState.PURSUE

    def _check_win_conditions(self) -> None:
        """Check if simulation should end."""
        qb_pos = self.state.qb.position
        qbs = self.state.qb_state

        # Check for scramble crossing LOS
        # In pocket_sim coords: y=0 is LOS, y>0 is backfield, y<0 is past LOS
        if qbs and qbs.action == QBAction.SCRAMBLING and qb_pos.y < 0:
            self.state.is_complete = True
            self.state.result = "scramble"
            # Calculate yards gained (negative y in pocket coords = positive yards)
            self.state.qb.animation = AnimationState.SCRAMBLE
            return

        for rusher in self.state.rushers:
            if rusher.is_free and not rusher.is_down:
                dist = rusher.position.distance_to(qb_pos)
                if dist <= self.SACK_DISTANCE:
                    self.state.is_complete = True
                    self.state.result = "sack"
                    rusher.animation = AnimationState.SACK
                    self.state.qb.animation = AnimationState.SACKED
                    return

        all_down = all(r.is_down for r in self.state.rushers)
        if all_down:
            self.state.is_complete = True
            self.state.result = "clean_pocket"
            return

        if self.state.tick >= self.MAX_TICKS:
            self.state.is_complete = True
            any_free = any(r.is_free and not r.is_down for r in self.state.rushers)
            if any_free:
                self.state.result = "pressure"
            else:
                self.state.result = "clean_pocket"

    def run_full(self) -> list[dict]:
        """Run complete simulation and return all states."""
        if self.state is None:
            self.setup()

        states = []
        while not self.state.is_complete:
            self.tick()
            states.append(self.state.to_dict())

        return states

    def reset(self) -> PocketSimState:
        """Reset to initial state."""
        return self.setup()

    def set_qb_throwing(self) -> None:
        """Signal that QB has thrown the ball (from external source like play_sim).

        This should be called when the play simulation determines the QB throws.
        It updates the pocket simulation's QB state accordingly.
        """
        if self.state is None:
            return

        qb = self.state.qb
        qbs = self.state.qb_state

        if qbs:
            qbs.action = QBAction.THROWING

        qb.animation = AnimationState.THROWING

    def set_qb_scrambling(self, direction: Optional[Vec2] = None) -> None:
        """Signal that QB is scrambling (from external source like play_sim).

        Args:
            direction: Optional scramble direction. If None, uses pressure-based escape.
        """
        if self.state is None:
            return

        qbs = self.state.qb_state
        if qbs:
            qbs.action = QBAction.SCRAMBLING
            qbs.escape_direction = direction or self._get_escape_direction()

        self.state.qb.animation = AnimationState.SCRAMBLE
