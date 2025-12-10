"""Behavior Decision Trees for player state machines.

Provides explicit state machines for QB, WR, and DB behavior with
clear states, transitions, and actions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Callable, Any, Optional

if TYPE_CHECKING:
    from .play_sim import TeamQB, TeamReceiver, TeamDefender, Ball, PlaySimState


# =============================================================================
# Behavior States
# =============================================================================

class QBState(str, Enum):
    """QB behavior states."""
    DROPBACK = "qb_dropback"
    SCANNING = "qb_scanning"
    LOCKED_ON = "qb_locked_on"
    THROWING = "qb_throwing"
    FOLLOW_THROUGH = "qb_follow_through"
    SCRAMBLE = "qb_scramble"  # Future


class WRState(str, Enum):
    """WR behavior states."""
    RELEASE = "wr_release"
    STEM = "wr_stem"
    BREAK = "wr_break"
    POST_BREAK = "wr_post_break"
    SETTLING = "wr_settling"
    TRACKING_BALL = "wr_tracking_ball"
    COMPLETE = "wr_complete"


class DBState(str, Enum):
    """DB behavior states."""
    PRESS = "db_press"
    TRAIL = "db_trail"
    FLIP_HIPS = "db_flip_hips"
    CLOSING = "db_closing"
    BALL_HAWKING = "db_ball_hawking"
    ZONE_READ = "db_zone_read"
    ZONE_BREAK = "db_zone_break"


# =============================================================================
# Transition Framework
# =============================================================================

@dataclass
class Transition:
    """A transition between behavior states."""
    to_state: str
    condition: Callable[[Any], bool]
    priority: int = 0  # Higher priority transitions checked first

    def check(self, context: Any) -> bool:
        """Check if this transition should fire."""
        return self.condition(context)


@dataclass
class BehaviorTree:
    """Generic behavior tree with states and transitions."""
    current_state: str
    transitions: dict[str, list[Transition]] = field(default_factory=dict)

    def add_transition(
        self,
        from_state: str,
        to_state: str,
        condition: Callable[[Any], bool],
        priority: int = 0,
    ) -> None:
        """Add a transition between states."""
        if from_state not in self.transitions:
            self.transitions[from_state] = []
        self.transitions[from_state].append(
            Transition(to_state=to_state, condition=condition, priority=priority)
        )
        # Keep sorted by priority (descending)
        self.transitions[from_state].sort(key=lambda t: -t.priority)

    def tick(self, context: Any) -> Optional[str]:
        """Evaluate transitions and return new state if changed.

        Returns:
            New state name if transitioned, None if staying in current state
        """
        transitions = self.transitions.get(self.current_state, [])
        for transition in transitions:
            if transition.check(context):
                old_state = self.current_state
                self.current_state = transition.to_state
                return self.current_state  # Return new state
        return None  # No transition


# =============================================================================
# Context Objects
# =============================================================================

@dataclass
class QBContext:
    """Context for QB decision tree."""
    qb: "TeamQB"
    tick: int
    pressure: float
    utility_decision: Optional[Any] = None  # ThrowDecision from utility_ai
    ball_thrown: bool = False


@dataclass
class WRContext:
    """Context for WR decision tree."""
    receiver: "TeamReceiver"
    tick: int
    ball: Optional["Ball"] = None
    is_target: bool = False
    at_break_point: bool = False
    break_complete: bool = False
    route_complete: bool = False
    is_settling_route: bool = False


@dataclass
class DBContext:
    """Context for DB decision tree."""
    defender: "TeamDefender"
    assigned_receiver: Optional["TeamReceiver"] = None
    tick: int = 0
    ball: Optional["Ball"] = None
    ball_in_air: bool = False
    wr_at_break: bool = False
    reaction_complete: bool = False
    is_press_coverage: bool = False
    is_zone_coverage: bool = False


# =============================================================================
# QB Behavior Tree Factory
# =============================================================================

def create_qb_behavior_tree() -> BehaviorTree:
    """Create QB behavior tree with all transitions."""
    tree = BehaviorTree(current_state=QBState.DROPBACK.value)

    # DROPBACK -> SCANNING: after tick 5
    tree.add_transition(
        from_state=QBState.DROPBACK.value,
        to_state=QBState.SCANNING.value,
        condition=lambda ctx: ctx.tick >= 5,
        priority=10,
    )

    # SCANNING -> LOCKED_ON: utility AI says throw
    tree.add_transition(
        from_state=QBState.SCANNING.value,
        to_state=QBState.LOCKED_ON.value,
        condition=lambda ctx: (
            ctx.utility_decision is not None and
            ctx.utility_decision.should_throw
        ),
        priority=20,
    )

    # SCANNING -> SCRAMBLE: pressure too high (future)
    tree.add_transition(
        from_state=QBState.SCANNING.value,
        to_state=QBState.SCRAMBLE.value,
        condition=lambda ctx: ctx.pressure > 0.9,
        priority=5,
    )

    # LOCKED_ON -> THROWING: immediate (1 tick later)
    tree.add_transition(
        from_state=QBState.LOCKED_ON.value,
        to_state=QBState.THROWING.value,
        condition=lambda ctx: True,  # Always transition
        priority=10,
    )

    # THROWING -> FOLLOW_THROUGH: after ball released
    tree.add_transition(
        from_state=QBState.THROWING.value,
        to_state=QBState.FOLLOW_THROUGH.value,
        condition=lambda ctx: ctx.ball_thrown,
        priority=10,
    )

    return tree


# =============================================================================
# WR Behavior Tree Factory
# =============================================================================

def create_wr_behavior_tree() -> BehaviorTree:
    """Create WR behavior tree with all transitions."""
    tree = BehaviorTree(current_state=WRState.RELEASE.value)

    # RELEASE -> STEM: after tick 2
    tree.add_transition(
        from_state=WRState.RELEASE.value,
        to_state=WRState.STEM.value,
        condition=lambda ctx: ctx.tick >= 2,
        priority=10,
    )

    # STEM -> TRACKING_BALL: ball thrown to this receiver
    tree.add_transition(
        from_state=WRState.STEM.value,
        to_state=WRState.TRACKING_BALL.value,
        condition=lambda ctx: ctx.is_target and ctx.ball is not None and ctx.ball.is_thrown,
        priority=20,
    )

    # STEM -> BREAK: near break waypoint
    tree.add_transition(
        from_state=WRState.STEM.value,
        to_state=WRState.BREAK.value,
        condition=lambda ctx: ctx.at_break_point,
        priority=10,
    )

    # BREAK -> TRACKING_BALL: ball thrown to this receiver
    tree.add_transition(
        from_state=WRState.BREAK.value,
        to_state=WRState.TRACKING_BALL.value,
        condition=lambda ctx: ctx.is_target and ctx.ball is not None and ctx.ball.is_thrown,
        priority=20,
    )

    # BREAK -> SETTLING: for hitch/curl routes after break
    tree.add_transition(
        from_state=WRState.BREAK.value,
        to_state=WRState.SETTLING.value,
        condition=lambda ctx: ctx.break_complete and ctx.is_settling_route,
        priority=15,
    )

    # BREAK -> POST_BREAK: for continuing routes
    tree.add_transition(
        from_state=WRState.BREAK.value,
        to_state=WRState.POST_BREAK.value,
        condition=lambda ctx: ctx.break_complete and not ctx.is_settling_route,
        priority=10,
    )

    # SETTLING -> TRACKING_BALL: ball thrown
    tree.add_transition(
        from_state=WRState.SETTLING.value,
        to_state=WRState.TRACKING_BALL.value,
        condition=lambda ctx: ctx.is_target and ctx.ball is not None and ctx.ball.is_thrown,
        priority=20,
    )

    # POST_BREAK -> TRACKING_BALL: ball thrown
    tree.add_transition(
        from_state=WRState.POST_BREAK.value,
        to_state=WRState.TRACKING_BALL.value,
        condition=lambda ctx: ctx.is_target and ctx.ball is not None and ctx.ball.is_thrown,
        priority=20,
    )

    # POST_BREAK -> COMPLETE: route finished
    tree.add_transition(
        from_state=WRState.POST_BREAK.value,
        to_state=WRState.COMPLETE.value,
        condition=lambda ctx: ctx.route_complete,
        priority=10,
    )

    return tree


# =============================================================================
# DB Behavior Tree Factory (Man Coverage)
# =============================================================================

def create_db_man_behavior_tree() -> BehaviorTree:
    """Create DB behavior tree for man coverage."""
    tree = BehaviorTree(current_state=DBState.TRAIL.value)

    # PRESS -> TRAIL: after WR releases (tick 2)
    tree.add_transition(
        from_state=DBState.PRESS.value,
        to_state=DBState.TRAIL.value,
        condition=lambda ctx: ctx.tick >= 2,
        priority=10,
    )

    # TRAIL -> BALL_HAWKING: ball in air
    tree.add_transition(
        from_state=DBState.TRAIL.value,
        to_state=DBState.BALL_HAWKING.value,
        condition=lambda ctx: ctx.ball_in_air,
        priority=20,
    )

    # TRAIL -> FLIP_HIPS: WR at break
    tree.add_transition(
        from_state=DBState.TRAIL.value,
        to_state=DBState.FLIP_HIPS.value,
        condition=lambda ctx: ctx.wr_at_break,
        priority=10,
    )

    # FLIP_HIPS -> BALL_HAWKING: ball in air
    tree.add_transition(
        from_state=DBState.FLIP_HIPS.value,
        to_state=DBState.BALL_HAWKING.value,
        condition=lambda ctx: ctx.ball_in_air,
        priority=20,
    )

    # FLIP_HIPS -> CLOSING: reaction complete
    tree.add_transition(
        from_state=DBState.FLIP_HIPS.value,
        to_state=DBState.CLOSING.value,
        condition=lambda ctx: ctx.reaction_complete,
        priority=10,
    )

    # CLOSING -> BALL_HAWKING: ball in air
    tree.add_transition(
        from_state=DBState.CLOSING.value,
        to_state=DBState.BALL_HAWKING.value,
        condition=lambda ctx: ctx.ball_in_air,
        priority=20,
    )

    return tree


def create_db_zone_behavior_tree() -> BehaviorTree:
    """Create DB behavior tree for zone coverage."""
    tree = BehaviorTree(current_state=DBState.ZONE_READ.value)

    # ZONE_READ -> BALL_HAWKING: ball in air
    tree.add_transition(
        from_state=DBState.ZONE_READ.value,
        to_state=DBState.BALL_HAWKING.value,
        condition=lambda ctx: ctx.ball_in_air,
        priority=20,
    )

    # ZONE_READ -> ZONE_BREAK: receiver in zone
    tree.add_transition(
        from_state=DBState.ZONE_READ.value,
        to_state=DBState.ZONE_BREAK.value,
        condition=lambda ctx: ctx.assigned_receiver is not None,
        priority=10,
    )

    # ZONE_BREAK -> BALL_HAWKING: ball in air
    tree.add_transition(
        from_state=DBState.ZONE_BREAK.value,
        to_state=DBState.BALL_HAWKING.value,
        condition=lambda ctx: ctx.ball_in_air,
        priority=20,
    )

    # ZONE_BREAK -> ZONE_READ: no receiver in zone
    tree.add_transition(
        from_state=DBState.ZONE_BREAK.value,
        to_state=DBState.ZONE_READ.value,
        condition=lambda ctx: ctx.assigned_receiver is None,
        priority=5,
    )

    return tree


# =============================================================================
# Behavior Tree Manager
# =============================================================================

class BehaviorTreeManager:
    """Manages behavior trees for all players in a simulation."""

    def __init__(self):
        self.qb_tree: Optional[BehaviorTree] = None
        self.wr_trees: dict[str, BehaviorTree] = {}  # receiver_id -> tree
        self.db_trees: dict[str, BehaviorTree] = {}  # defender_id -> tree

    def setup_qb(self) -> BehaviorTree:
        """Create and store QB behavior tree."""
        self.qb_tree = create_qb_behavior_tree()
        return self.qb_tree

    def setup_wr(self, receiver_id: str) -> BehaviorTree:
        """Create and store WR behavior tree."""
        tree = create_wr_behavior_tree()
        self.wr_trees[receiver_id] = tree
        return tree

    def setup_db(self, defender_id: str, is_zone: bool = False) -> BehaviorTree:
        """Create and store DB behavior tree."""
        if is_zone:
            tree = create_db_zone_behavior_tree()
        else:
            tree = create_db_man_behavior_tree()
        self.db_trees[defender_id] = tree
        return tree

    def get_qb_state(self) -> Optional[str]:
        """Get current QB state."""
        return self.qb_tree.current_state if self.qb_tree else None

    def get_wr_state(self, receiver_id: str) -> Optional[str]:
        """Get current WR state."""
        tree = self.wr_trees.get(receiver_id)
        return tree.current_state if tree else None

    def get_db_state(self, defender_id: str) -> Optional[str]:
        """Get current DB state."""
        tree = self.db_trees.get(defender_id)
        return tree.current_state if tree else None

    def tick_qb(self, context: QBContext) -> Optional[str]:
        """Tick QB behavior tree."""
        if self.qb_tree:
            return self.qb_tree.tick(context)
        return None

    def tick_wr(self, receiver_id: str, context: WRContext) -> Optional[str]:
        """Tick WR behavior tree."""
        tree = self.wr_trees.get(receiver_id)
        if tree:
            return tree.tick(context)
        return None

    def tick_db(self, defender_id: str, context: DBContext) -> Optional[str]:
        """Tick DB behavior tree."""
        tree = self.db_trees.get(defender_id)
        if tree:
            return tree.tick(context)
        return None

    def reset(self) -> None:
        """Reset all behavior trees."""
        self.qb_tree = None
        self.wr_trees.clear()
        self.db_trees.clear()
