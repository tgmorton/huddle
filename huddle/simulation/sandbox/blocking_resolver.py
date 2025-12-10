"""Blocking simulation resolver for 1v1 matchups."""

import random
from typing import Optional

from .models import (
    BlockerTechnique,
    MatchupOutcome,
    MatchupState,
    Position2D,
    RusherTechnique,
    SandboxPlayer,
    SimulationState,
    TickResult,
)


class BlockingSimulator:
    """
    Simulates a 1v1 blocking matchup tick-by-tick.

    Models the push-and-pull between an offensive lineman (blocker)
    and a defensive lineman (rusher) using probabilistic outcomes
    weighted by player attributes.
    """

    # Default simulation parameters
    DEFAULT_TICK_RATE_MS = 100  # 100ms per tick
    DEFAULT_MAX_TICKS = 50  # ~5 seconds of game time
    DEFAULT_QB_ZONE_DEPTH = 7.0  # Yards from LOS where rusher wins

    # Movement constants (yards per tick outcome)
    MOVEMENT_SHED = 1.0  # Major rusher win
    MOVEMENT_RUSHER_WINNING = 0.3  # Rusher gaining
    MOVEMENT_ENGAGED = 0.05  # Slight drift toward QB
    MOVEMENT_BLOCKER_WINNING = -0.1  # Blocker pushing back
    MOVEMENT_PANCAKE = 0.0  # No more movement

    # Contest margin thresholds
    MARGIN_SHED = 18.0  # Rusher score > blocker + 18 = shed
    MARGIN_RUSHER_WINNING = 6.0  # Rusher score > blocker + 6
    MARGIN_BLOCKER_WINNING = -6.0  # Blocker score > rusher + 6
    MARGIN_PANCAKE = -22.0  # Blocker dominates (rare)

    # Randomness factor (standard deviation for gaussian noise)
    NOISE_STDDEV = 5.0

    def __init__(
        self,
        blocker: SandboxPlayer,
        rusher: SandboxPlayer,
        tick_rate_ms: int = DEFAULT_TICK_RATE_MS,
        max_ticks: int = DEFAULT_MAX_TICKS,
        qb_zone_depth: float = DEFAULT_QB_ZONE_DEPTH,
    ) -> None:
        """
        Initialize the blocking simulator.

        Args:
            blocker: The offensive lineman
            rusher: The defensive lineman
            tick_rate_ms: Milliseconds per simulation tick
            max_ticks: Maximum ticks before blocker wins by default
            qb_zone_depth: Yards from LOS where rusher wins
        """
        self.blocker = blocker
        self.rusher = rusher
        self.tick_rate_ms = tick_rate_ms
        self.max_ticks = max_ticks
        self.qb_zone_depth = qb_zone_depth

        # State tracking
        self.current_tick = 0
        self.rusher_depth = 0.0  # Yards penetrated toward QB
        # Rusher starts at LOS (x=0), blocker is between rusher and QB (x=0.5)
        self.blocker_position = Position2D(x=0.5, y=0.0)  # In front of QB
        self.rusher_position = Position2D(x=0.0, y=0.0)  # At LOS

        # Stats
        self.rusher_wins_contest = 0
        self.blocker_wins_contest = 0
        self.neutral_contests = 0

        # Outcome tracking
        self.outcome = MatchupOutcome.IN_PROGRESS
        self.matchup_state = MatchupState.INITIAL

    def reset(self) -> None:
        """Reset the simulation to initial state."""
        self.current_tick = 0
        self.rusher_depth = 0.0
        self.blocker_position = Position2D(x=0.5, y=0.0)
        self.rusher_position = Position2D(x=0.0, y=0.0)
        self.rusher_wins_contest = 0
        self.blocker_wins_contest = 0
        self.neutral_contests = 0
        self.outcome = MatchupOutcome.IN_PROGRESS
        self.matchup_state = MatchupState.INITIAL

    def is_complete(self) -> bool:
        """Check if simulation is complete."""
        return self.outcome != MatchupOutcome.IN_PROGRESS

    def tick(self) -> TickResult:
        """
        Execute one simulation tick.

        Returns:
            TickResult with all details of this tick
        """
        if self.is_complete():
            # Return the last state if already complete
            return self._create_tick_result(
                rusher_technique=RusherTechnique.BULL_RUSH,
                blocker_technique=BlockerTechnique.ANCHOR,
                rusher_score=0.0,
                blocker_score=0.0,
                margin=0.0,
                movement=0.0,
            )

        self.current_tick += 1

        # First tick is engagement
        if self.current_tick == 1:
            self.matchup_state = MatchupState.ENGAGED

        # 1. Rusher selects technique
        rusher_technique = self._select_rusher_technique()

        # 2. Blocker responds
        blocker_technique = self._select_blocker_response(rusher_technique)

        # 3. Calculate contest scores
        rusher_score = self._calculate_rusher_score(rusher_technique)
        blocker_score = self._calculate_blocker_score(blocker_technique, rusher_technique)

        # 4. Add randomness
        rusher_score += random.gauss(0, self.NOISE_STDDEV)
        blocker_score += random.gauss(0, self.NOISE_STDDEV)

        # 5. Resolve contest
        margin = rusher_score - blocker_score
        movement, new_state = self._resolve_contest(margin)

        # 6. Update positions - keep players engaged together
        self.rusher_depth += movement
        self.rusher_position.x += movement

        # Blocker moves with the engagement
        # When rusher advances (movement > 0), blocker retreats to stay engaged
        # When blocker wins (movement < 0), blocker pushes forward
        if movement > 0:
            # Rusher winning - blocker gets pushed back but stays engaged
            self.blocker_position.x += movement * 0.9
        elif movement < 0:
            # Blocker winning - blocker pushes forward with the rusher
            self.blocker_position.x += movement * 0.9

        # 7. Track stats
        if margin > self.MARGIN_RUSHER_WINNING:
            self.rusher_wins_contest += 1
        elif margin < self.MARGIN_BLOCKER_WINNING:
            self.blocker_wins_contest += 1
        else:
            self.neutral_contests += 1

        # 8. Update state
        self.matchup_state = new_state

        # 9. Check win conditions
        self._check_win_conditions()

        return self._create_tick_result(
            rusher_technique=rusher_technique,
            blocker_technique=blocker_technique,
            rusher_score=rusher_score,
            blocker_score=blocker_score,
            margin=margin,
            movement=movement,
        )

    def _select_rusher_technique(self) -> RusherTechnique:
        """
        Select rusher's technique based on attributes.

        Weighted by:
        - bull_rush: power_moves * 0.5 + strength * 0.4 + random
        - swim/spin: finesse_moves * 0.6 + speed * 0.3 + random
        - rip: finesse_moves * 0.4 + power_moves * 0.4 + random
        """
        weights = {
            RusherTechnique.BULL_RUSH: (
                self.rusher.power_moves * 0.5 + self.rusher.strength * 0.4 + random.gauss(0, 10)
            ),
            RusherTechnique.SWIM: (
                self.rusher.finesse_moves * 0.6 + self.rusher.speed * 0.3 + random.gauss(0, 10)
            ),
            RusherTechnique.SPIN: (
                self.rusher.finesse_moves * 0.6 + self.rusher.speed * 0.3 + random.gauss(0, 10)
            ),
            RusherTechnique.RIP: (
                self.rusher.finesse_moves * 0.4
                + self.rusher.power_moves * 0.4
                + random.gauss(0, 10)
            ),
        }

        # Select highest weighted technique
        return max(weights, key=weights.get)

    def _select_blocker_response(self, rusher_technique: RusherTechnique) -> BlockerTechnique:
        """
        Select blocker's response based on rusher technique and attributes.

        Counter-techniques:
        - anchor: Good vs power (bull_rush, rip)
        - mirror: Good vs finesse (swim, spin)
        - punch: Aggressive, works against everything but risky
        """
        is_power_move = rusher_technique in (RusherTechnique.BULL_RUSH, RusherTechnique.RIP)
        is_finesse_move = rusher_technique in (RusherTechnique.SWIM, RusherTechnique.SPIN)

        # Calculate weights based on situation
        weights = {}

        # Anchor is best vs power
        anchor_bonus = 20 if is_power_move else 0
        weights[BlockerTechnique.ANCHOR] = (
            self.blocker.strength * 0.5
            + self.blocker.pass_block * 0.4
            + anchor_bonus
            + random.gauss(0, 10)
        )

        # Mirror is best vs finesse
        mirror_bonus = 20 if is_finesse_move else 0
        weights[BlockerTechnique.MIRROR] = (
            self.blocker.agility * 0.4
            + self.blocker.pass_block * 0.4
            + mirror_bonus
            + random.gauss(0, 10)
        )

        # Punch is aggressive and relies on awareness
        weights[BlockerTechnique.PUNCH] = (
            self.blocker.pass_block * 0.6 + self.blocker.awareness * 0.3 + random.gauss(0, 10)
        )

        return max(weights, key=weights.get)

    def _calculate_rusher_score(self, technique: RusherTechnique) -> float:
        """Calculate rusher's score for this tick based on technique."""
        base_score = 0.0

        if technique == RusherTechnique.BULL_RUSH:
            base_score = (
                self.rusher.power_moves * 0.4
                + self.rusher.strength * 0.4
                + self.rusher.block_shedding * 0.2
            )
        elif technique == RusherTechnique.SWIM:
            base_score = (
                self.rusher.finesse_moves * 0.5
                + self.rusher.speed * 0.3
                + self.rusher.agility * 0.2
            )
        elif technique == RusherTechnique.SPIN:
            base_score = (
                self.rusher.finesse_moves * 0.5
                + self.rusher.agility * 0.3
                + self.rusher.speed * 0.2
            )
        elif technique == RusherTechnique.RIP:
            base_score = (
                self.rusher.finesse_moves * 0.35
                + self.rusher.power_moves * 0.35
                + self.rusher.block_shedding * 0.3
            )

        return base_score

    def _calculate_blocker_score(
        self, technique: BlockerTechnique, rusher_technique: RusherTechnique
    ) -> float:
        """Calculate blocker's score based on technique and matchup."""
        base_score = 0.0
        counter_bonus = 0.0

        # Check if blocker is using the right counter
        is_power_move = rusher_technique in (RusherTechnique.BULL_RUSH, RusherTechnique.RIP)
        is_finesse_move = rusher_technique in (RusherTechnique.SWIM, RusherTechnique.SPIN)

        if technique == BlockerTechnique.ANCHOR:
            base_score = (
                self.blocker.strength * 0.45
                + self.blocker.pass_block * 0.35
                + self.blocker.awareness * 0.1
            )
            # Bonus vs power
            if is_power_move:
                counter_bonus = 5.0
        elif technique == BlockerTechnique.MIRROR:
            base_score = (
                self.blocker.agility * 0.4
                + self.blocker.pass_block * 0.4
                + self.blocker.awareness * 0.2
            )
            # Bonus vs finesse
            if is_finesse_move:
                counter_bonus = 6.0
        elif technique == BlockerTechnique.PUNCH:
            base_score = (
                self.blocker.pass_block * 0.6
                + self.blocker.awareness * 0.3
                + self.blocker.strength * 0.1
            )
            # Punch is aggressive but less effective vs finesse
            if is_finesse_move:
                counter_bonus = -5.0

        return base_score + counter_bonus

    def _resolve_contest(self, margin: float) -> tuple[float, MatchupState]:
        """
        Resolve the contest and return movement and new state.

        Args:
            margin: rusher_score - blocker_score

        Returns:
            Tuple of (movement in yards, new matchup state)
        """
        if margin > self.MARGIN_SHED:
            return self.MOVEMENT_SHED, MatchupState.SHED
        elif margin > self.MARGIN_RUSHER_WINNING:
            return self.MOVEMENT_RUSHER_WINNING, MatchupState.RUSHER_WINNING
        elif margin < self.MARGIN_PANCAKE:
            return self.MOVEMENT_PANCAKE, MatchupState.PANCAKE
        elif margin < self.MARGIN_BLOCKER_WINNING:
            return self.MOVEMENT_BLOCKER_WINNING, MatchupState.BLOCKER_WINNING
        else:
            return self.MOVEMENT_ENGAGED, MatchupState.ENGAGED

    def _check_win_conditions(self) -> None:
        """Check and update win conditions."""
        # Rusher wins if they reach QB zone
        if self.rusher_depth >= self.qb_zone_depth:
            self.outcome = MatchupOutcome.RUSHER_WIN
            return

        # Blocker wins on pancake
        if self.matchup_state == MatchupState.PANCAKE:
            self.outcome = MatchupOutcome.PANCAKE
            return

        # Blocker wins if time expires
        if self.current_tick >= self.max_ticks:
            self.outcome = MatchupOutcome.BLOCKER_WIN
            return

    def _create_tick_result(
        self,
        rusher_technique: RusherTechnique,
        blocker_technique: BlockerTechnique,
        rusher_score: float,
        blocker_score: float,
        margin: float,
        movement: float,
    ) -> TickResult:
        """Create a TickResult object."""
        return TickResult(
            tick_number=self.current_tick,
            timestamp_ms=self.current_tick * self.tick_rate_ms,
            blocker_position=Position2D(
                x=self.blocker_position.x, y=self.blocker_position.y
            ),
            rusher_position=Position2D(x=self.rusher_position.x, y=self.rusher_position.y),
            rusher_technique=rusher_technique,
            blocker_technique=blocker_technique,
            rusher_score=rusher_score,
            blocker_score=blocker_score,
            margin=margin,
            movement=movement,
            matchup_state=self.matchup_state,
            outcome=self.outcome,
            rusher_depth=self.rusher_depth,
            engagement_duration_ms=self.current_tick * self.tick_rate_ms,
        )

    def run_full_simulation(self) -> list[TickResult]:
        """
        Run the complete simulation and return all tick results.

        Useful for non-real-time simulation or replays.
        """
        self.reset()
        results = []

        while not self.is_complete():
            result = self.tick()
            results.append(result)

        return results

    def get_state(self) -> SimulationState:
        """Get the current simulation state as a SimulationState object."""
        return SimulationState(
            blocker=self.blocker,
            rusher=self.rusher,
            tick_rate_ms=self.tick_rate_ms,
            max_ticks=self.max_ticks,
            qb_zone_depth=self.qb_zone_depth,
            current_tick=self.current_tick,
            is_running=not self.is_complete(),
            is_complete=self.is_complete(),
            blocker_position=Position2D(
                x=self.blocker_position.x, y=self.blocker_position.y
            ),
            rusher_position=Position2D(x=self.rusher_position.x, y=self.rusher_position.y),
            outcome=self.outcome,
            rusher_wins_contest=self.rusher_wins_contest,
            blocker_wins_contest=self.blocker_wins_contest,
            neutral_contests=self.neutral_contests,
        )
