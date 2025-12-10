"""Play calling widget for manual mode."""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Button, Static

from huddle.core.enums import PassType, RunType
from huddle.core.models.play import PlayCall
from huddle.ui.messages import PlayCallSelectedMessage


class PlayCaller(Horizontal):
    """Play selection interface for manual mode."""

    is_active: reactive[bool] = reactive(False)
    awaiting_call: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        """Compose the play caller."""
        yield Static("CALL PLAY: ", classes="call-label")
        yield Button("Run In [R]", id="call-run-inside", variant="primary", classes="play-btn")
        yield Button("Run Out [O]", id="call-run-outside", variant="primary", classes="play-btn")
        yield Button("Short [S]", id="call-pass-short", variant="success", classes="play-btn")
        yield Button("Medium [M]", id="call-pass-medium", variant="success", classes="play-btn")
        yield Button("Deep [D]", id="call-pass-deep", variant="success", classes="play-btn")
        yield Button("Punt [U]", id="call-punt", variant="warning", classes="play-btn")
        yield Button("FG [F]", id="call-fg", variant="warning", classes="play-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle play call button presses."""
        if not self.awaiting_call:
            return

        button_id = event.button.id
        play_call = self._get_play_call(button_id)

        if play_call:
            self.awaiting_call = False
            self.post_message(PlayCallSelectedMessage(play_call))

    def _get_play_call(self, button_id: str | None) -> PlayCall | None:
        """Convert button ID to PlayCall."""
        if button_id is None:
            return None

        play_calls = {
            "call-run-inside": PlayCall.run(RunType.INSIDE),
            "call-run-outside": PlayCall.run(RunType.OUTSIDE),
            "call-pass-short": PlayCall.pass_play(PassType.SHORT),
            "call-pass-medium": PlayCall.pass_play(PassType.MEDIUM),
            "call-pass-deep": PlayCall.pass_play(PassType.DEEP),
            "call-punt": PlayCall.punt(),
            "call-fg": PlayCall.field_goal(),
        }
        return play_calls.get(button_id)

    def request_play_call(self) -> None:
        """Signal that a play call is needed."""
        self.awaiting_call = True

    def watch_awaiting_call(self, awaiting: bool) -> None:
        """Update button states based on awaiting status."""
        if not self.is_mounted:
            return
        for btn in self.query(".play-btn"):
            btn.disabled = not awaiting

    def watch_is_active(self, active: bool) -> None:
        """Update visibility based on active status."""
        if not self.is_mounted:
            return
        self.display = active

    def handle_key_call(self, key: str) -> bool:
        """Handle keyboard play call. Returns True if handled."""
        if not self.awaiting_call:
            return False

        key_mapping = {
            "r": "call-run-inside",
            "o": "call-run-outside",
            "s": "call-pass-short",
            "m": "call-pass-medium",
            "d": "call-pass-deep",
            "u": "call-punt",
            "f": "call-fg",
        }

        button_id = key_mapping.get(key.lower())
        if button_id:
            play_call = self._get_play_call(button_id)
            if play_call:
                self.awaiting_call = False
                self.post_message(PlayCallSelectedMessage(play_call))
                return True

        return False
