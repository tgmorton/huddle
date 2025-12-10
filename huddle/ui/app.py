"""Main Huddle TUI application."""

from pathlib import Path

from textual.app import App
from textual.binding import Binding

from huddle.core.models.team import Team
from huddle.generators import generate_team
from huddle.ui.screens.game_screen import GameScreen


class HuddleApp(App):
    """Main Textual application for Huddle football simulator."""

    TITLE = "Huddle Football Simulator"
    SUB_TITLE = "American Football TUI"

    CSS_PATH = Path(__file__).parent / "styles" / "game.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True, priority=True),
        Binding("question_mark", "help", "Help", show=True),
    ]

    def __init__(
        self,
        home_team: Team | None = None,
        away_team: Team | None = None,
        debug_mode: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.home_team = home_team
        self.away_team = away_team

        # Disable mouse in debug mode to allow text selection
        if debug_mode:
            self.mouse_over = None  # type: ignore

    def on_mount(self) -> None:
        """Set up the app on mount."""
        # Generate teams if not provided
        if self.home_team is None:
            self.home_team = generate_team("Eagles", "Philadelphia", "PHI", overall_range=(75, 85))

        if self.away_team is None:
            self.away_team = generate_team("Cowboys", "Dallas", "DAL", overall_range=(75, 85))

        # Push the game screen
        self.push_screen(GameScreen(self.home_team, self.away_team))

    def action_help(self) -> None:
        """Show help information."""
        self.notify(
            "Keys: 1/2/3=Layout, Space=Step, P=Pause, +/-=Speed, A=Auto/Manual, Q=Quit",
            title="Controls",
            timeout=5,
        )


def run_app(
    home_team: Team | None = None,
    away_team: Team | None = None,
) -> None:
    """Run the Huddle TUI application."""
    app = HuddleApp(home_team=home_team, away_team=away_team)
    app.run()
