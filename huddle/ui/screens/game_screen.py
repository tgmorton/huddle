"""Main game screen with layout switching."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Footer, Header, Static
from textual.worker import Worker, WorkerState

from huddle.core.models.team import Team
from huddle.ui.constants import DEFAULT_LAYOUT, DEFAULT_MODE, DEFAULT_PACING, LAYOUTS
from huddle.events.types import GameEndEvent, PlayCompletedEvent
from huddle.ui.messages import (
    LayoutChangedMessage,
    PacingChangedMessage,
    PauseToggledMessage,
    PlayCallSelectedMessage,
    StepRequestedMessage,
)
from huddle.ui.state.game_controller import GameController
from huddle.ui.widgets.depth_chart_panel import DepthChartPanel
from huddle.ui.widgets.field_view import FieldView
from huddle.ui.widgets.formation_view import FormationView
from huddle.ui.widgets.pacing_control import PacingControl
from huddle.ui.widgets.play_caller import PlayCaller
from huddle.ui.widgets.play_log import PlayLog, PlayLogEntry
from huddle.ui.widgets.player_stats_panel import PlayerStatsPanel
from huddle.ui.widgets.scoreboard import Scoreboard
from huddle.ui.widgets.stats_panel import StatsPanel


class GameScreen(Screen):
    """Main game viewing screen with switchable layouts."""

    BINDINGS = [
        Binding("1", "switch_layout('play_by_play')", "Play Log", show=True),
        Binding("2", "switch_layout('field')", "Field", show=True),
        Binding("3", "switch_layout('stats')", "Stats", show=True),
        Binding("4", "switch_layout('players')", "Players", show=True),
        Binding("5", "switch_layout('depth_chart')", "Depth", show=True),
        Binding("space", "step", "Next Play", show=True),
        Binding("p", "toggle_pause", "Pause", show=True),
        Binding("t", "toggle_formation", "Formation", show=True),
        Binding("equal", "speed_up", "Faster", show=False),
        Binding("plus", "speed_up", "Faster", show=False),
        Binding("minus", "speed_down", "Slower", show=False),
        Binding("a", "toggle_mode", "Auto/Manual", show=True),
        # Manual mode play calls
        Binding("r", "call_run_inside", "Run In", show=False),
        Binding("o", "call_run_outside", "Run Out", show=False),
        Binding("s", "call_pass_short", "Short", show=False),
        Binding("m", "call_pass_medium", "Medium", show=False),
        Binding("d", "call_pass_deep", "Deep", show=False),
        Binding("u", "call_punt", "Punt", show=False),
        Binding("f", "call_fg", "FG", show=False),
    ]

    # Reactive attributes
    current_layout: reactive[str] = reactive(DEFAULT_LAYOUT)
    simulation_mode: reactive[str] = reactive(DEFAULT_MODE)
    current_pacing: reactive[str] = reactive(DEFAULT_PACING)
    is_paused: reactive[bool] = reactive(False)
    is_game_over: reactive[bool] = reactive(False)
    show_formation: reactive[bool] = reactive(True)

    def __init__(
        self,
        home_team: Team,
        away_team: Team,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.home_team = home_team
        self.away_team = away_team
        self.controller: GameController | None = None
        self._simulation_worker: Worker | None = None

    def compose(self) -> ComposeResult:
        """Compose the game screen."""
        yield Header()

        # Scoreboard at top
        yield Scoreboard(id="scoreboard")

        # Main content area with all layouts
        with Container(id="main-content", classes=f"layout-{self.current_layout}"):
            # Play log (visible in play_by_play and stats layouts)
            yield PlayLog(id="play-log", classes="section")

            # Field area with optional formation context (visible in field layout)
            with Horizontal(id="field-area"):
                yield FieldView(id="field-view")
                yield FormationView(id="formation-view")

            # Stats panel (visible in stats layout)
            yield StatsPanel(
                home_name=self.home_team.abbreviation,
                away_name=self.away_team.abbreviation,
                id="stats-panel",
                classes="section",
            )

            # Player stats panel (visible in players layout)
            yield PlayerStatsPanel(id="player-stats-panel", classes="section")

            # Depth chart panel (visible in depth_chart layout)
            yield DepthChartPanel(
                home_team=self.home_team,
                away_team=self.away_team,
                id="depth-chart-panel",
                classes="section",
            )

        # Play caller (visible in manual mode)
        yield PlayCaller(id="play-caller")

        # Pacing control
        yield PacingControl(id="pacing-control")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize controller and start simulation."""
        # Set up scoreboard with team names
        scoreboard = self.query_one("#scoreboard", Scoreboard)
        scoreboard.home_name = self.home_team.abbreviation
        scoreboard.away_name = self.away_team.abbreviation

        # Set up field view with team names and colors
        field_view = self.query_one("#field-view", FieldView)
        field_view.home_name = self.home_team.abbreviation
        field_view.away_name = self.away_team.abbreviation
        field_view.set_team_color(is_home=True, hex_color=self.home_team.primary_color)
        field_view.set_team_color(is_home=False, hex_color=self.away_team.primary_color)

        # Set up player stats panel with team names
        player_stats_panel = self.query_one("#player-stats-panel", PlayerStatsPanel)
        player_stats_panel.set_team_names(self.home_team.abbreviation, self.away_team.abbreviation)

        # Set border titles for section panels
        field_view.border_title = "Field"

        play_log = self.query_one("#play-log", PlayLog)
        play_log.border_title = "Play-by-Play"

        stats_panel = self.query_one("#stats-panel", StatsPanel)
        stats_panel.border_title = "Team Stats"

        player_stats_panel.border_title = "Player Stats"

        # Initialize controller with callbacks
        self.controller = GameController(self, self.home_team, self.away_team)
        self.controller.set_callbacks(
            on_play_completed=self._handle_play_completed,
            on_game_end=self._handle_game_end,
            on_awaiting_play_call=self._handle_awaiting_play_call,
        )
        self.controller.create_game()

        # Set initial possession in scoreboard
        if self.controller.game_state:
            possession_is_home = (
                self.controller.game_state.possession.team_with_ball
                == self.home_team.id
            )
            scoreboard.possession_is_home = possession_is_home
            field_view.possession_is_home = possession_is_home

        # Apply initial layout
        self._apply_layout(self.current_layout)

        # Hide play caller initially (auto mode)
        play_caller = self.query_one("#play-caller", PlayCaller)
        play_caller.is_active = self.simulation_mode == "manual"

        # Start simulation
        self._start_simulation()

    def _start_simulation(self) -> None:
        """Start the simulation worker."""
        if self.controller:
            self._simulation_worker = self.run_worker(
                self.controller.run_simulation(),
                exclusive=True,
                thread=False,
            )

    # --- Layout Management ---

    def action_switch_layout(self, layout: str) -> None:
        """Switch to a different layout."""
        if layout in LAYOUTS:
            self.current_layout = layout

    def watch_current_layout(self, layout: str) -> None:
        """Apply layout changes."""
        # Only apply if widget is mounted (avoid error during compose)
        if self.is_mounted:
            self._apply_layout(layout)
            self.post_message(LayoutChangedMessage(layout))

    def _apply_layout(self, layout: str) -> None:
        """Apply CSS classes for layout."""
        main_content = self.query_one("#main-content", Container)

        # Remove old layout classes
        for old_layout in LAYOUTS:
            main_content.remove_class(f"layout-{old_layout}")

        # Add new layout class
        main_content.add_class(f"layout-{layout}")

        # Update play log compact mode based on layout
        play_log = self.query_one("#play-log", PlayLog)
        play_log.compact_mode = layout != "play_by_play"

    # --- Pacing Control ---

    def action_speed_up(self) -> None:
        """Increase simulation speed."""
        pacing_order = ["step", "slow", "fast", "instant"]
        try:
            idx = pacing_order.index(self.current_pacing)
            if idx < len(pacing_order) - 1:
                self.current_pacing = pacing_order[idx + 1]
        except ValueError:
            pass

    def action_speed_down(self) -> None:
        """Decrease simulation speed."""
        pacing_order = ["step", "slow", "fast", "instant"]
        try:
            idx = pacing_order.index(self.current_pacing)
            if idx > 0:
                self.current_pacing = pacing_order[idx - 1]
        except ValueError:
            pass

    def watch_current_pacing(self, pacing: str) -> None:
        """Update controller and UI when pacing changes."""
        if self.controller:
            self.controller.set_pacing(pacing)

        if self.is_mounted:
            pacing_control = self.query_one("#pacing-control", PacingControl)
            pacing_control.current_pacing = pacing

    def on_pacing_changed_message(self, message: PacingChangedMessage) -> None:
        """Handle pacing change from control widget."""
        self.current_pacing = message.pacing

    # --- Pause/Resume ---

    def action_toggle_pause(self) -> None:
        """Toggle pause state."""
        if self.controller:
            self.controller.toggle_pause()
            self.is_paused = self.controller.is_paused

    def action_step(self) -> None:
        """Advance one play in step mode."""
        if self.controller and self.current_pacing == "step":
            self.controller.request_step()

    def on_pause_toggled_message(self, message: PauseToggledMessage) -> None:
        """Handle pause toggle from control widget."""
        self.action_toggle_pause()

    def on_step_requested_message(self, message: StepRequestedMessage) -> None:
        """Handle step request from control widget."""
        self.action_step()

    def watch_is_paused(self, paused: bool) -> None:
        """Update UI when pause state changes."""
        if self.is_mounted:
            pacing_control = self.query_one("#pacing-control", PacingControl)
            pacing_control.is_paused = paused

    # --- Formation Toggle ---

    def action_toggle_formation(self) -> None:
        """Toggle formation view visibility."""
        self.show_formation = not self.show_formation

    def watch_show_formation(self, show: bool) -> None:
        """Update formation view visibility."""
        if self.is_mounted:
            try:
                formation_view = self.query_one("#formation-view", FormationView)
                formation_view.display = show
            except Exception:
                pass

    # --- Mode Switching ---

    def action_toggle_mode(self) -> None:
        """Toggle between auto and manual mode."""
        if self.simulation_mode == "auto":
            self.simulation_mode = "manual"
        else:
            self.simulation_mode = "auto"

    def watch_simulation_mode(self, mode: str) -> None:
        """Update UI and controller when mode changes."""
        if self.controller:
            self.controller.set_mode(mode)

        if self.is_mounted:
            play_caller = self.query_one("#play-caller", PlayCaller)
            play_caller.is_active = mode == "manual"

    # --- Manual Play Calling ---

    def _handle_awaiting_play_call(self) -> None:
        """Handle request for play call in manual mode."""
        play_caller = self.query_one("#play-caller", PlayCaller)
        play_caller.request_play_call()

    def on_play_call_selected_message(self, message: PlayCallSelectedMessage) -> None:
        """Handle play call selection."""
        if self.controller:
            self.controller.submit_play_call(message.play_call)

    def action_call_run_inside(self) -> None:
        """Call inside run play."""
        play_caller = self.query_one("#play-caller", PlayCaller)
        play_caller.handle_key_call("r")

    def action_call_run_outside(self) -> None:
        """Call outside run play."""
        play_caller = self.query_one("#play-caller", PlayCaller)
        play_caller.handle_key_call("o")

    def action_call_pass_short(self) -> None:
        """Call short pass play."""
        play_caller = self.query_one("#play-caller", PlayCaller)
        play_caller.handle_key_call("s")

    def action_call_pass_medium(self) -> None:
        """Call medium pass play."""
        play_caller = self.query_one("#play-caller", PlayCaller)
        play_caller.handle_key_call("m")

    def action_call_pass_deep(self) -> None:
        """Call deep pass play."""
        play_caller = self.query_one("#play-caller", PlayCaller)
        play_caller.handle_key_call("d")

    def action_call_punt(self) -> None:
        """Call punt."""
        play_caller = self.query_one("#play-caller", PlayCaller)
        play_caller.handle_key_call("u")

    def action_call_fg(self) -> None:
        """Call field goal."""
        play_caller = self.query_one("#play-caller", PlayCaller)
        play_caller.handle_key_call("f")

    # --- Simulation Event Handlers (callbacks from controller) ---

    def _handle_play_completed(self, event: PlayCompletedEvent) -> None:
        """Handle play completion event."""
        result = event.result

        # Update scoreboard
        scoreboard = self.query_one("#scoreboard", Scoreboard)
        scoreboard.home_score = event.home_score
        scoreboard.away_score = event.away_score
        scoreboard.quarter = event.quarter
        scoreboard.time_remaining = event.time_remaining
        scoreboard.down = event.down
        scoreboard.yards_to_go = event.yards_to_go
        scoreboard.field_position = event.field_position
        scoreboard.possession_is_home = event.offense_is_home

        # Update play log
        play_log = self.query_one("#play-log", PlayLog)

        # Apply state classes for visual feedback
        play_log.remove_class("-scoring", "-turnover", "-first-down")
        if result.is_touchdown:
            play_log.add_class("-scoring")
            self.set_timer(2.0, lambda: play_log.remove_class("-scoring"))
        elif result.is_turnover:
            play_log.add_class("-turnover")
            self.set_timer(2.0, lambda: play_log.remove_class("-turnover"))
        elif result.is_first_down:
            play_log.add_class("-first-down")
            self.set_timer(1.5, lambda: play_log.remove_class("-first-down"))
        entry = PlayLogEntry(
            quarter=event.quarter,
            time_remaining=event.time_remaining,
            down=event.down,
            yards_to_go=event.yards_to_go,
            field_position=event.field_position,
            description=result.description,
            is_scoring=result.is_touchdown,
            is_turnover=result.is_turnover,
            yards_gained=result.yards_gained,
        )
        play_log.add_play(entry)

        # Update field view
        field_view = self.query_one("#field-view", FieldView)
        field_view.update_from_field_position(event.field_position, event.yards_to_go)
        field_view.possession_is_home = event.offense_is_home
        # Show special play indicator for notable plays
        field_view.show_play_result(result.outcome, result.is_first_down)

        # Update formation view with play call details and defensive scheme
        formation_view = self.query_one("#formation-view", FormationView)
        offensive_team = self.home_team if event.offense_is_home else self.away_team
        defensive_team = self.away_team if event.offense_is_home else self.home_team
        formation_view.update_from_play(
            offense_team=offensive_team,
            defense_team=defensive_team,
            formation=result.play_call.formation,
            personnel=result.play_call.personnel,
            defensive_scheme=result.defensive_call.scheme if result.defensive_call else None,
        )

        # Update stats panel
        if self.controller and self.controller.game_log:
            stats_panel = self.query_one("#stats-panel", StatsPanel)
            stats_panel.update_stats(
                self.controller.game_log.home_stats,
                self.controller.game_log.away_stats,
            )

            # Update player stats panel
            player_stats_panel = self.query_one("#player-stats-panel", PlayerStatsPanel)
            player_stats_panel.update_stats(self.controller.game_log.player_stats)

    def _handle_game_end(self, event: GameEndEvent) -> None:
        """Handle game end."""
        self.is_game_over = True

        # Update scoreboard with final scores
        scoreboard = self.query_one("#scoreboard", Scoreboard)
        scoreboard.home_score = event.final_home_score
        scoreboard.away_score = event.final_away_score

        # Add game over entry to log
        play_log = self.query_one("#play-log", PlayLog)
        final_entry = PlayLogEntry(
            quarter=4,
            time_remaining="FINAL",
            down=0,
            yards_to_go=0,
            field_position="",
            description=f"FINAL: {self.away_team.abbreviation} {event.final_away_score} - {self.home_team.abbreviation} {event.final_home_score}",
            is_scoring=False,
            is_turnover=False,
        )
        play_log.add_play(final_entry)

        # Pause the simulation
        if self.controller:
            self.controller.pause()
            self.is_paused = True
