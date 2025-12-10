"""Game service wrapping simulation engine for API use."""

import asyncio
from typing import Callable, Optional
from uuid import UUID

from huddle.core.enums import PassType, RunType
from huddle.core.models.game import GamePhase, GameState
from huddle.core.models.play import PlayCall, PlayResult
from huddle.core.models.team import Team
from huddle.events.types import (
    GameEndEvent,
    GameEvent,
    PlayCompletedEvent,
    QuarterEndEvent,
    ScoringEvent,
    TurnoverEvent,
)
from huddle.logging import GameLog
from huddle.simulation import SimulationEngine


# Pacing delays (seconds between plays)
PACING_DELAYS = {
    "slow": 2.0,
    "normal": 1.0,
    "fast": 0.3,
    "step": None,  # Wait for manual step
}


class GameService:
    """
    API-friendly game service without Textual dependencies.

    Wraps SimulationEngine for use with FastAPI/WebSocket.
    """

    def __init__(
        self,
        home_team: Team,
        away_team: Team,
        event_callback: Optional[Callable[[GameEvent], None]] = None,
    ) -> None:
        """
        Initialize game service.

        Args:
            home_team: Home team
            away_team: Away team
            event_callback: Callback for all game events (for WebSocket push)
        """
        self.home_team = home_team
        self.away_team = away_team
        self._event_callback = event_callback

        # Create simulation components
        self.engine = SimulationEngine()
        self.game_state: Optional[GameState] = None
        self.game_log = GameLog(
            home_abbrev=home_team.abbreviation,
            away_abbrev=away_team.abbreviation,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
        )
        self.game_log.connect_to_event_bus(self.engine.event_bus)

        # Register all players for stats tracking
        self._register_players(home_team, home_team.abbreviation)
        self._register_players(away_team, away_team.abbreviation)

        # Subscribe to simulation events
        self._setup_event_handlers()

        # Control state
        self.current_pacing = "normal"
        self._paused = asyncio.Event()
        self._paused.set()  # Start unpaused
        self._step_event = asyncio.Event()
        self._play_call_event = asyncio.Event()
        self._pending_play_call: Optional[PlayCall] = None
        self._simulation_mode = "auto"
        self._running = False
        self._awaiting_play_call = False

    def _setup_event_handlers(self) -> None:
        """Subscribe to simulation events."""
        event_bus = self.engine.event_bus
        event_bus.subscribe(PlayCompletedEvent, self._on_event)
        event_bus.subscribe(ScoringEvent, self._on_event)
        event_bus.subscribe(TurnoverEvent, self._on_event)
        event_bus.subscribe(QuarterEndEvent, self._on_event)
        event_bus.subscribe(GameEndEvent, self._on_event)

    def _on_event(self, event: GameEvent) -> None:
        """Handle any game event - forward to callback."""
        if self._event_callback:
            self._event_callback(event)

    def set_event_callback(self, callback: Callable[[GameEvent], None]) -> None:
        """Set the event callback (for WebSocket push)."""
        self._event_callback = callback

    def _register_players(self, team: Team, team_abbrev: str) -> None:
        """Register all players from a team for stats tracking."""
        for player in team.roster.players.values():
            self.game_log.register_player(
                player_id=player.id,
                name=player.display_name,
                position=player.position.name,
                team_abbrev=team_abbrev,
            )

    def create_game(self) -> GameState:
        """Create a new game."""
        self.game_state = self.engine.create_game(self.home_team, self.away_team)
        return self.game_state

    def get_game_state(self) -> Optional[GameState]:
        """Get current game state."""
        return self.game_state

    def set_pacing(self, pacing: str) -> None:
        """Update simulation pacing."""
        if pacing in PACING_DELAYS:
            self.current_pacing = pacing

    def set_mode(self, mode: str) -> None:
        """Update simulation mode (auto/manual)."""
        if mode in ("auto", "manual"):
            self._simulation_mode = mode

    def pause(self) -> None:
        """Pause simulation."""
        self._paused.clear()

    def resume(self) -> None:
        """Resume simulation."""
        self._paused.set()

    def toggle_pause(self) -> None:
        """Toggle pause state."""
        if self._paused.is_set():
            self.pause()
        else:
            self.resume()

    @property
    def is_paused(self) -> bool:
        """Check if simulation is paused."""
        return not self._paused.is_set()

    @property
    def is_running(self) -> bool:
        """Check if simulation is actively running."""
        return self._running

    @property
    def is_awaiting_play_call(self) -> bool:
        """Check if waiting for manual play call."""
        return self._awaiting_play_call

    def request_step(self) -> None:
        """Signal to advance one play in step mode."""
        self._step_event.set()

    def submit_play_call(self, play_call: PlayCall) -> None:
        """Submit a play call in manual mode."""
        self._pending_play_call = play_call
        self._play_call_event.set()
        self._awaiting_play_call = False

    def simulate_single_play(self) -> Optional[PlayResult]:
        """
        Simulate a single play with AI calls.

        For REST API use when not using continuous simulation.
        """
        if self.game_state is None:
            self.create_game()

        if self.game_state.is_game_over:
            return None

        result = self.engine.simulate_play_with_ai(self.game_state)

        # Check for quarter/half transitions
        self.engine._check_quarter_end(self.game_state)
        if self.game_state.phase == GamePhase.HALFTIME:
            self.engine._handle_halftime(self.game_state)

        return result

    def simulate_with_play_call(self, play_call: PlayCall) -> Optional[PlayResult]:
        """
        Simulate a single play with a specific play call.

        For REST API use with manual play calling.
        """
        if self.game_state is None:
            self.create_game()

        if self.game_state.is_game_over:
            return None

        def_call = self.engine._get_ai_defensive_call(self.game_state)
        result = self.engine.simulate_play(self.game_state, play_call, def_call)

        # Check for quarter/half transitions
        self.engine._check_quarter_end(self.game_state)
        if self.game_state.phase == GamePhase.HALFTIME:
            self.engine._handle_halftime(self.game_state)

        return result

    async def run_simulation(
        self,
        on_awaiting_play_call: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Run game simulation as async task.

        This is the main simulation loop that respects pacing and pause states.
        Used for WebSocket-based real-time simulation.
        """
        if self.game_state is None:
            self.create_game()

        self._running = True

        try:
            while not self.game_state.is_game_over:
                # Respect pause state
                await self._paused.wait()

                if self._simulation_mode == "manual":
                    # Signal that we're awaiting a play call
                    self._awaiting_play_call = True
                    if on_awaiting_play_call:
                        on_awaiting_play_call()

                    # Wait for play call
                    await self._play_call_event.wait()
                    self._play_call_event.clear()

                    if self._pending_play_call is None:
                        continue

                    # Execute the called play
                    play_call = self._pending_play_call
                    self._pending_play_call = None
                    def_call = self.engine._get_ai_defensive_call(self.game_state)
                    self.engine.simulate_play(self.game_state, play_call, def_call)
                else:
                    # Auto simulation - AI calls plays
                    self._awaiting_play_call = False
                    self.engine.simulate_play_with_ai(self.game_state)

                # Check for quarter/half transitions
                self.engine._check_quarter_end(self.game_state)
                if self.game_state.phase == GamePhase.HALFTIME:
                    self.engine._handle_halftime(self.game_state)

                # Apply pacing delay
                delay = PACING_DELAYS.get(self.current_pacing, 0.5)
                if delay is None:
                    # Step mode - wait for user input
                    self._step_event.clear()
                    await self._step_event.wait()
                elif delay > 0:
                    await asyncio.sleep(delay)

            # Game over - emit final event
            self.engine._emit_game_end_event(self.game_state)
        finally:
            self._running = False

    def stop_simulation(self) -> None:
        """Stop the simulation loop."""
        self._running = False
        # Release any waiting events
        self._step_event.set()
        self._play_call_event.set()
        self._paused.set()

    def get_quick_play_calls(self) -> dict[str, PlayCall]:
        """Get available quick play calls for manual mode."""
        return {
            "run_inside": PlayCall.run(RunType.INSIDE),
            "run_outside": PlayCall.run(RunType.OUTSIDE),
            "pass_short": PlayCall.pass_play(PassType.SHORT),
            "pass_medium": PlayCall.pass_play(PassType.MEDIUM),
            "pass_deep": PlayCall.pass_play(PassType.DEEP),
            "punt": PlayCall.punt(),
            "field_goal": PlayCall.field_goal(),
        }

    def get_team_stats(self) -> dict:
        """Get team statistics for both teams."""
        home_stats = self.game_log.get_team_stats(is_home=True)
        away_stats = self.game_log.get_team_stats(is_home=False)

        def stats_to_dict(stats) -> dict:
            return {
                "plays": stats.pass_attempts + stats.rush_attempts,
                "total_yards": stats.total_yards,
                "passing_yards": stats.pass_yards,
                "rushing_yards": stats.rush_yards,
                "first_downs": 0,  # Not tracked yet
                "third_down_conversions": 0,  # Not tracked yet
                "third_down_attempts": 0,  # Not tracked yet
                "fourth_down_conversions": 0,  # Not tracked yet
                "fourth_down_attempts": 0,  # Not tracked yet
                "turnovers": stats.turnovers,
                "penalties": 0,  # Not tracked yet
                "penalty_yards": 0,  # Not tracked yet
            }

        return {
            "home": stats_to_dict(home_stats),
            "away": stats_to_dict(away_stats),
        }

    def get_player_stats(self) -> dict:
        """Get player statistics."""
        return self.game_log.get_player_stats()

    def get_play_log_entries(self) -> list[str]:
        """Get play log entries."""
        return self.game_log.entries
