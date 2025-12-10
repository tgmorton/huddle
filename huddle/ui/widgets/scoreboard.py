"""Scoreboard widget displaying game status."""

from rich.text import Text
from textual.reactive import reactive
from textual.widgets import Static


class Scoreboard(Static):
    """Displays current game status: score, quarter, clock, down/distance."""

    # Reactive attributes for automatic UI updates
    home_score: reactive[int] = reactive(0)
    away_score: reactive[int] = reactive(0)
    home_name: reactive[str] = reactive("HOME")
    away_name: reactive[str] = reactive("AWAY")
    quarter: reactive[int] = reactive(1)
    time_remaining: reactive[str] = reactive("15:00")
    down: reactive[int] = reactive(1)
    yards_to_go: reactive[int] = reactive(10)
    field_position: reactive[str] = reactive("OWN 25")
    possession_is_home: reactive[bool] = reactive(True)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def render(self) -> Text:
        """Render the scoreboard with Rich styling."""
        text = Text()

        # Quarter display
        quarter_names = {1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4", 5: "OT"}
        q_display = quarter_names.get(self.quarter, f"Q{self.quarter}")

        # Down and distance
        down_suffix = {1: "st", 2: "nd", 3: "rd", 4: "th"}
        down_str = f"{self.down}{down_suffix.get(self.down, 'th')}"

        # Build score line with styling
        # Away team section
        if not self.possession_is_home:
            text.append("● ", style="bold #2e7d32")  # Green possession dot
        else:
            text.append("  ")
        text.append(f"{self.away_name:>4} ", style="bold")
        text.append(f"{self.away_score:>2}", style="bold #1a1a1a")

        # Center section - quarter and time
        text.append("    ")
        text.append(f"{q_display}", style="bold #666666")
        text.append(f"  {self.time_remaining}  ", style="#1a1a1a")

        # Home team section
        text.append(f"{self.home_score:<2}", style="bold #1a1a1a")
        text.append(f" {self.home_name:<4}", style="bold")
        if self.possession_is_home:
            text.append(" ●", style="bold #2e7d32")  # Green possession dot
        else:
            text.append("  ")

        # New line for situation
        text.append("\n")

        # Situation line - centered with styling
        situation = f"{down_str} & {self.yards_to_go}"
        position = f"at {self.field_position}"

        # Calculate padding for centering
        total_len = len(situation) + 1 + len(position)
        padding = (50 - total_len) // 2
        text.append(" " * padding)
        text.append(situation, style="bold")
        text.append(" ")
        text.append(position, style="#666666")

        return text

    def watch_home_score(self, new_score: int) -> None:
        """Called when home_score changes."""
        self.refresh()

    def watch_away_score(self, new_score: int) -> None:
        """Called when away_score changes."""
        self.refresh()

    def watch_quarter(self, new_quarter: int) -> None:
        """Called when quarter changes."""
        self.refresh()

    def watch_time_remaining(self, new_time: str) -> None:
        """Called when time changes."""
        self.refresh()

    def watch_down(self, new_down: int) -> None:
        """Called when down changes."""
        self.refresh()

    def watch_yards_to_go(self, new_yards: int) -> None:
        """Called when yards to go changes."""
        self.refresh()

    def watch_field_position(self, new_position: str) -> None:
        """Called when field position changes."""
        self.refresh()

    def watch_possession_is_home(self, is_home: bool) -> None:
        """Called when possession changes."""
        self.refresh()
