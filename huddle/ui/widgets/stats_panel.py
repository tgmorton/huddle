"""Team statistics panel widget."""

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Static

from huddle.logging.game_log import TeamStats


# Stats styling
STYLE_HEADER = "bold #1565c0"
STYLE_CATEGORY = "bold #666666"
STYLE_VALUE = "#1a1a1a"
STYLE_HIGHLIGHT = "bold #2e7d32"
STYLE_DANGER = "bold #c62828"
STYLE_MUTED = "#888888"


class TeamStatsColumn(Static):
    """Single team's statistics display."""

    team_name: reactive[str] = reactive("TEAM")
    stats: reactive[TeamStats | None] = reactive(None)

    def render(self) -> Text:
        """Render team statistics with Rich styling."""
        text = Text()

        # Team header
        header = f"  {self.team_name:^20}  "
        text.append(header + "\n", style=STYLE_HEADER)
        text.append("─" * 24 + "\n", style=STYLE_MUTED)

        if self.stats is None:
            text.append("  No stats available", style="italic dim")
            return text

        s = self.stats

        # Passing section
        text.append("  PASSING\n", style=STYLE_CATEGORY)
        text.append(f"    {s.pass_completions}/{s.pass_attempts} ", style=STYLE_VALUE)
        text.append(f"({s.completion_pct:.1f}%)\n", style=STYLE_MUTED)
        text.append(f"    {s.pass_yards}", style=STYLE_VALUE)
        text.append(" yards\n", style=STYLE_MUTED)

        # TD/INT with color
        text.append("    ")
        if s.pass_tds > 0:
            text.append(f"{s.pass_tds} TD", style=STYLE_HIGHLIGHT)
        else:
            text.append(f"{s.pass_tds} TD", style=STYLE_VALUE)
        text.append(", ")
        if s.interceptions > 0:
            text.append(f"{s.interceptions} INT", style=STYLE_DANGER)
        else:
            text.append(f"{s.interceptions} INT", style=STYLE_VALUE)
        text.append("\n")

        # Rushing section
        text.append("  RUSHING\n", style=STYLE_CATEGORY)
        text.append(f"    {s.rush_attempts}", style=STYLE_VALUE)
        text.append(" carries\n", style=STYLE_MUTED)
        text.append(f"    {s.rush_yards}", style=STYLE_VALUE)
        text.append(f" yards ({s.yards_per_rush:.1f}/car)\n", style=STYLE_MUTED)

        if s.rush_tds > 0:
            text.append(f"    {s.rush_tds} TD\n", style=STYLE_HIGHLIGHT)
        else:
            text.append(f"    {s.rush_tds} TD\n", style=STYLE_VALUE)

        # Totals section
        text.append("  TOTAL\n", style=STYLE_CATEGORY)
        text.append(f"    {s.total_yards}", style="bold")
        text.append(" yards\n", style=STYLE_MUTED)

        if s.total_tds > 0:
            text.append(f"    {s.total_tds} TD\n", style=STYLE_HIGHLIGHT)
        else:
            text.append(f"    {s.total_tds} TD\n", style=STYLE_VALUE)

        # Other section
        text.append("  OTHER\n", style=STYLE_CATEGORY)
        text.append("    Sacks: ", style=STYLE_MUTED)
        text.append(f"{s.sacks}\n", style=STYLE_VALUE)
        text.append("    Turnovers: ", style=STYLE_MUTED)
        if s.turnovers > 0:
            text.append(f"{s.turnovers}\n", style=STYLE_DANGER)
        else:
            text.append(f"{s.turnovers}\n", style=STYLE_VALUE)
        text.append("    FG: ", style=STYLE_MUTED)
        text.append(f"{s.field_goals_made}/{s.field_goals_attempted}", style=STYLE_VALUE)

        return text

    def watch_stats(self, stats: TeamStats | None) -> None:
        """Called when stats change."""
        self.refresh()

    def watch_team_name(self, name: str) -> None:
        """Called when team name changes."""
        self.refresh()


class StatsPanel(Horizontal):
    """Side-by-side team statistics display."""

    def __init__(
        self,
        home_name: str = "HOME",
        away_name: str = "AWAY",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._home_name = home_name
        self._away_name = away_name

    def compose(self) -> ComposeResult:
        """Compose the stats panel."""
        yield TeamStatsColumn(id="away-stats-col")
        yield Static(" | ", classes="stats-separator")
        yield TeamStatsColumn(id="home-stats-col")

    def on_mount(self) -> None:
        """Set initial team names."""
        away_col = self.query_one("#away-stats-col", TeamStatsColumn)
        home_col = self.query_one("#home-stats-col", TeamStatsColumn)
        away_col.team_name = self._away_name
        home_col.team_name = self._home_name

    def update_stats(self, home_stats: TeamStats, away_stats: TeamStats) -> None:
        """Update both teams' statistics."""
        away_col = self.query_one("#away-stats-col", TeamStatsColumn)
        home_col = self.query_one("#home-stats-col", TeamStatsColumn)
        away_col.stats = away_stats
        home_col.stats = home_stats
        # Force refresh since stats objects are mutated in place
        away_col.refresh()
        home_col.refresh()

    def set_team_names(self, home_name: str, away_name: str) -> None:
        """Set team names."""
        self._home_name = home_name
        self._away_name = away_name
        try:
            away_col = self.query_one("#away-stats-col", TeamStatsColumn)
            home_col = self.query_one("#home-stats-col", TeamStatsColumn)
            away_col.team_name = away_name
            home_col.team_name = home_name
        except Exception:
            pass  # Widget not yet mounted
