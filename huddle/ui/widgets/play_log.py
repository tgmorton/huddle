"""Play-by-play log widget."""

from dataclasses import dataclass
from typing import Optional

from rich.text import Text
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.widgets import Static


@dataclass
class PlayLogEntry:
    """Single entry in the play log."""

    quarter: int
    time_remaining: str
    down: int
    yards_to_go: int
    field_position: str
    description: str
    is_scoring: bool = False
    is_turnover: bool = False
    yards_gained: Optional[int] = None

    def format(self, compact: bool = False) -> str:
        """Format entry for display (plain text)."""
        # Time and situation
        if compact:
            prefix = f"Q{self.quarter} {self.time_remaining} | "
        else:
            prefix = f"Q{self.quarter} {self.time_remaining} | {self.down}&{self.yards_to_go} at {self.field_position} | "

        # Add markers for special plays
        if self.is_scoring:
            marker = "[TD] "
        elif self.is_turnover:
            marker = "[TO] "
        else:
            marker = ""

        return f"{prefix}{marker}{self.description}"

    def format_rich(self, compact: bool = False) -> Text:
        """Format entry for display with Rich styling."""
        text = Text()

        # Time prefix - muted color
        if compact:
            text.append(f"Q{self.quarter} {self.time_remaining}", style="#666666")
        else:
            text.append(f"Q{self.quarter} {self.time_remaining}", style="#666666")
            text.append(" │ ", style="#999999")
            text.append(f"{self.down}&{self.yards_to_go}", style="bold")
            text.append(f" at {self.field_position}", style="#666666")

        text.append(" │ ", style="#999999")

        # Add markers for special plays with colors
        if self.is_scoring:
            text.append("TD ", style="bold #f57c00")  # Orange for scoring
        elif self.is_turnover:
            text.append("TO ", style="bold #c62828")  # Red for turnover

        # Description
        text.append(self.description)

        return text


class PlayLog(VerticalScroll):
    """Scrolling list of play-by-play descriptions."""

    compact_mode: reactive[bool] = reactive(False)

    def __init__(self, max_entries: int = 200, **kwargs) -> None:
        super().__init__(**kwargs)
        self.entries: list[PlayLogEntry] = []
        self.max_entries = max_entries

    def compose(self):
        """Compose the widget."""
        yield Static("", id="play-log-content")

    def add_play(self, entry: PlayLogEntry) -> None:
        """Add a play and auto-scroll to bottom."""
        self.entries.append(entry)

        # Trim if too many entries
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]

        self._refresh_content()
        self.scroll_end(animate=False)

    def _refresh_content(self) -> None:
        """Refresh the log content."""
        if not self.is_mounted:
            return

        try:
            content_widget = self.query_one("#play-log-content", Static)

            if not self.entries:
                # Empty state with muted styling
                empty_text = Text("Waiting for game to start...", style="italic #999999")
                content_widget.update(empty_text)
                return

            # Build Rich text content
            content = Text()
            for i, entry in enumerate(self.entries):
                if i > 0:
                    content.append("\n")
                content.append(entry.format_rich(compact=self.compact_mode))

            content_widget.update(content)
        except Exception:
            pass

    def on_mount(self) -> None:
        """Initialize content on mount."""
        self._refresh_content()

    def watch_compact_mode(self, compact: bool) -> None:
        """Called when compact mode changes."""
        if self.is_mounted:
            self._refresh_content()

    def clear(self) -> None:
        """Clear all entries."""
        self.entries.clear()
        self._refresh_content()

    def get_last_plays(self, count: int = 5) -> list[PlayLogEntry]:
        """Get the last N plays."""
        return self.entries[-count:] if self.entries else []
