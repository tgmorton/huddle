"""Markdown game summary writer."""

from datetime import datetime
from pathlib import Path
from typing import TextIO

from huddle.core.models.game import GameState
from huddle.core.models.team import Team
from huddle.logging.game_log import GameLog


class MarkdownGameWriter:
    """Generates markdown game summaries."""

    def write_game_summary(
        self,
        game_state: GameState,
        game_log: GameLog,
        home_team: Team,
        away_team: Team,
        output_path: Path,
    ) -> None:
        """
        Write complete game summary to markdown file.

        Args:
            game_state: Final game state
            game_log: Log of all game events
            home_team: Home team
            away_team: Away team
            output_path: Path to write markdown file
        """
        with open(output_path, "w") as f:
            self._write_header(f, game_state, home_team, away_team)
            self._write_score_summary(f, game_state, home_team, away_team)
            self._write_scoring_plays(f, game_log, home_team, away_team)
            self._write_game_stats(f, game_log, home_team, away_team)
            self._write_play_by_play(f, game_log)
            self._write_footer(f)

    def generate_summary_string(
        self,
        game_state: GameState,
        game_log: GameLog,
        home_team: Team,
        away_team: Team,
    ) -> str:
        """Generate markdown summary as a string."""
        lines = []

        # Header
        lines.append(f"# {away_team.full_name} @ {home_team.full_name}")
        lines.append("")
        lines.append(f"**Final Score:** {away_team.abbreviation} {game_state.score.away_score} - "
                    f"{home_team.abbreviation} {game_state.score.home_score}")
        lines.append("")

        # Box score
        lines.append("## Box Score")
        lines.append("")
        lines.append("| Team | Q1 | Q2 | Q3 | Q4 | Final |")
        lines.append("|------|----|----|----|----|-------|")

        home_by_q = game_state.score.home_by_quarter
        away_by_q = game_state.score.away_by_quarter

        # Pad to 4 quarters
        while len(home_by_q) < 4:
            home_by_q.append(0)
        while len(away_by_q) < 4:
            away_by_q.append(0)

        lines.append(f"| {away_team.abbreviation} | {away_by_q[0]} | {away_by_q[1]} | "
                    f"{away_by_q[2]} | {away_by_q[3]} | **{game_state.score.away_score}** |")
        lines.append(f"| {home_team.abbreviation} | {home_by_q[0]} | {home_by_q[1]} | "
                    f"{home_by_q[2]} | {home_by_q[3]} | **{game_state.score.home_score}** |")
        lines.append("")

        # Scoring plays
        lines.append("## Scoring Summary")
        lines.append("")
        scoring_plays = game_log.get_scoring_summary()
        if scoring_plays:
            current_quarter = 0
            for play in scoring_plays:
                if play.quarter != current_quarter:
                    current_quarter = play.quarter
                    lines.append(f"### Quarter {current_quarter}")
                    lines.append("")

                score_str = f"{play.away_score_after}-{play.home_score_after}"
                lines.append(f"- **{play.time_remaining}** - {play.team_abbrev} {play.scoring_type} "
                           f"({score_str})")
            lines.append("")
        else:
            lines.append("*No scoring plays*")
            lines.append("")

        # Team stats
        home_stats = game_log.home_stats
        away_stats = game_log.away_stats

        lines.append("## Team Statistics")
        lines.append("")
        lines.append(f"| Statistic | {away_team.abbreviation} | {home_team.abbreviation} |")
        lines.append("|-----------|:---:|:---:|")
        lines.append(f"| Total Yards | {away_stats.total_yards} | {home_stats.total_yards} |")
        lines.append(f"| Passing Yards | {away_stats.pass_yards} | {home_stats.pass_yards} |")
        lines.append(f"| Rushing Yards | {away_stats.rush_yards} | {home_stats.rush_yards} |")
        lines.append(f"| Pass Attempts | {away_stats.pass_attempts} | {home_stats.pass_attempts} |")
        lines.append(f"| Completions | {away_stats.pass_completions} | {home_stats.pass_completions} |")
        lines.append(f"| Comp % | {away_stats.completion_pct:.1f}% | {home_stats.completion_pct:.1f}% |")
        lines.append(f"| Rush Attempts | {away_stats.rush_attempts} | {home_stats.rush_attempts} |")
        lines.append(f"| Yards/Rush | {away_stats.yards_per_rush:.1f} | {home_stats.yards_per_rush:.1f} |")
        lines.append(f"| Sacks | {away_stats.sacks} | {home_stats.sacks} |")
        lines.append(f"| Turnovers | {away_stats.turnovers} | {home_stats.turnovers} |")
        lines.append(f"| FG Made/Att | {away_stats.field_goals_made}/{away_stats.field_goals_attempted} | {home_stats.field_goals_made}/{home_stats.field_goals_attempted} |")
        lines.append("")

        # Play-by-play (condensed)
        lines.append("## Play-by-Play")
        lines.append("")

        by_quarter = game_log.get_plays_by_quarter()
        for quarter in sorted(by_quarter.keys()):
            lines.append(f"### Quarter {quarter}")
            lines.append("")

            plays = by_quarter[quarter]
            # Show only significant plays (scoring, turnovers, big gains)
            for entry in plays:
                if entry.is_scoring_play or entry.is_turnover:
                    lines.append(f"**{entry.time_remaining}** - {entry.description}")
                elif entry.yards_gained is not None and abs(entry.yards_gained) >= 15:
                    lines.append(f"**{entry.time_remaining}** - {entry.description}")

            lines.append("")

        # Footer
        lines.append("---")
        lines.append(f"*Generated by Huddle Football Simulator - {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

        return "\n".join(lines)

    def _write_header(
        self, f: TextIO, game_state: GameState, home_team: Team, away_team: Team
    ) -> None:
        """Write game header."""
        f.write(f"# {away_team.full_name} @ {home_team.full_name}\n\n")
        f.write(f"**Final Score:** {away_team.abbreviation} {game_state.score.away_score} - "
               f"{home_team.abbreviation} {game_state.score.home_score}\n\n")

    def _write_score_summary(
        self, f: TextIO, game_state: GameState, home_team: Team, away_team: Team
    ) -> None:
        """Write quarter-by-quarter scoring summary."""
        f.write("## Box Score\n\n")
        f.write("| Team | Q1 | Q2 | Q3 | Q4 | Final |\n")
        f.write("|------|----|----|----|----|-------|\n")

        home_by_q = game_state.score.home_by_quarter
        away_by_q = game_state.score.away_by_quarter

        # Pad to 4 quarters
        while len(home_by_q) < 4:
            home_by_q.append(0)
        while len(away_by_q) < 4:
            away_by_q.append(0)

        f.write(f"| {away_team.abbreviation} | {away_by_q[0]} | {away_by_q[1]} | "
               f"{away_by_q[2]} | {away_by_q[3]} | **{game_state.score.away_score}** |\n")
        f.write(f"| {home_team.abbreviation} | {home_by_q[0]} | {home_by_q[1]} | "
               f"{home_by_q[2]} | {home_by_q[3]} | **{game_state.score.home_score}** |\n")
        f.write("\n")

    def _write_scoring_plays(
        self, f: TextIO, game_log: GameLog, home_team: Team, away_team: Team
    ) -> None:
        """Write scoring plays summary."""
        f.write("## Scoring Summary\n\n")

        scoring_plays = game_log.get_scoring_summary()
        if not scoring_plays:
            f.write("*No scoring plays*\n\n")
            return

        current_quarter = 0
        for play in scoring_plays:
            if play.quarter != current_quarter:
                current_quarter = play.quarter
                f.write(f"### Quarter {current_quarter}\n\n")

            score_str = f"{play.away_score_after}-{play.home_score_after}"
            f.write(f"- **{play.time_remaining}** - {play.team_abbrev} {play.scoring_type} "
                   f"({score_str})\n")

        f.write("\n")

    def _write_game_stats(
        self, f: TextIO, game_log: GameLog, home_team: Team, away_team: Team
    ) -> None:
        """Write game statistics."""
        f.write("## Team Statistics\n\n")

        home_stats = game_log.home_stats
        away_stats = game_log.away_stats

        # Create a comparison table
        f.write(f"| Statistic | {away_team.abbreviation} | {home_team.abbreviation} |\n")
        f.write("|-----------|:---:|:---:|\n")
        f.write(f"| Total Yards | {away_stats.total_yards} | {home_stats.total_yards} |\n")
        f.write(f"| Passing Yards | {away_stats.pass_yards} | {home_stats.pass_yards} |\n")
        f.write(f"| Rushing Yards | {away_stats.rush_yards} | {home_stats.rush_yards} |\n")
        f.write(f"| Pass Attempts | {away_stats.pass_attempts} | {home_stats.pass_attempts} |\n")
        f.write(f"| Completions | {away_stats.pass_completions} | {home_stats.pass_completions} |\n")
        f.write(f"| Comp % | {away_stats.completion_pct:.1f}% | {home_stats.completion_pct:.1f}% |\n")
        f.write(f"| Rush Attempts | {away_stats.rush_attempts} | {home_stats.rush_attempts} |\n")
        f.write(f"| Yards/Rush | {away_stats.yards_per_rush:.1f} | {home_stats.yards_per_rush:.1f} |\n")
        f.write(f"| Sacks | {away_stats.sacks} | {home_stats.sacks} |\n")
        f.write(f"| Turnovers | {away_stats.turnovers} | {home_stats.turnovers} |\n")
        f.write(f"| FG Made/Att | {away_stats.field_goals_made}/{away_stats.field_goals_attempted} | {home_stats.field_goals_made}/{home_stats.field_goals_attempted} |\n")
        f.write("\n")

    def _write_play_by_play(self, f: TextIO, game_log: GameLog) -> None:
        """Write full play-by-play."""
        f.write("## Play-by-Play\n\n")

        by_quarter = game_log.get_plays_by_quarter()
        for quarter in sorted(by_quarter.keys()):
            f.write(f"### Quarter {quarter}\n\n")

            for entry in by_quarter[quarter]:
                if entry.event_type == "PLAY":
                    prefix = ""
                    if entry.is_scoring_play:
                        prefix = "**TD** "
                    elif entry.is_turnover:
                        prefix = "**TO** "

                    f.write(f"- {prefix}**{entry.time_remaining}** - {entry.description}\n")

            f.write("\n")

    def _write_footer(self, f: TextIO) -> None:
        """Write footer."""
        f.write("---\n")
        f.write(f"*Generated by Huddle Football Simulator - {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")
