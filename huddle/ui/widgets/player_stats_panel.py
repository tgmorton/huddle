"""Player statistics panel widget."""

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Static

from huddle.logging.game_log import PlayerStats


class TeamPlayerStats(VerticalScroll):
    """Single team's player statistics display."""

    def __init__(self, team_abbrev: str = "TEAM", **kwargs) -> None:
        super().__init__(**kwargs)
        self._team_abbrev = team_abbrev
        self._player_stats: dict[str, PlayerStats] = {}

    def compose(self) -> ComposeResult:
        """Compose the panel."""
        yield Static("", id="team-player-stats-content")

    def set_team_name(self, team_abbrev: str) -> None:
        """Set team abbreviation."""
        self._team_abbrev = team_abbrev

    def update_stats(self, all_player_stats: dict[str, PlayerStats]) -> None:
        """Update player statistics display for this team."""
        if not self.is_mounted:
            return

        # Filter to just this team's players
        team_players = [
            ps for ps in all_player_stats.values()
            if ps.team_abbrev == self._team_abbrev
        ]

        lines = []
        lines.append(f"{'=' * 32}")
        lines.append(f"  {self._team_abbrev:^28}")
        lines.append(f"{'=' * 32}")

        # Passing
        lines.append("")
        lines.append("  PASSING")
        lines.append(f"  {'Name':<12} {'C/A':>5} {'YD':>4} {'TD':>2} {'IN':>2}")
        lines.append("  " + "-" * 28)

        passers = [p for p in team_players if p.pass_attempts > 0]
        passers.sort(key=lambda p: p.pass_yards, reverse=True)
        for ps in passers[:3]:
            comp_att = f"{ps.pass_completions}/{ps.pass_attempts}"
            lines.append(
                f"  {ps.player_name[:12]:<12} {comp_att:>5} {ps.pass_yards:>4} "
                f"{ps.pass_tds:>2} {ps.interceptions:>2}"
            )
        if not passers:
            lines.append("  (none)")

        # Rushing
        lines.append("")
        lines.append("  RUSHING")
        lines.append(f"  {'Name':<12} {'ATT':>4} {'YD':>5} {'AVG':>4} {'TD':>2}")
        lines.append("  " + "-" * 28)

        rushers = [p for p in team_players if p.rush_attempts > 0]
        rushers.sort(key=lambda p: p.rush_yards, reverse=True)
        for ps in rushers[:5]:
            lines.append(
                f"  {ps.player_name[:12]:<12} {ps.rush_attempts:>4} {ps.rush_yards:>5} "
                f"{ps.yards_per_carry:>4.1f} {ps.rush_tds:>2}"
            )
        if not rushers:
            lines.append("  (none)")

        # Receiving
        lines.append("")
        lines.append("  RECEIVING")
        lines.append(f"  {'Name':<12} {'REC':>4} {'YD':>5} {'AVG':>4} {'TD':>2}")
        lines.append("  " + "-" * 28)

        receivers = [p for p in team_players if p.receptions > 0]
        receivers.sort(key=lambda p: p.receiving_yards, reverse=True)
        for ps in receivers[:5]:
            lines.append(
                f"  {ps.player_name[:12]:<12} {ps.receptions:>4} {ps.receiving_yards:>5} "
                f"{ps.yards_per_reception:>4.1f} {ps.receiving_tds:>2}"
            )
        if not receivers:
            lines.append("  (none)")

        # Defense
        lines.append("")
        lines.append("  DEFENSE")
        lines.append(f"  {'Name':<12} {'TKL':>4} {'SCK':>4} {'INT':>4}")
        lines.append("  " + "-" * 28)

        defenders = [
            p for p in team_players
            if p.tackles > 0 or p.sacks > 0 or p.interceptions_def > 0
        ]
        defenders.sort(key=lambda p: (p.tackles + p.sacks * 2 + p.interceptions_def * 3), reverse=True)
        for ps in defenders[:5]:
            lines.append(
                f"  {ps.player_name[:12]:<12} {ps.tackles:>4} {ps.sacks:>4} {ps.interceptions_def:>4}"
            )
        if not defenders:
            lines.append("  (none)")

        content = "\n".join(lines)
        try:
            content_widget = self.query_one("#team-player-stats-content", Static)
            content_widget.update(content)
        except Exception:
            pass


class PlayerStatsPanel(Horizontal):
    """Side-by-side player statistics display for both teams."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._home_abbrev = "HOME"
        self._away_abbrev = "AWAY"

    def compose(self) -> ComposeResult:
        """Compose the panel with two team columns."""
        yield TeamPlayerStats(id="away-player-stats")
        yield Static(" | ", classes="player-stats-separator")
        yield TeamPlayerStats(id="home-player-stats")

    def on_mount(self) -> None:
        """Set initial team names."""
        away_col = self.query_one("#away-player-stats", TeamPlayerStats)
        home_col = self.query_one("#home-player-stats", TeamPlayerStats)
        away_col.set_team_name(self._away_abbrev)
        home_col.set_team_name(self._home_abbrev)

    def set_team_names(self, home_abbrev: str, away_abbrev: str) -> None:
        """Set team abbreviations."""
        self._home_abbrev = home_abbrev
        self._away_abbrev = away_abbrev
        if self.is_mounted:
            away_col = self.query_one("#away-player-stats", TeamPlayerStats)
            home_col = self.query_one("#home-player-stats", TeamPlayerStats)
            away_col.set_team_name(away_abbrev)
            home_col.set_team_name(home_abbrev)

    def update_stats(self, player_stats: dict[str, PlayerStats]) -> None:
        """Update both teams' player statistics."""
        if not self.is_mounted:
            return

        away_col = self.query_one("#away-player-stats", TeamPlayerStats)
        home_col = self.query_one("#home-player-stats", TeamPlayerStats)
        away_col.update_stats(player_stats)
        home_col.update_stats(player_stats)
