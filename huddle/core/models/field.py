"""Field position and down/distance tracking."""

from dataclasses import dataclass
from enum import Enum, auto


class FieldZone(Enum):
    """Field zones for probability adjustments and situational awareness."""

    OWN_ENDZONE = auto()  # 0-10: Backed up, conservative
    OWN_TERRITORY = auto()  # 10-50: Normal play
    OPPONENT_TERRITORY = auto()  # 50-90: Scoring range
    RED_ZONE = auto()  # 90-100: Close to goal line


@dataclass
class FieldPosition:
    """
    Represents position on the field.

    Uses a 0-100 scale where:
    - 0 = own goal line (defensive endzone)
    - 50 = midfield
    - 100 = opponent's goal line (touchdown)

    This simplifies calculations while maintaining accuracy.
    """

    yard_line: int  # 0-100

    def __post_init__(self) -> None:
        """Clamp yard line to valid range."""
        self.yard_line = max(0, min(100, self.yard_line))

    @classmethod
    def from_field_position(cls, yard_line: int, own_side: bool) -> "FieldPosition":
        """
        Create from traditional field position notation.

        Args:
            yard_line: The yard line number (1-50)
            own_side: True if in own territory, False if in opponent's

        Examples:
            - Own 25 yard line: from_field_position(25, True) -> 25
            - Opponent 25 yard line: from_field_position(25, False) -> 75
        """
        if own_side:
            return cls(yard_line)
        else:
            return cls(100 - yard_line)

    @property
    def display(self) -> str:
        """
        Human-readable field position.

        Returns strings like "OWN 25", "OPP 30", "50" (midfield).
        """
        if self.yard_line == 50:
            return "50"
        elif self.yard_line < 50:
            return f"OWN {self.yard_line}"
        else:
            return f"OPP {100 - self.yard_line}"

    @property
    def traditional_display(self) -> str:
        """
        Traditional field position display (e.g., 'NE 25', 'DAL 30').

        For use when team context is available.
        """
        if self.yard_line <= 50:
            return f"{self.yard_line}"
        else:
            return f"{100 - self.yard_line}"

    @property
    def zone(self) -> FieldZone:
        """Get the field zone for this position."""
        if self.yard_line <= 10:
            return FieldZone.OWN_ENDZONE
        elif self.yard_line <= 50:
            return FieldZone.OWN_TERRITORY
        elif self.yard_line < 90:
            return FieldZone.OPPONENT_TERRITORY
        else:
            return FieldZone.RED_ZONE

    @property
    def yards_to_goal(self) -> int:
        """Yards needed to reach opponent's end zone."""
        return 100 - self.yard_line

    @property
    def yards_to_safety(self) -> int:
        """Yards to own end zone (negative play territory)."""
        return self.yard_line

    @property
    def is_goal_to_go(self) -> bool:
        """Check if inside the 10 yard line."""
        return self.yard_line >= 90

    @property
    def is_in_field_goal_range(self) -> bool:
        """Check if in reasonable field goal range (roughly 55 yards or less)."""
        return self.yard_line >= 45  # 100 - 45 = 55 yard FG attempt

    def advance(self, yards: int) -> "FieldPosition":
        """
        Create new field position after advancing yards.

        Positive yards = toward opponent's end zone.
        Negative yards = toward own end zone.
        """
        return FieldPosition(self.yard_line + yards)

    def __add__(self, yards: int) -> "FieldPosition":
        """Allow: new_pos = field_pos + 10."""
        return self.advance(yards)

    def __sub__(self, yards: int) -> "FieldPosition":
        """Allow: new_pos = field_pos - 5."""
        return self.advance(-yards)


@dataclass
class DownState:
    """
    Tracks current down and distance situation.

    This is the core situational state for play-by-play simulation.
    """

    down: int = 1  # 1-4
    yards_to_go: int = 10
    line_of_scrimmage: FieldPosition = None

    def __post_init__(self) -> None:
        """Initialize default line of scrimmage if not provided."""
        if self.line_of_scrimmage is None:
            self.line_of_scrimmage = FieldPosition(25)

    @property
    def display(self) -> str:
        """Display string like '1st & 10' or '3rd & Goal'."""
        down_names = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}
        down_str = down_names.get(self.down, f"{self.down}th")

        if self.is_goal_to_go:
            return f"{down_str} & Goal"
        else:
            return f"{down_str} & {self.yards_to_go}"

    @property
    def full_display(self) -> str:
        """Full display with field position."""
        return f"{self.display} at {self.line_of_scrimmage.display}"

    @property
    def is_goal_to_go(self) -> bool:
        """Check if this is a goal-to-go situation."""
        return self.line_of_scrimmage.yards_to_goal <= self.yards_to_go

    @property
    def is_fourth_down(self) -> bool:
        """Check if this is 4th down."""
        return self.down == 4

    @property
    def is_short_yardage(self) -> bool:
        """Check if this is a short yardage situation (3 yards or less)."""
        return self.yards_to_go <= 3

    @property
    def is_long_yardage(self) -> bool:
        """Check if this is a long yardage situation (7+ yards)."""
        return self.yards_to_go >= 7

    @property
    def first_down_marker(self) -> int:
        """
        Yard line where first down would be achieved.

        Returns value in 0-100 scale. If goal-to-go, returns 100.
        """
        target = self.line_of_scrimmage.yard_line + self.yards_to_go
        return min(100, target)

    def reset_for_first_down(self, new_los: FieldPosition) -> "DownState":
        """
        Create new down state after achieving first down.

        Sets yards to go based on distance to goal line.
        """
        yards_to_go = min(10, new_los.yards_to_goal)
        return DownState(down=1, yards_to_go=yards_to_go, line_of_scrimmage=new_los)

    def advance(self, yards_gained: int) -> tuple["DownState", bool]:
        """
        Create new down state after a play.

        Args:
            yards_gained: Yards gained on the play (can be negative)

        Returns:
            Tuple of (new_down_state, achieved_first_down)
        """
        new_los = self.line_of_scrimmage.advance(yards_gained)
        new_yards_to_go = self.yards_to_go - yards_gained

        # Check for touchdown
        if new_los.yard_line >= 100:
            return DownState(down=1, yards_to_go=10, line_of_scrimmage=new_los), True

        # Check for first down
        if new_yards_to_go <= 0:
            return self.reset_for_first_down(new_los), True

        # Advance to next down
        return DownState(
            down=self.down + 1,
            yards_to_go=new_yards_to_go,
            line_of_scrimmage=new_los,
        ), False

    def copy(self) -> "DownState":
        """Create a copy of this down state."""
        return DownState(
            down=self.down,
            yards_to_go=self.yards_to_go,
            line_of_scrimmage=FieldPosition(self.line_of_scrimmage.yard_line),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "down": self.down,
            "yards_to_go": self.yards_to_go,
            "line_of_scrimmage": self.line_of_scrimmage.yard_line,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DownState":
        """Create from dictionary."""
        return cls(
            down=data.get("down", 1),
            yards_to_go=data.get("yards_to_go", 10),
            line_of_scrimmage=FieldPosition(data.get("line_of_scrimmage", 25)),
        )
