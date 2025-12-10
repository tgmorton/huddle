"""Rich-styled football field visualization widget."""

from enum import Enum, auto
from typing import Optional

from rich.text import Text
from textual.reactive import reactive
from textual.widgets import Static

from huddle.core.enums import PlayOutcome


class SpecialPlay(Enum):
    """Special play types for visual effects."""

    NONE = auto()
    TOUCHDOWN = auto()
    FIELD_GOAL_GOOD = auto()
    FIELD_GOAL_MISS = auto()
    PUNT = auto()
    INTERCEPTION = auto()
    FUMBLE = auto()
    SAFETY = auto()
    FIRST_DOWN = auto()


class FieldView(Static):
    """
    Rich-styled football field visualization.

    Features:
    - Green field with colored end zones
    - Yellow first-down line (full height)
    - Visible ball marker with orange background
    - Cyan scrimmage line
    - Red zone shading when inside 20
    """

    # Ball position: 0 = own goal, 100 = opponent's goal
    ball_position: reactive[int] = reactive(25)
    first_down_marker: reactive[int] = reactive(35)
    possession_is_home: reactive[bool] = reactive(True)
    home_name: reactive[str] = reactive("HOME")
    away_name: reactive[str] = reactive("AWAY")

    # Team colors (Rich color names)
    home_primary_color: reactive[str] = reactive("blue")
    away_primary_color: reactive[str] = reactive("red")

    # Special play display
    special_play: reactive[SpecialPlay] = reactive(SpecialPlay.NONE)
    special_play_text: reactive[str] = reactive("")

    # Field dimensions
    FIELD_WIDTH = 53  # Playing field width in characters
    END_ZONE_WIDTH = 7  # End zone width
    FIELD_ROWS = 5  # Number of field rows
    BALL_ROW = 2  # Middle row (0-indexed) where ball appears

    # Symbols
    BALL_SYMBOL = "<*>"

    def set_team_color(self, is_home: bool, hex_color: str) -> None:
        """Set team color from hex string (e.g., '#004C54')."""
        # Rich supports hex colors directly, just ensure it starts with #
        if hex_color.startswith("#"):
            color = hex_color
        else:
            color = f"#{hex_color}"

        if is_home:
            self.home_primary_color = color
        else:
            self.away_primary_color = color

    def render(self) -> Text:
        """Render the styled field using Rich Text."""
        # Calculate display positions
        display_ball, display_fd = self._calculate_display_positions()

        # Build each section
        lines: list[Text] = []
        lines.append(self._build_header())
        lines.append(self._build_border("top"))

        for row in range(self.FIELD_ROWS):
            lines.append(self._build_field_row(row, display_ball, display_fd))

        lines.append(self._build_border("bottom"))
        lines.append(self._build_status_line())

        # Join lines
        result = Text()
        for i, line in enumerate(lines):
            result.append(line)
            if i < len(lines) - 1:
                result.append("\n")

        return result

    def _calculate_display_positions(self) -> tuple[int, int]:
        """Calculate display column positions for ball and first down."""
        # Home attacks left (toward away end zone), away attacks right
        if self.possession_is_home:
            display_ball = 100 - self.ball_position
            display_fd = 100 - self.first_down_marker
        else:
            display_ball = self.ball_position
            display_fd = self.first_down_marker

        return display_ball, display_fd

    def _pos_to_col(self, yard_pos: int) -> int:
        """Convert yard position (0-100) to field column (0 to FIELD_WIDTH-1)."""
        col = int(yard_pos * self.FIELD_WIDTH / 100)
        return max(0, min(self.FIELD_WIDTH - 1, col))

    def _is_red_zone(self, display_yard: int) -> bool:
        """Check if position is in red zone (inside 20 of goal being attacked)."""
        # Red zone is within 20 yards of the goal line we're attacking
        if self.possession_is_home:
            # Home attacks left (low numbers), so red zone is < 20
            return display_yard < 20
        else:
            # Away attacks right (high numbers), so red zone is > 80
            return display_yard > 80

    def _get_field_style(self, display_yard: int) -> str:
        """Get Rich style for a field position."""
        if self._is_red_zone(display_yard):
            return "on red"
        return "on green"

    def _build_header(self) -> Text:
        """Build header with team names and direction indicator."""
        text = Text()

        # Determine team positions
        left_team = self.away_name
        right_team = self.home_name

        if self.possession_is_home:
            offense = self.home_name
            direction = "<<<"
        else:
            offense = self.away_name
            direction = ">>>"

        # Build header: " AWAY                    PHI >>>                     HOME"
        text.append(" ")
        text.append(f"{left_team:<6}", style="bold")

        # Center section with offense and direction
        center = f"{offense} {direction}"
        padding = (self.FIELD_WIDTH + self.END_ZONE_WIDTH * 2 - 14) // 2
        text.append(" " * padding)
        text.append(center, style="bold green")
        text.append(" " * padding)

        text.append(f"{right_team:>6}", style="bold")

        return text

    def _build_border(self, position: str) -> Text:
        """Build top or bottom border with end zone edges."""
        text = Text()

        # Use box drawing characters for clean borders
        if position == "top":
            left_corner = "┌"
            right_corner = "┐"
            h_line = "─"
            t_piece = "┬"
        else:
            left_corner = "└"
            right_corner = "┘"
            h_line = "─"
            t_piece = "┴"

        # Left end zone border
        left_color = self.away_primary_color
        text.append(left_corner, style=f"on {left_color}")
        text.append(h_line * (self.END_ZONE_WIDTH - 2), style=f"on {left_color}")
        text.append(t_piece, style=f"on {left_color}")

        # Field border - match the field green
        text.append(h_line * self.FIELD_WIDTH, style="on #2e8b2e")

        # Right end zone border
        right_color = self.home_primary_color
        text.append(t_piece, style=f"on {right_color}")
        text.append(h_line * (self.END_ZONE_WIDTH - 2), style=f"on {right_color}")
        text.append(right_corner, style=f"on {right_color}")

        return text

    def _build_field_row(self, row_idx: int, ball_yard: int, fd_yard: int) -> Text:
        """Build a single field row with all elements."""
        text = Text()

        # Left end zone
        text.append(self._build_end_zone_cell(self.away_name, self.away_primary_color, row_idx, is_left=True))

        # Build field content
        ball_col = self._pos_to_col(ball_yard)
        fd_col = self._pos_to_col(fd_yard) if 0 < fd_yard < 100 else -1

        # Light theme: medium green that works on white backgrounds
        base_style = "on #2e8b2e"

        col = 0
        while col < self.FIELD_WIDTH:
            # Check if this is the ball position on the ball row
            if row_idx == self.BALL_ROW and col == ball_col:
                # Ball - bright orange/brown football on dark background
                ball_display = self.BALL_SYMBOL
                if col + len(ball_display) > self.FIELD_WIDTH:
                    ball_display = ball_display[:self.FIELD_WIDTH - col]
                text.append(ball_display, style="bold #ffffff on #8b4513")
                col += len(ball_display)
                continue

            # Check for scrimmage line (rows above/below ball)
            if row_idx in [self.BALL_ROW - 1, self.BALL_ROW + 1] and col == ball_col:
                text.append("───", style=f"bold #007fff {base_style}")
                col += 3
                continue

            # Check for first down marker (full height yellow/orange line)
            if col == fd_col and fd_col >= 0:
                text.append("│", style=f"bold #ff8c00 {base_style}")
                col += 1
                continue

            # Check for yard number markers on the middle row
            # But skip if the marker would overlap with the ball position
            if row_idx == self.BALL_ROW:
                yard_marker = self._get_yard_marker_at(col)
                if yard_marker:
                    marker_end = col + len(yard_marker)
                    # Don't draw marker if ball is within its span
                    if not (col <= ball_col < marker_end):
                        text.append(yard_marker, style=f"bold #ffffff {base_style}")
                        col += len(yard_marker)
                        continue

            # Regular field cell
            text.append(" ", style=base_style)
            col += 1

        # Right end zone
        text.append(self._build_end_zone_cell(self.home_name, self.home_primary_color, row_idx, is_left=False))

        return text

    def _get_yard_marker_at(self, col: int) -> Optional[str]:
        """Get yard marker text if this column starts one."""
        # Yard markers at 10-yard intervals
        # Columns for each marker (approximate positions in 53-char field)
        markers = {
            0: "G",      # 0 yard line (goal)
            5: "10",     # 10 yard line
            11: "20",    # 20 yard line
            16: "30",    # 30 yard line
            21: "40",    # 40 yard line
            26: "50",    # 50 yard line (midfield)
            32: "40",    # 40 yard line (other side)
            37: "30",    # 30 yard line
            42: "20",    # 20 yard line
            48: "10",    # 10 yard line
            52: "G",     # 0 yard line (other goal)
        }
        return markers.get(col)

    def _build_end_zone_cell(self, team: str, color: str, row_idx: int, is_left: bool) -> Text:
        """Build an end zone cell for a specific row."""
        text = Text()
        width = self.END_ZONE_WIDTH
        style = f"bold white on {color}"

        # Vertical border
        text.append("│", style=style)

        if row_idx == self.BALL_ROW:
            # Center row shows team abbreviation
            content = f"{team:^{width - 2}}"
        else:
            # Other rows are solid color
            content = " " * (width - 2)

        text.append(content, style=style)

        # Right border
        text.append("│", style=style)

        return text

    def _build_status_line(self) -> Text:
        """Build status line with ball position and special play info."""
        text = Text()

        # Ball position description - dark text for light theme
        yard_desc = self._get_display_yard_line()
        text.append(f"       Ball @ {yard_desc}", style="#1a1a1a")

        # First down info - muted but readable
        fd_yard = self.first_down_marker
        if fd_yard < 100:
            fd_desc = self._get_first_down_description()
            text.append(f"  |  {fd_desc}", style="#666666")

        # Special play indicator
        if self.special_play != SpecialPlay.NONE:
            special_text = self._get_special_play_display()
            special_style = self._get_special_play_style()
            text.append(f"  |  {special_text}", style=special_style)

        return text

    def _get_display_yard_line(self) -> str:
        """Get human-readable yard line description."""
        pos = self.ball_position

        if pos <= 0:
            return "Own Goal Line"
        elif pos >= 100:
            return "Opponent Goal Line"
        elif pos == 50:
            return "50 Yard Line"
        elif pos < 50:
            return f"OWN {pos}"
        else:
            return f"OPP {100 - pos}"

    def _get_first_down_description(self) -> str:
        """Get first down marker description."""
        fd = self.first_down_marker
        if fd >= 100:
            return "Goal to go"
        elif fd == 50:
            return "1st @ 50"
        elif fd < 50:
            return f"1st @ OWN {fd}"
        else:
            return f"1st @ OPP {100 - fd}"

    def _get_special_play_display(self) -> str:
        """Get display text for special play."""
        displays = {
            SpecialPlay.TOUCHDOWN: "TOUCHDOWN!",
            SpecialPlay.FIELD_GOAL_GOOD: "FIELD GOAL GOOD!",
            SpecialPlay.FIELD_GOAL_MISS: "FG MISSED",
            SpecialPlay.PUNT: "PUNT",
            SpecialPlay.INTERCEPTION: "INTERCEPTION!",
            SpecialPlay.FUMBLE: "FUMBLE!",
            SpecialPlay.SAFETY: "SAFETY!",
            SpecialPlay.FIRST_DOWN: "FIRST DOWN",
        }
        base = displays.get(self.special_play, "")
        if self.special_play_text:
            return f"{base} {self.special_play_text}"
        return base

    def _get_special_play_style(self) -> str:
        """Get Rich style for special play display."""
        styles = {
            SpecialPlay.TOUCHDOWN: "bold yellow on red",
            SpecialPlay.FIELD_GOAL_GOOD: "bold green",
            SpecialPlay.FIELD_GOAL_MISS: "dim red",
            SpecialPlay.PUNT: "dim white",
            SpecialPlay.INTERCEPTION: "bold white on purple",
            SpecialPlay.FUMBLE: "bold white on dark_orange",
            SpecialPlay.SAFETY: "bold yellow on blue",
            SpecialPlay.FIRST_DOWN: "bold green",
        }
        return styles.get(self.special_play, "white")

    def update_from_field_position(self, field_position: str, yards_to_first: int = 10) -> None:
        """
        Update ball position from field position string.

        Field position format: 'OWN 25' or 'OPP 30'
        - OWN = offensive team's side of field
        - OPP = opponent's side of field
        """
        try:
            parts = field_position.upper().split()
            if len(parts) >= 2:
                zone = parts[0]
                yard = int(parts[1])

                if zone == "OWN":
                    self.ball_position = yard
                elif zone == "OPP":
                    self.ball_position = 100 - yard
                else:
                    self.ball_position = 50

                self.first_down_marker = min(100, self.ball_position + yards_to_first)

        except (ValueError, IndexError):
            pass

    def show_special_play(self, play_type: SpecialPlay, text: str = "") -> None:
        """Show a special play indicator."""
        self.special_play = play_type
        self.special_play_text = text

    def clear_special_play(self) -> None:
        """Clear special play indicator."""
        self.special_play = SpecialPlay.NONE
        self.special_play_text = ""

    def show_play_result(self, outcome: PlayOutcome, is_first_down: bool = False) -> None:
        """Show appropriate special play based on outcome."""
        if outcome == PlayOutcome.TOUCHDOWN:
            self.show_special_play(SpecialPlay.TOUCHDOWN)
        elif outcome == PlayOutcome.FIELD_GOAL_GOOD:
            self.show_special_play(SpecialPlay.FIELD_GOAL_GOOD)
        elif outcome == PlayOutcome.FIELD_GOAL_MISSED:
            self.show_special_play(SpecialPlay.FIELD_GOAL_MISS)
        elif outcome == PlayOutcome.PUNT_RESULT:
            self.show_special_play(SpecialPlay.PUNT)
        elif outcome == PlayOutcome.INTERCEPTION:
            self.show_special_play(SpecialPlay.INTERCEPTION)
        elif outcome in (PlayOutcome.FUMBLE, PlayOutcome.FUMBLE_LOST):
            self.show_special_play(SpecialPlay.FUMBLE)
        elif outcome == PlayOutcome.SAFETY:
            self.show_special_play(SpecialPlay.SAFETY)
        elif is_first_down and outcome not in (PlayOutcome.INCOMPLETE,):
            self.show_special_play(SpecialPlay.FIRST_DOWN)
        else:
            self.clear_special_play()

    # Reactive watchers
    def watch_ball_position(self, position: int) -> None:
        """Called when ball position changes."""
        self.refresh()

    def watch_first_down_marker(self, marker: int) -> None:
        """Called when first down marker changes."""
        self.refresh()

    def watch_possession_is_home(self, is_home: bool) -> None:
        """Called when possession changes."""
        self.refresh()

    def watch_special_play(self, play: SpecialPlay) -> None:
        """Called when special play changes."""
        self.refresh()
