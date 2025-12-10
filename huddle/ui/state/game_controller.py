"""Game controller bridging simulation engine to UI."""

import asyncio
from typing import TYPE_CHECKING, Callable, Optional

from huddle.core.enums import PassType, RunType
from huddle.core.models.game import GamePhase, GameState
from huddle.core.models.play import PlayCall
from huddle.core.models.team import Team
from huddle.events.types import (
    GameEndEvent,
    PlayCompletedEvent,
    QuarterEndEvent,
    ScoringEvent,
    TurnoverEvent,
)
from huddle.logging import GameLog
from huddle.simulation import SimulationEngine
from huddle.ui.constants import PACING_DELAYS

if TYPE_CHECKING:
    from textual.screen import Screen


class GameController:
    """
    Manages game simulation and UI synchronization.

    Bridges the SimulationEngine's EventBus to screen callbacks.
    Handles pacing, pausing, and manual play calling.
    """

    def __init__(
        self,
        screen: "Screen",
        home_team: Team,
        away_team: Team,
    ) -> None:
        self.screen = screen
        self.home_team = home_team
        self.away_team = away_team

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

        # Callbacks for UI updates
        self._on_play_completed_callback: Optional[Callable[[PlayCompletedEvent], None]] = None
        self._on_scoring_callback: Optional[Callable[[ScoringEvent], None]] = None
        self._on_turnover_callback: Optional[Callable[[TurnoverEvent], None]] = None
        self._on_quarter_end_callback: Optional[Callable[[QuarterEndEvent], None]] = None
        self._on_game_end_callback: Optional[Callable[[GameEndEvent], None]] = None
        self._on_awaiting_play_call_callback: Optional[Callable[[], None]] = None

        # Subscribe to simulation events
        self._setup_event_handlers()

        # Control state
        self.current_pacing = "fast"
        self._paused = asyncio.Event()
        self._paused.set()  # Start unpaused
        self._step_event = asyncio.Event()
        self._play_call_event = asyncio.Event()
        self._pending_play_call: Optional[PlayCall] = None
        self._simulation_mode = "auto"

    def set_callbacks(
        self,
        on_play_completed: Optional[Callable[[PlayCompletedEvent], None]] = None,
        on_scoring: Optional[Callable[[ScoringEvent], None]] = None,
        on_turnover: Optional[Callable[[TurnoverEvent], None]] = None,
        on_quarter_end: Optional[Callable[[QuarterEndEvent], None]] = None,
        on_game_end: Optional[Callable[[GameEndEvent], None]] = None,
        on_awaiting_play_call: Optional[Callable[[], None]] = None,
    ) -> None:
        """Set UI update callbacks."""
        self._on_play_completed_callback = on_play_completed
        self._on_scoring_callback = on_scoring
        self._on_turnover_callback = on_turnover
        self._on_quarter_end_callback = on_quarter_end
        self._on_game_end_callback = on_game_end
        self._on_awaiting_play_call_callback = on_awaiting_play_call

    def _setup_event_handlers(self) -> None:
        """Subscribe to simulation events and convert to callbacks."""
        event_bus = self.engine.event_bus
        event_bus.subscribe(PlayCompletedEvent, self._on_play_completed)
        event_bus.subscribe(ScoringEvent, self._on_scoring)
        event_bus.subscribe(TurnoverEvent, self._on_turnover)
        event_bus.subscribe(QuarterEndEvent, self._on_quarter_end)
        event_bus.subscribe(GameEndEvent, self._on_game_end)

    def _on_play_completed(self, event: PlayCompletedEvent) -> None:
        """Handle PlayCompletedEvent."""
        if self._on_play_completed_callback:
            self._on_play_completed_callback(event)

    def _on_scoring(self, event: ScoringEvent) -> None:
        """Handle ScoringEvent."""
        if self._on_scoring_callback:
            self._on_scoring_callback(event)

    def _on_turnover(self, event: TurnoverEvent) -> None:
        """Handle TurnoverEvent."""
        if self._on_turnover_callback:
            self._on_turnover_callback(event)

    def _on_quarter_end(self, event: QuarterEndEvent) -> None:
        """Handle QuarterEndEvent."""
        if self._on_quarter_end_callback:
            self._on_quarter_end_callback(event)

    def _on_game_end(self, event: GameEndEvent) -> None:
        """Handle GameEndEvent."""
        if self._on_game_end_callback:
            self._on_game_end_callback(event)

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

    def set_pacing(self, pacing: str) -> None:
        """Update simulation pacing."""
        self.current_pacing = pacing

    def set_mode(self, mode: str) -> None:
        """Update simulation mode (auto/manual)."""
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

    def request_step(self) -> None:
        """Signal to advance one play in step mode."""
        self._step_event.set()

    def submit_play_call(self, play_call: PlayCall) -> None:
        """Submit a play call in manual mode."""
        self._pending_play_call = play_call
        self._play_call_event.set()

    async def run_simulation(self) -> None:
        """
        Run game simulation as async task.

        This is the main simulation loop that respects pacing and pause states.
        """
        if self.game_state is None:
            self.create_game()

        while not self.game_state.is_game_over:
            # Respect pause state
            await self._paused.wait()

            if self._simulation_mode == "manual":
                # Signal UI to show play caller
                if self._on_awaiting_play_call_callback:
                    self._on_awaiting_play_call_callback()

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
