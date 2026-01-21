"""Phase State Machine - Explicit play phase transitions.

Manages play lifecycle phases with validated transitions.
All phase changes go through this state machine to ensure
valid transitions and enable testing.

Play Lifecycle:
    SETUP → PRE_SNAP → SNAP → DEVELOPMENT

    From DEVELOPMENT:
        → BALL_IN_AIR (pass thrown)
        → RUN_ACTIVE (handoff/scramble)
        → POST_PLAY (sack/timeout)

    From BALL_IN_AIR:
        → AFTER_CATCH (catch)
        → POST_PLAY (incomplete/interception)

    From AFTER_CATCH:
        → POST_PLAY (tackle/out of bounds)

    From RUN_ACTIVE:
        → POST_PLAY (tackle/touchdown/fumble/out of bounds)

Between-Play Lifecycle (for continuous game simulation):
    POST_PLAY → HUDDLE → FORMATION_MOVE → PRE_SNAP → ...

    HUDDLE: Players jog from play-end positions to huddle formation
    FORMATION_MOVE: Players break huddle and move to pre-snap positions
"""

from __future__ import annotations

from enum import Enum
from typing import Set, Optional, Callable, Dict, Any
from dataclasses import dataclass, field


class PlayPhase(str, Enum):
    """Current phase of play execution."""
    SETUP = "setup"              # Configuring the play
    PRE_SNAP = "pre_snap"        # At alignments, ready to snap
    SNAP = "snap"                # Ball just snapped (single tick)
    DEVELOPMENT = "development"  # Routes running, pocket forming
    BALL_IN_AIR = "ball_in_air"  # Pass thrown, waiting for resolution
    AFTER_CATCH = "after_catch"  # Receiver caught ball, now running
    RUN_ACTIVE = "run_active"    # Ballcarrier has ball, running
    RESOLUTION = "resolution"    # Play resolving (legacy, not currently used)
    POST_PLAY = "post_play"      # Play complete, compiling results
    # Between-play phases
    HUDDLE = "huddle"            # Players jogging to huddle formation
    FORMATION_MOVE = "formation_move"  # Players breaking huddle to pre-snap positions


# Valid phase transitions
VALID_TRANSITIONS: Dict[PlayPhase, Set[PlayPhase]] = {
    PlayPhase.SETUP: {PlayPhase.PRE_SNAP},
    PlayPhase.PRE_SNAP: {PlayPhase.SNAP},
    PlayPhase.SNAP: {PlayPhase.DEVELOPMENT},
    PlayPhase.DEVELOPMENT: {
        PlayPhase.BALL_IN_AIR,  # Pass thrown
        PlayPhase.RUN_ACTIVE,   # Handoff or scramble
        PlayPhase.POST_PLAY,    # Sack, timeout
    },
    PlayPhase.BALL_IN_AIR: {
        PlayPhase.AFTER_CATCH,  # Catch
        PlayPhase.POST_PLAY,    # Incomplete, interception
    },
    PlayPhase.AFTER_CATCH: {
        PlayPhase.POST_PLAY,    # Tackle, out of bounds, touchdown
    },
    PlayPhase.RUN_ACTIVE: {
        PlayPhase.POST_PLAY,    # Tackle, fumble, touchdown, out of bounds
    },
    PlayPhase.RESOLUTION: {
        PlayPhase.POST_PLAY,    # Legacy
    },
    PlayPhase.POST_PLAY: {PlayPhase.HUDDLE},  # Can transition to huddle for next play
    # Between-play phase transitions
    PlayPhase.HUDDLE: {PlayPhase.FORMATION_MOVE},  # Huddle complete, break to formation
    PlayPhase.FORMATION_MOVE: {PlayPhase.PRE_SNAP},  # Formation set, ready for snap
}


@dataclass
class PhaseTransition:
    """Record of a phase transition."""
    from_phase: PlayPhase
    to_phase: PlayPhase
    reason: str
    tick: int
    time: float


TransitionCallback = Callable[[PhaseTransition], None]


class PhaseStateMachine:
    """Manages play phase transitions with validation.

    Features:
    - Validates transitions against allowed rules
    - Records transition history for debugging
    - Supports callbacks on phase changes
    - Provides phase queries (is_active, is_terminal, etc.)

    Usage:
        fsm = PhaseStateMachine()
        fsm.transition_to(PlayPhase.PRE_SNAP, reason="setup complete", tick=0, time=0.0)

        if fsm.can_transition_to(PlayPhase.SNAP):
            fsm.transition_to(PlayPhase.SNAP, reason="ball snapped", tick=1, time=0.05)
    """

    def __init__(self, initial_phase: PlayPhase = PlayPhase.SETUP):
        self._phase = initial_phase
        self._history: list[PhaseTransition] = []
        self._callbacks: list[TransitionCallback] = []

    @property
    def phase(self) -> PlayPhase:
        """Current phase."""
        return self._phase

    @property
    def history(self) -> list[PhaseTransition]:
        """History of phase transitions."""
        return self._history.copy()

    def can_transition_to(self, target: PlayPhase) -> bool:
        """Check if transition to target phase is valid."""
        return target in VALID_TRANSITIONS.get(self._phase, set())

    def transition_to(
        self,
        target: PlayPhase,
        reason: str = "",
        tick: int = 0,
        time: float = 0.0,
        validate: bool = True,
    ) -> None:
        """Transition to a new phase.

        Args:
            target: Target phase
            reason: Why the transition is happening
            tick: Current tick number
            time: Current simulation time
            validate: If True, raise on invalid transition

        Raises:
            InvalidPhaseTransition: If transition is not valid and validate=True
        """
        if validate and not self.can_transition_to(target):
            raise InvalidPhaseTransition(
                f"Cannot transition from {self._phase.value} to {target.value}. "
                f"Valid targets: {[p.value for p in VALID_TRANSITIONS.get(self._phase, set())]}"
            )

        transition = PhaseTransition(
            from_phase=self._phase,
            to_phase=target,
            reason=reason,
            tick=tick,
            time=time,
        )

        self._phase = target
        self._history.append(transition)

        # Notify callbacks
        for callback in self._callbacks:
            callback(transition)

    def on_transition(self, callback: TransitionCallback) -> None:
        """Register a callback for phase transitions."""
        self._callbacks.append(callback)

    def reset(self, initial_phase: PlayPhase = PlayPhase.SETUP) -> None:
        """Reset to initial state."""
        self._phase = initial_phase
        self._history.clear()

    # Convenience queries

    @property
    def is_pre_snap(self) -> bool:
        """True if play hasn't started yet."""
        return self._phase in (PlayPhase.SETUP, PlayPhase.PRE_SNAP)

    @property
    def is_active(self) -> bool:
        """True if play is in progress."""
        return self._phase in (
            PlayPhase.SNAP,
            PlayPhase.DEVELOPMENT,
            PlayPhase.BALL_IN_AIR,
            PlayPhase.AFTER_CATCH,
            PlayPhase.RUN_ACTIVE,
            PlayPhase.RESOLUTION,
        )

    @property
    def is_terminal(self) -> bool:
        """True if play has ended (POST_PLAY with no next play pending)."""
        return self._phase == PlayPhase.POST_PLAY

    @property
    def is_between_plays(self) -> bool:
        """True if in between-play transition (HUDDLE or FORMATION_MOVE)."""
        return self._phase in (PlayPhase.HUDDLE, PlayPhase.FORMATION_MOVE)

    @property
    def ball_is_live(self) -> bool:
        """True if ball is in play (can be caught, fumbled, etc.)."""
        return self._phase in (
            PlayPhase.DEVELOPMENT,
            PlayPhase.BALL_IN_AIR,
            PlayPhase.AFTER_CATCH,
            PlayPhase.RUN_ACTIVE,
        )

    @property
    def is_passing(self) -> bool:
        """True if this is a passing play situation."""
        return self._phase in (PlayPhase.DEVELOPMENT, PlayPhase.BALL_IN_AIR)

    @property
    def has_ballcarrier(self) -> bool:
        """True if there's an active ballcarrier (for YAC/run)."""
        return self._phase in (PlayPhase.AFTER_CATCH, PlayPhase.RUN_ACTIVE)


class InvalidPhaseTransition(Exception):
    """Raised when an invalid phase transition is attempted."""
    pass
