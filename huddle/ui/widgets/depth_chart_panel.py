"""Depth chart display widget."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Static

from huddle.core.models.player import Player
from huddle.core.models.team import Team


# Position groups for organized display
POSITION_GROUPS = {
    "offense": {
        "Skill": ["QB", "RB", "FB", "WR", "TE"],
        "O-Line": ["LT", "LG", "C", "RG", "RT"],
    },
    "defense": {
        "D-Line": ["DE", "DT"],
        "Linebackers": ["OLB", "MLB", "ILB"],
        "Secondary": ["CB", "FS", "SS"],
    },
    "special": {
        "Specialists": ["K", "P", "LS"],
    },
}


def _format_player(player: Player | None, slot: str) -> str:
    """Format a player entry for display."""
    if player is None:
        return f"  {slot}: --"

    # Format: "12-T.Brady (85)"
    jersey = player.jersey_number
    name = player.display_name
    overall = player.overall
    return f"  {slot}: {jersey}-{name} ({overall})"


class TeamDepthColumn(Static):
    """Single team's depth chart display."""

    team: reactive[Team | None] = reactive(None)

    def render(self) -> str:
        """Render team depth chart."""
        if self.team is None:
            return "No team data"

        lines = []
        lines.append(f"  {self.team.abbreviation:^22}  ")
        lines.append("=" * 26)

        # Offense
        lines.append("")
        lines.append("  OFFENSE")
        lines.append("  -------")
        for group_name, positions in POSITION_GROUPS["offense"].items():
            for pos in positions:
                # Show up to 2 depths for each position
                for depth in range(1, 3):
                    slot = f"{pos}{depth}"
                    player = self.team.get_starter(slot)
                    if player or depth == 1:
                        lines.append(_format_player(player, slot))

        # Defense
        lines.append("")
        lines.append("  DEFENSE")
        lines.append("  -------")
        for group_name, positions in POSITION_GROUPS["defense"].items():
            for pos in positions:
                # Show up to 2 depths for each position
                for depth in range(1, 3):
                    slot = f"{pos}{depth}"
                    player = self.team.get_starter(slot)
                    if player or depth == 1:
                        lines.append(_format_player(player, slot))

        # Special Teams
        lines.append("")
        lines.append("  SPECIAL TEAMS")
        lines.append("  -------------")
        for group_name, positions in POSITION_GROUPS["special"].items():
            for pos in positions:
                slot = f"{pos}1"
                player = self.team.get_starter(slot)
                lines.append(_format_player(player, slot))

        return "\n".join(lines)

    def watch_team(self, team: Team | None) -> None:
        """Called when team changes."""
        self.refresh()


class DepthChartPanel(Horizontal):
    """Side-by-side depth chart display for both teams."""

    def __init__(
        self,
        home_team: Team | None = None,
        away_team: Team | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._home_team = home_team
        self._away_team = away_team

    def compose(self) -> ComposeResult:
        """Compose the depth chart panel."""
        yield TeamDepthColumn(id="away-depth-col")
        yield Static(" | ", classes="depth-chart-separator")
        yield TeamDepthColumn(id="home-depth-col")

    def on_mount(self) -> None:
        """Set initial teams."""
        if self._home_team:
            home_col = self.query_one("#home-depth-col", TeamDepthColumn)
            home_col.team = self._home_team
        if self._away_team:
            away_col = self.query_one("#away-depth-col", TeamDepthColumn)
            away_col.team = self._away_team

    def set_teams(self, home_team: Team, away_team: Team) -> None:
        """Set both teams for display."""
        self._home_team = home_team
        self._away_team = away_team
        try:
            away_col = self.query_one("#away-depth-col", TeamDepthColumn)
            home_col = self.query_one("#home-depth-col", TeamDepthColumn)
            away_col.team = away_team
            home_col.team = home_team
        except Exception:
            pass  # Widget not yet mounted

    def refresh_display(self) -> None:
        """Force refresh of depth chart display."""
        try:
            away_col = self.query_one("#away-depth-col", TeamDepthColumn)
            home_col = self.query_one("#home-depth-col", TeamDepthColumn)
            away_col.refresh()
            home_col.refresh()
        except Exception:
            pass
