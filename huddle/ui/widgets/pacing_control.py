"""Pacing control widget for simulation speed."""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Button, Static

from huddle.ui.constants import PACING_DELAYS
from huddle.ui.messages import PacingChangedMessage, PauseToggledMessage, StepRequestedMessage


class PacingControl(Horizontal):
    """Speed selection and play/pause controls."""

    current_pacing: reactive[str] = reactive("fast")
    is_paused: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        """Compose the pacing control."""
        yield Button("Instant", id="pacing-instant", classes="pacing-btn")
        yield Button("Fast", id="pacing-fast", classes="pacing-btn selected")
        yield Button("Slow", id="pacing-slow", classes="pacing-btn")
        yield Button("Step", id="pacing-step", classes="pacing-btn")
        yield Static(" | ", classes="separator")
        yield Button("Pause", id="toggle-pause", variant="warning")
        yield Button("Next", id="step-next", variant="primary", disabled=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id and button_id.startswith("pacing-"):
            pacing = button_id.replace("pacing-", "")
            self.current_pacing = pacing
            self.post_message(PacingChangedMessage(pacing))
        elif button_id == "toggle-pause":
            self.is_paused = not self.is_paused
            self.post_message(PauseToggledMessage())
        elif button_id == "step-next":
            self.post_message(StepRequestedMessage())

    def watch_current_pacing(self, pacing: str) -> None:
        """Update button styles when pacing changes."""
        if not self.is_mounted:
            return
        for btn in self.query(".pacing-btn"):
            btn.remove_class("selected")

        selected_btn = self.query_one(f"#pacing-{pacing}", Button)
        selected_btn.add_class("selected")

        # Enable/disable step button based on pacing
        step_btn = self.query_one("#step-next", Button)
        step_btn.disabled = pacing != "step"

    def watch_is_paused(self, paused: bool) -> None:
        """Update pause button text."""
        if not self.is_mounted:
            return
        pause_btn = self.query_one("#toggle-pause", Button)
        pause_btn.label = "Resume" if paused else "Pause"
        pause_btn.variant = "success" if paused else "warning"
