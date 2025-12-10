"""Custom Textual messages for UI updates."""

from typing import TYPE_CHECKING

from textual.message import Message

if TYPE_CHECKING:
    from huddle.core.models.play import PlayCall
    from huddle.events.types import (
        GameEndEvent,
        PlayCompletedEvent,
        QuarterEndEvent,
        ScoringEvent,
        TurnoverEvent,
    )


class PlayCompletedMessage(Message):
    """Posted when a play completes."""

    def __init__(self, event: "PlayCompletedEvent") -> None:
        self.event = event
        super().__init__()


class ScoringMessage(Message):
    """Posted on scoring plays."""

    def __init__(self, event: "ScoringEvent") -> None:
        self.event = event
        super().__init__()


class TurnoverMessage(Message):
    """Posted on turnovers."""

    def __init__(self, event: "TurnoverEvent") -> None:
        self.event = event
        super().__init__()


class QuarterEndMessage(Message):
    """Posted at end of quarter."""

    def __init__(self, event: "QuarterEndEvent") -> None:
        self.event = event
        super().__init__()


class GameEndMessage(Message):
    """Posted when game ends."""

    def __init__(self, event: "GameEndEvent") -> None:
        self.event = event
        super().__init__()


class AwaitingPlayCallMessage(Message):
    """Posted when manual mode needs a play call."""

    pass


class PlayCallSelectedMessage(Message):
    """Posted when user selects a play in manual mode."""

    def __init__(self, play_call: "PlayCall") -> None:
        self.play_call = play_call
        super().__init__()


class PacingChangedMessage(Message):
    """Posted when pacing setting changes."""

    def __init__(self, pacing: str) -> None:
        self.pacing = pacing
        super().__init__()


class LayoutChangedMessage(Message):
    """Posted when layout changes."""

    def __init__(self, layout: str) -> None:
        self.layout = layout
        super().__init__()


class ModeChangedMessage(Message):
    """Posted when simulation mode changes."""

    def __init__(self, mode: str) -> None:
        self.mode = mode
        super().__init__()


class PauseToggledMessage(Message):
    """Posted when pause state toggles."""

    pass


class StepRequestedMessage(Message):
    """Posted when user requests next step in step mode."""

    pass
